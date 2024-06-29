import streamlit as st
import yt_dlp
import os
import subprocess
import tempfile
import re

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def format_duration(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def is_valid_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    return re.match(youtube_regex, url) is not None

def download_video(url, resolution):
    try:
        ffmpeg_available = st.session_state.ffmpeg_available
        
        if ffmpeg_available:
            format_spec = f'bestvideo[height<={resolution[:-1]}]+bestaudio/best[height<={resolution[:-1]}]'
        else:
            format_spec = f'best[height<={resolution[:-1]}]'
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            ydl_opts = {
                'format': format_spec,
                'outtmpl': os.path.join(tmpdirname, '%(title)s.%(ext)s'),
                'progress_hooks': [progress_hook],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_title = info['title']
                
                with st.spinner(f"Downloading: {video_title}"):
                    if 'progress_bar' not in st.session_state:
                        st.session_state.progress_bar = st.progress(0)
                    if 'status_text' not in st.session_state:
                        st.session_state.status_text = st.empty()
                    
                    ydl.download([url])
                    downloaded_file = ydl.prepare_filename(info)

            st.success("Congratulations!! Download completed successfully! Click the button below to download.")
            with open(downloaded_file, 'rb') as f:
                st.download_button(
                    label="Download Video",
                    data=f,
                    file_name=os.path.basename(downloaded_file),
                    mime="video/mp4"
                )
            st.balloons()
    except Exception as e:
        st.error(f"An error occurred: {e}")

def progress_hook(d):
    if d['status'] == 'downloading':
        progress = float(d['downloaded_bytes'] / d['total_bytes']) * 100
        st.session_state.progress_bar.progress(int(progress))
        st.session_state.status_text.text(f"Downloaded: {d['downloaded_bytes'] / 1024 / 1024:.2f} MB / {d['total_bytes'] / 1024 / 1024:.2f} MB")
    elif d['status'] == 'finished':
        st.session_state.status_text.text("Download finished, now converting...")

st.set_page_config(page_title="MiEn's YouTube Video Downloader", page_icon="🎥", layout="wide")

# Custom CSS for styling
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
        color: green;
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

url = st.text_input("Paste or Enter the YouTube video URL:", key="url_input")
col1, col2, col3 = st.columns([1, 1, 1])
send_button = col1.button("Get Video Info", key="get_info_button")
clear_button = col2.button("Clear", key="clear_button")

if clear_button:
    st.session_state.url_input = ""
    st.session_state.pop('video_info', None)
    st.session_state.pop('resolutions', None)
    st.experimental_rerun()

if send_button and url:
    if not is_valid_youtube_url(url):
        st.error("Invalid YouTube URL. Please enter a valid YouTube video URL.")
    else:
        try:
            with st.spinner("Please wait while we Fetch the video information..."):
                ydl_opts = {'format': 'bestvideo+bestaudio/best'}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    st.session_state.video_info = {
                        'title': info['title'],
                        'duration': info['duration'],
                        'views': info['view_count'],
                        'thumbnail': info['thumbnail'],
                    }
                    
                    available_formats = [f for f in info['formats'] if f.get('height')]
                    resolutions = sorted(set([f'{f["height"]}p' for f in available_formats]), key=lambda x: int(x[:-1]), reverse=True)
                    st.session_state.resolutions = resolutions
            
            st.success("Video information loaded successfully!")
        except Exception as e:
            st.error(f"Error loading video information: {e}")

if 'video_info' in st.session_state:
    st.subheader("Video Information")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(st.session_state.video_info['thumbnail'], use_column_width=True)
    with col2:
        st.markdown(f"**Title:** {st.session_state.video_info['title']}")
        st.markdown(f"**Duration:** {format_duration(st.session_state.video_info['duration'])}")
        st.markdown(f"**Views:** {st.session_state.video_info['views']:,}")
    
    selected_resolution = st.selectbox("Select Resolution", st.session_state.resolutions)
    
    if st.button("Download Video"):
        download_video(url, selected_resolution)

st.markdown("---")
st.markdown("<h6 style='text-align: center;'>Made with ❤️ by Michael Moses😊</h6>", unsafe_allow_html=True)
