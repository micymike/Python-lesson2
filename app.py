import json
from flask import Flask, Response, render_template, request, send_file, jsonify
import yt_dlp
import os
import subprocess
import tempfile
import re
from youtubesearchpython import VideosSearch

app = Flask(__name__)

def progress_hook(d):
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        if total_bytes > 0:
            progress = (d['downloaded_bytes'] / total_bytes) * 100
            progress_data = {
                'progress': progress,
                'downloaded_bytes': d['downloaded_bytes'],
                'total_bytes': total_bytes,
                'speed': d.get('speed', 0),
                'eta': d.get('eta', 0)
            }
            yield f"data: {json.dumps(progress_data)}\n\n"

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def format_duration(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    elif minutes > 0:
        return f"{minutes}m {seconds:02d}s"
    else:
        return f"{seconds}s"

def is_valid_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    return re.match(youtube_regex, url) is not None

def search_youtube(query):
    try:
        videos_search = VideosSearch(query, limit=5)
        results = videos_search.result()
        return results.get('result', [])
    except Exception as e:
        return []

def download_media(url, resolution, is_audio):
    try:
        ffmpeg_available = check_ffmpeg()

        if is_audio:
            format_spec = 'bestaudio/best'
            file_extension = '.mp3' if ffmpeg_available else '.webm'
        else:
            format_spec = f'bestvideo[height<={resolution[:-1]}]+bestaudio/best[height<={resolution[:-1]}]' if ffmpeg_available else f'best[height<={resolution[:-1]}]'
            file_extension = '.mp4'

        with tempfile.TemporaryDirectory() as tmpdirname:
            ydl_opts = {
                'format': format_spec,
                'outtmpl': os.path.join(tmpdirname, '%(title)s.%(ext)s'),
                'progress_hooks': [progress_hook],
            }
            if is_audio and ffmpeg_available:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                final_filename = os.path.splitext(filename)[0] + file_extension

                if os.path.exists(final_filename):
                    return send_file(final_filename, as_attachment=True)
                else:
                    return jsonify({"error": f"Downloaded file not found: {final_filename}"}), 404
    except Exception as e:
        return jsonify({"error": f"An error occurred during download: {str(e)}"}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    results = search_youtube(query)
    return jsonify(results)

@app.route('/video_info', methods=['POST'])
def video_info():
    url = request.form.get('url')
    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        ydl_opts = {'format': 'bestvideo+bestaudio/best'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if info:
                video_info = {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': format_duration(info.get('duration', 0)),
                    'views': info.get('view_count', 0),
                    'thumbnail': info.get('thumbnail', ''),
                }

                available_formats = [f for f in info.get('formats', []) if f.get('height')]
                resolutions = sorted(set([f'{f["height"]}p' for f in available_formats if f.get('height')]), key=lambda x: int(x[:-1]), reverse=True)
                video_info['resolutions'] = resolutions if resolutions else ['720p']

                return jsonify(video_info)
            else:
                return jsonify({"error": "Failed to fetch video information"}), 404
    except Exception as e:
        return jsonify({"error": f"Error loading video information: {str(e)}"}), 500

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    resolution = request.form.get('resolution')
    is_audio = request.form.get('is_audio') == 'true'
    return download_media(url, resolution, is_audio)

@app.route('/download_progress')
def download_progress():
    def generate():
        yield "data: {'status': 'started'}\n\n"
        for progress in progress_hook({'status': 'downloading', 'downloaded_bytes': 0, 'total_bytes': 100}):
            yield progress
        yield "data: {'status': 'finished'}\n\n"
    
    return Response(generate(), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)