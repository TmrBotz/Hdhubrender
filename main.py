from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import asyncio

app = FastAPI(title="HDHub4u Scraper API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "https://new1.hdhub4u.cl/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

SKIP_DOMAINS = ["hdhub4u", "how-to", "whatsapp", "youtube", "imdb", "catimages", "gravatar"]


# ── Fetch HTML ──────────────────────────────────────────────
async def fetch_html(url: str) -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text


# ── Step 1: Get N latest post URLs from homepage ────────────
async def get_latest_posts(count: int = 5) -> list[dict]:
    html = await fetch_html(BASE_URL)
    soup = BeautifulSoup(html, "html.parser")

    posts = []
    seen = set()

    ul = soup.find("ul", class_="recent-movies")
    if ul:
        for li in ul.find_all("li", class_="thumb"):
            a = li.find("a", href=True)
            img = li.find("img")
            if not a:
                continue
            href = a["href"]
            if href in seen or "/category/" in href or href == BASE_URL:
                continue
            seen.add(href)
            posts.append({
                "url": href,
                "title": img.get("title", img.get("alt", "")) if img else "",
                "thumbnail": img["src"] if img else None,
            })
            if len(posts) >= count:
                break

    return posts


# ── Step 2: Extract download links from post page ───────────
async def get_post_links(post_url: str) -> dict:
    html = await fetch_html(post_url)
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else "Unknown"
    title = title.split("–")[0].split("-")[0].strip()

    # Thumbnail
    thumb = soup.find("img", class_="aligncenter")
    thumbnail = thumb["src"] if thumb else None

    # Movie info
    info = {}
    info_map = {
        "quality": "Quality",
        "language": "Language",
        "genre": "Genre",
        "stars": "Stars",
        "director": "Director",
    }
    for key, label in info_map.items():
        tag = soup.find("strong", string=lambda t: t and label in t)
        if tag and tag.parent:
            val = tag.parent.get_text(separator=" ").replace(label + ":", "").strip()
            info[key] = val

    # IMDb
    imdb_tag = soup.find("a", href=lambda h: h and "imdb.com" in h)
    if imdb_tag:
        info["imdb"] = imdb_tag.text.strip()

    # Download links from h3 + h4
    links = []
    for tag in soup.find_all(["h3", "h4"]):
        for a in tag.find_all("a", href=True):
            url = a["href"]
            label = a.get_text(strip=True)
            if not url.startswith("http"):
                continue
            if any(d in url for d in SKIP_DOMAINS):
                continue
            link_type = "watch" if any(w in label.lower() for w in ["watch", "player"]) else "download"
            links.append({
                "label": label,
                "url": url,
                "type": link_type,
            })

    return {
        "post_url": post_url,
        "title": title,
        "thumbnail": thumbnail,
        "info": info,
        "download_links": links,
    }


# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "name": "HDHub4u Scraper API",
        "version": "2.0",
        "endpoints": {
            "latest":    "/latest?count=5",
            "post":      "/post?url=POST_URL",
            "full":      "/full?count=5",
        }
    }


@app.get("/latest")
async def latest_posts(count: int = Query(default=5, ge=1, le=20)):
    """Homepage se latest N post URLs aur thumbnails"""
    try:
        posts = await get_latest_posts(count)
        return {
            "success": True,
            "scraped_at": datetime.utcnow().isoformat(),
            "count": len(posts),
            "posts": posts,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/post")
async def single_post(url: str = Query(..., description="Post URL")):
    """Ek specific post ke download links"""
    try:
        data = await get_post_links(url)
        return {"success": True, "scraped_at": datetime.utcnow().isoformat(), **data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/full")
async def full_scrape(count: int = Query(default=5, ge=1, le=10)):
    """Latest N posts + unke saare download links ek saath"""
    try:
        posts = await get_latest_posts(count)
        if not posts:
            return {"success": False, "error": "No posts found on homepage"}

        # Sabke download links parallel fetch karo
        tasks = [get_post_links(p["url"]) for p in posts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        full_data = []
        for result in results:
            if isinstance(result, Exception):
                full_data.append({"error": str(result)})
            else:
                full_data.append(result)

        return {
            "success": True,
            "scraped_at": datetime.utcnow().isoformat(),
            "count": len(full_data),
            "posts": full_data,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
