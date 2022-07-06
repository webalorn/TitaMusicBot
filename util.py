import yaml, magic, random
from pathlib import Path
import subprocess
import os
import youtube_dl

dir_path = Path(__file__).absolute().parent
pipe_path = "/tmp/titapipe"

def format_time(seconds):
    return f'{(seconds//3600)%24:02d}:{(seconds//60)%60:02d}:{seconds%60:02d}'

youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ffmpeg_options = {
    'options': '-vn',
}

# ========== PIPE & COMMUNICATION ==========

def open_pipe_read():
    if os.path.exists(pipe_path):
        os.remove(pipe_path)
    os.mkfifo(pipe_path)
    pipe_fd = os.open(pipe_path, os.O_RDONLY | os.O_NONBLOCK)
    return os.fdopen(pipe_fd)

# ========== FILES ==========

def is_youtube(url):
    return 'www.youtube.com/watch' in url

def is_audio(audio):
    return audio.is_file() and magic.from_file(audio, mime=True).split('/')[0] == 'audio'

def read_config():
    with open(str(dir_path / 'config.yml')) as config_file:
        return yaml.load(config_file, Loader=yaml.FullLoader)

def get_files_in(path):
    if path.is_file():
        return [path]
    else:
        audio_files = []
        for audio in path.iterdir():
            if is_audio(audio):
                audio_files.append(audio)
        random.shuffle(audio_files)
        print(audio_files)

        for i, audio in enumerate(audio_files):
            if audio.name.startswith('(A)'):
                audio_files[0], audio_files[i] = audio_files[i], audio_files[0]
                break

        return audio_files


# ========== AUDIO ==========

def get_audio_duration(source):
    ffprobe = f'ffprobe -i {source} -show_entries format=duration -v quiet -of csv="p=0"'
    output = subprocess.check_output(ffprobe, shell=True)
    return float(output.decode('utf-8'))

def get_random_audio_point(source, end_max=1, fomat=True):
    duration = get_audio_duration(source)
    point = int(random.random() * end_max * duration)
    return format_time(point) if format else point
