import flet as ft
# yt_dlp is imported lazily to prevent Android startup crashes
import urllib.request
import os
import threading
import urllib.parse
import traceback

def main(page: ft.Page):
    try:
        page.title = "X Video Downloader"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.scroll = ft.ScrollMode.AUTO
        
        url_input = ft.TextField(label="Enter X Video URL", expand=True)
        parse_btn = ft.ElevatedButton("Parse Video", icon=ft.icons.SEARCH)
        
        # UI Elements for video details
        video_card = ft.Column(visible=False, spacing=10)
        video_thumbnail = ft.Image(src="", border_radius=10, fit=ft.ImageFit.CONTAIN)
        video_title = ft.Text("Title: ", weight=ft.FontWeight.BOLD, size=16, no_wrap=False)
        video_quality = ft.Text("Quality: ")
        video_duration = ft.Text("Duration: ")
        
        progress_bar = ft.ProgressBar(visible=False, value=0)
        progress_text = ft.Text(visible=False, color=ft.colors.GREY_700)
        download_btn = ft.ElevatedButton("Download Video", icon=ft.icons.DOWNLOAD, visible=False, bgcolor=ft.colors.GREEN, color=ft.colors.WHITE)
        
        # Store fetched data
        video_info = {"url": "", "title": ""}
        
        def on_parse(e):
            if not url_input.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a URL"))
                page.snack_bar.open = True
                page.update()
                return
                
            parse_btn.disabled = True
            progress_bar.visible = True
            progress_bar.value = None # indeterminate
            progress_text.visible = True
            progress_text.value = "Extracting video info..."
            page.update()
            
            # run in thread to avoid blocking UI
            threading.Thread(target=extract_info).start()

        def extract_info():
            try:
                import yt_dlp
                ydl_opts = {
                    'format': 'best',
                    'quiet': True,
                    'noplaylist': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url_input.value, download=False)
                    
                    # try to find the best direct mp4/http format first
                    direct_url = None
                    if 'formats' in info and len(info['formats']) > 0:
                        direct_formats = [
                            f for f in info['formats'] 
                            if f.get('ext') == 'mp4' and f.get('protocol', '').startswith('http') and 'm3u8' not in f.get('protocol', '')
                        ]
                        if direct_formats:
                            direct_url = direct_formats[-1].get('url')
                        else:
                            direct_url = info['formats'][-1].get('url')
                    elif 'url' in info:
                        direct_url = info['url']
                    elif 'entries' in info and len(info['entries']) > 0:
                        direct_url = info['entries'][0].get('url')
                        
                    if not direct_url:
                        raise Exception("Could not extract direct video url")
                    
                    video_info["url"] = direct_url
                    video_info["title"] = info.get('title', 'x_video')
                    
                    # update UI
                    video_thumbnail.src = info.get('thumbnail', '')
                    video_title.value = f"Title: {video_info['title']}"
                    
                    quality = info.get('format_note', 'best')
                    video_quality.value = f"Quality: {quality}"
                    
                    dur = info.get('duration', 0)
                    video_duration.value = f"Duration: {dur}s"
                    
                    video_card.controls = [
                        video_thumbnail,
                        video_title,
                        video_quality,
                        video_duration
                    ]
                    video_card.visible = True
                    download_btn.visible = True
                    
                    progress_bar.visible = False
                    progress_text.visible = False
                    parse_btn.disabled = False
                    
                    page.update()
                    
            except Exception as ex:
                print(f"Error: {ex}")
                progress_bar.visible = False
                progress_text.visible = False
                parse_btn.disabled = False
                page.snack_bar = ft.SnackBar(ft.Text(f"Error parsing: {str(ex)}"))
                page.snack_bar.open = True
                page.update()

        def on_download(e):
            download_btn.disabled = True
            progress_bar.visible = True
            progress_bar.value = 0
            progress_text.visible = True
            progress_text.value = "Preparing download..."
            page.update()
            
            threading.Thread(target=download_video).start()

        def download_video():
            try:
                video_url = video_info["url"]
                title = video_info["title"]
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                if not safe_title:
                    safe_title = "x_video"
                
                # Try finding Downloads folder
                download_dir = os.path.expanduser("~/Downloads")
                android_ext_storage = os.environ.get("EXTERNAL_STORAGE")
                if android_ext_storage:
                    download_dir = os.path.join(android_ext_storage, "Download")
                
                if not os.path.exists(download_dir):
                    download_dir = os.getcwd() # local fallback
                    
                file_path = os.path.join(download_dir, f"{safe_title}.mp4")
                
                req = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req) as response:
                    total_size = int(response.info().get('Content-Length', -1))
                    downloaded_size = 0
                    
                    with open(file_path, 'wb') as out_file:
                        while chunk := response.read(8192 * 4):
                            out_file.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0:
                                progress_bar.value = downloaded_size / total_size
                                progress_text.value = f"Downloaded {downloaded_size//1024//1024}MB / {total_size//1024//1024}MB"
                            else:
                                progress_bar.value = None
                                progress_text.value = f"Downloaded {downloaded_size//1024//1024}MB"
                            page.update()
                
                progress_bar.visible = False
                progress_text.value = f"Saved to: {file_path}"
                
                page.snack_bar = ft.SnackBar(ft.Text("Download Complete!"))
                page.snack_bar.open = True
                
            except Exception as ex:
                print(f"Error downloading: {ex}")
                progress_bar.visible = False
                progress_text.value = f"Error: {str(ex)}"
                page.snack_bar = ft.SnackBar(ft.Text(f"Download Error: {str(ex)}"))
                page.snack_bar.open = True
            finally:
                download_btn.disabled = False
                page.update()

        parse_btn.on_click = on_parse
        download_btn.on_click = on_download

        page.add(
            ft.Row([ft.Icon(ft.icons.VIDEO_LIBRARY, color=ft.colors.BLUE_700), ft.Text("X Video Downloader", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_700)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(),
            ft.Row([url_input, parse_btn]),
            ft.Column([
                progress_bar,
                progress_text,
                video_card,
                download_btn
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    except Exception as e:
        page.add(ft.Text(f"CRITICAL APP ERROR:\n{traceback.format_exc()}", color=ft.colors.RED))
        page.update()

if __name__ == "__main__":
    ft.app(target=main)
