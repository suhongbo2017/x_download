import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import yt_dlp
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"message": "index.html not found"})

@app.post("/api/parse")
async def parse_video(request: Request):
    data = await request.json()
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
    
    # We use empty user-agent or let yt-dlp handle it.
    # X (Twitter) extraction usually works with yt-dlp but can sometimes require cookies. 
    # For a basic prototype, standard extraction is used.
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # try to find the best direct mp4/http format first
            video_url = None
            if 'formats' in info and len(info['formats']) > 0:
                # filter formats that are mp4 and protocol is https/http (avoid m3u8/DASH that can't be directly downloaded)
                direct_formats = [
                    f for f in info['formats'] 
                    if f.get('ext') == 'mp4' and f.get('protocol', '').startswith('http') and 'm3u8' not in f.get('protocol', '')
                ]
                if direct_formats:
                    video_url = direct_formats[-1].get('url')
                else:
                    video_url = info['formats'][-1].get('url')
            elif 'url' in info:
                video_url = info['url']
            elif 'entries' in info and len(info['entries']) > 0:
                video_url = info['entries'][0].get('url')
            
            if not video_url:
                raise HTTPException(status_code=400, detail="Could not extract video url")

            title = info.get('title', 'twitter_video')
            duration = info.get('duration', 0)
            thumbnail = info.get('thumbnail', '')
            quality = info.get('format_note', 'best')
            
            return {
                "success": True,
                "data": {
                    "title": title,
                    "url": video_url,
                    "duration": duration,
                    "thumbnail": thumbnail,
                    "quality": quality if quality else "Best"
                }
            }
    except Exception as e:
        print(f"Error parsing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import StreamingResponse
import urllib.request
import urllib.error
import urllib.parse

@app.get("/api/download")
def proxy_download(video_url: str, title: str = "x_video"):
    """
    Proxy the download to bypass CORS and force a file attachment download
    """
    try:
        req = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        response = urllib.request.urlopen(req)
        
        def stream():
            while chunk := response.read(8192 * 4):
                yield chunk
                
        # sanitize title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_title:
            safe_title = "x_video"
            
        encoded_title = urllib.parse.quote(safe_title)
            
        return StreamingResponse(
            stream(), 
            media_type="video/mp4", 
            headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded_title}.mp4"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
