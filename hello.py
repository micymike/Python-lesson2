import streamlit as st
import yt_dlp
import os
import subprocess
import tempfile
import re
from youtubesearchpython import VideosSearch

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
        st.error(f"Error searching YouTube: {e}")
        return []

def download_media(url, resolution, is_audio):
    try:
        ffmpeg_available = st.session_state.ffmpeg_available

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
                    st.success("Your media is ready to be downloaded! Please click the button below.")
                    with open(final_filename, 'rb') as f:
                        st.download_button(
                            label="Download Media",
                            data=f,
                            file_name=os.path.basename(final_filename),
                            mime="audio/mpeg" if is_audio and ffmpeg_available else "video/mp4"
                        )
                    st.balloons()
                else:
                    st.error(f"Downloaded file not found: {final_filename}")
    except Exception as e:
        st.error(f"An error occurred during download: {e}")

def progress_hook(d):
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        if total_bytes > 0:
            progress = (d['downloaded_bytes'] / total_bytes) * 100
            st.session_state.progress_bar.progress(int(progress))
            st.session_state.status_text.text(f"Downloaded: {d['downloaded_bytes'] / 1024 / 1024:.2f} MB / {total_bytes / 1024 / 1024:.2f} MB")
    elif d['status'] == 'finished':
        st.session_state.status_text.text("Download finished, now processing...")

st.set_page_config(page_title="MiKe's YouTube Video Downloader", page_icon="🎥", layout="wide")

# Custom CSS for styling (unchanged)
st.markdown("""
    <style>
    .main-title {
        color: #4A90E2;
        text-align: center;
        font-family: 'Arial Black', Gadget, sans-serif;
    }
    .button {
        background-color: #4A90E2;
        border: none;
        color: white;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 16px;
    }
    .button:hover {
        background-color: #45a049;
    }
    .download-button {
        background-color: #4A90E2;
        border: none;
        color: white;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 16px;
    }
    .download-button:hover {
        background-color: #007bb5;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>🎥 MiKe's Youtube Video Downloader</h1>", unsafe_allow_html=True)
st.write("Download your favorite YouTube videos with ease!")

if 'ffmpeg_available' not in st.session_state:
    st.session_state.ffmpeg_available = check_ffmpeg()

if not st.session_state.ffmpeg_available:
    st.warning("")

search_method = st.radio("Choose search method:", ("Search for a song/video", "Paste YouTube URL"))

if search_method == "Search for a song/video":
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Enter your search query:")
    with col2:
        search_button = st.button("Search")
    
    if search_button and query:
        with st.spinner("Searching for videos..."):
            results = search_youtube(query)
        if results:
            options = [f"{result['title']} by {result['channel']['name']}" for result in results]
            selected_option = st.selectbox("Select a video:", options)
            selected_index = options.index(selected_option)
            url = results[selected_index]['link']
            st.session_state.url = url
        else:
            st.write("No results found.")
            st.session_state.url = None
else:
    url = st.text_input("Paste or Enter the YouTube video URL:", key="url_input")
    if url:
        st.session_state.url = url

if 'url' in st.session_state and st.session_state.url:
    if not is_valid_youtube_url(st.session_state.url):
        st.error("Invalid YouTube URL. Please enter a valid YouTube video URL.")
    else:
        try:
            with st.spinner("Please wait while we fetch the media information..."):
                ydl_opts = {'format': 'bestvideo+bestaudio/best'}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(st.session_state.url, download=False)

                    if info:
                        st.session_state.video_info = {
                            'title': info.get('title', 'Unknown Title'),
                            'duration': info.get('duration', 0),
                            'views': info.get('view_count', 0),
                            'thumbnail': info.get('thumbnail', ''),
                        }

                        available_formats = [f for f in info.get('formats', []) if f.get('height')]
                        resolutions = sorted(set([f'{f["height"]}p' for f in available_formats if f.get('height')]), key=lambda x: int(x[:-1]), reverse=True)
                        st.session_state.resolutions = resolutions if resolutions else ['720p']  # Default to 720p if no resolutions found

                        st.success("Video information loaded successfully!")
                    else:
                        st.error("Failed to fetch video information. Please try again.")
        except Exception as e:
            st.error(f"Error loading video information: {e}")

if 'video_info' in st.session_state and st.session_state.video_info:
    st.subheader("Video Information")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(st.session_state.video_info['thumbnail'], use_column_width=True)
    with col2:
        st.markdown(f"**Title:** {st.session_state.video_info['title']}")
        st.markdown(f"**Duration:** {format_duration(st.session_state.video_info['duration'])}")
        st.markdown(f"**Views:** {st.session_state.video_info['views']:,}")

    download_type = st.radio("Choose download type:", ("Video", "Audio"))

    if download_type == "Video" and 'resolutions' in st.session_state:
        selected_resolution = st.selectbox("Select Resolution", st.session_state.resolutions)
    else:
        selected_resolution = None
        if not st.session_state.ffmpeg_available:
            st.warning("")

    if 'progress_bar' not in st.session_state:
        st.session_state.progress_bar = st.progress(0)
    if 'status_text' not in st.session_state:
        st.session_state.status_text = st.empty()

    if st.button("Download"):
        download_media(st.session_state.url, selected_resolution, is_audio=(download_type == "Audio"))

st.markdown("---")
st.markdown("<h6 style='text-align: center;'>Made with ❤️ by Michael Moses😊</h6>", unsafe_allow_html=True)

if st.button("Clear All"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()