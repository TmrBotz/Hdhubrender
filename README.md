# HDHub4u Scraper API — Python + FastAPI

## Files
```
hdhub4u-api/
├── main.py           ← FastAPI app
├── requirements.txt  ← Dependencies
├── render.yaml       ← Render deploy config
└── README.md
```

## Deploy on Render (Free)

1. GitHub pe repo banao, yeh files upload karo
2. [render.com](https://render.com) → New → Web Service
3. GitHub repo connect karo
4. Yeh settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Deploy** → URL milega

## API Endpoints

| Endpoint | Kaam | Example |
|----------|------|---------|
| `GET /` | API info | `/` |
| `GET /latest?count=5` | Latest 5 post URLs | `/latest?count=10` |
| `GET /post?url=URL` | Ek post ke download links | `/post?url=https://...` |
| `GET /full?count=5` | Latest 5 posts + download links | `/full?count=3` |

## Example Response — /full?count=2

```json
{
  "success": true,
  "count": 2,
  "posts": [
    {
      "title": "Dutton Ranch Season 1",
      "thumbnail": "https://image.tmdb.org/...",
      "info": { "quality": "WEB-DL", "language": "Hindi" },
      "download_links": [
        { "label": "Episode 1", "url": "https://...", "type": "download" },
        { "label": "WATCH",     "url": "https://...", "type": "watch" }
      ]
    }
  ]
}
```
