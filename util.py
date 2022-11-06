import yaml, magic, random
from pathlib import Path
import subprocess
import os, sys
import unicodedata
import youtube_dl
from itertools import zip_longest

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

# ========== SHOW FILES ==========
MUSIC_EXTS = ['.mp3', '.opus', '.ogg', '.wav', '.flac', '.mp4']
IGNORE_EXTS = ['.webloc', '.yaml']
COLORS = {
    'blue': '\033[94m',
    'pink': '\033[95m',
    'cyan': '\033[96m',
    'green': '\033[92m',
    'yellow_dim': '\033[33m',
    'yellow': '\033[93m',
    'yellow_back': '\033[43m\033[30m',
    'red': '\033[91m',
    'reset': '\033[00m',
    'bold': '\033[01m',
    'underline': '\033[04m',
}

"""
Option file: _audio.yaml
Example:

list_files: true / false [false]
list_dirs: true / false [true]
hidden: true / false [false]
files_first: true / false [true]
show_symlink_origin: true / false [false]
show_depth: X
right_side:
    - subdir_name
    - ...
order_top:
    - subdir_name
    - ...
order_bottom:
    - subdir_name
    - ...
hide:
    - file_name
    - subdir_name
    - ...

"""
def build_file_structure(path, depth, max_depth, underline_file):
    if depth >= max_depth:
        return None
    dir_data = {
        'name': path.name,
        'files': [],
        'subdirs': [],
        'options': {},
        'depth': depth,
        'symlink': None,
        'underline': False
    }
    if path.is_symlink():
        dir_data['symlink'] = str(path.readlink())
    if underline_file and underline_file == path.resolve():
        dir_data['underline'] = True

    options_file = path / '_audio.yaml'
    if options_file.exists():
        with options_file.open() as f:
            dir_data['options'] = yaml.safe_load(f)
        if dir_data['options'].get('hidden', False):
            return None
        if 'show_depth' in dir_data['options']:
            max_depth = depth + dir_data['options']['show_depth']
    
    to_hide = dir_data['options'].get('hide', [])

    for subpath in path.iterdir():
        if not subpath.name in to_hide:
            if subpath.is_file():
                if subpath.name[0] != '.' and subpath.suffix not in IGNORE_EXTS:
                    dir_data['files'].append(subpath.name)
            elif max_depth > 1:
                sub_struct = build_file_structure(subpath, depth+1, max_depth, underline_file)
                if sub_struct:
                    dir_data['subdirs'].append(sub_struct)

    if not dir_data['files'] and not dir_data['subdirs']:
        return None
    return dir_data

def get_indent_str(stack_last_child):
    all_indents = []
    if stack_last_child:
        for is_empty in stack_last_child[:-1]:
            if is_empty:
                all_indents.append('    ')
            else:
                all_indents.append('│   ')

        if stack_last_child[-1]:
            all_indents.append('└── ')
        else:
            all_indents.append('├── ')
    return ''.join(all_indents)

def get_name(structure):
    if isinstance(structure, str):
        return structure
    return structure['name']

def print_structure(structure, stack_last_child, column, right_col=None, underline_file=None):
    indent = get_indent_str(stack_last_child)
    color = ''
    if isinstance(structure, str):
        # if any(structure.endswith(ext) for ext in MUSIC_EXTS):
        if 'mix' in structure:
            color = COLORS["green"]
        if underline_file and underline_file.name == get_name(structure):
            color = COLORS['yellow_back']
        column.append(f'{indent}{color}{structure}{COLORS["reset"]}')
    else:
        color = COLORS['pink'] if structure['symlink'] else COLORS['cyan']
        if structure['underline']:
            color = COLORS['yellow_back']
        count = ''
        if structure['files']:
            music_count = len(structure['files'])
            mix_count = sum(['mix' in f for f in structure['files']])
            if mix_count:
                count = f' [{music_count-mix_count}|{mix_count}]'
            else:
                count = f' [{music_count}]'

        column.append(f"{indent}{color}{structure['name']}/{COLORS['reset']}{COLORS['yellow_dim']}{count}{COLORS['reset']}")
        if structure['symlink'] and structure['options'].get('show_symlink_origin', False):
            column[-1] += (' -> ' + structure['symlink'])

        at_right = structure["options"].get("right_side", [])
        subs = []
        if structure['options'].get('list_files', False):
            subs.extend(structure['files'])
        if structure['options'].get('list_dirs', True):
            if structure['options'].get('files_first', True):
                subs.extend(structure['subdirs'])
            else:
                subs = structure['subdirs'] + subs

        subs_top, subs_mid, subs_bottom = [], [], []
        order_top = structure['options'].get('order_top', [])
        order_top.extend(at_right)
        order_bottom = structure['options'].get('order_bottom', [])
        for sub_struct in subs:
            if get_name(sub_struct) in order_top:
                subs_top.append(sub_struct)
            elif get_name(sub_struct) in order_bottom:
                subs_bottom.append(sub_struct)
            else:
                subs_mid.append(sub_struct)
        subs_top.sort(key = lambda s : order_top.index(get_name(s)))
        subs_bottom.sort(key = lambda s : order_bottom.index(get_name(s)))
        subs = subs_top + subs_mid + subs_bottom

        for i, sub_struct in enumerate(subs):
            sub_col = column
            if right_col is not None and get_name(sub_struct) in at_right:
                sub_col = right_col

            stack_last_child.append(i == len(subs)-1)
            print_structure(sub_struct, stack_last_child, sub_col, underline_file=underline_file)
            stack_last_child.pop()

def real_len(string):
    return len(unicodedata.normalize('NFC', string)) - string.count('\033') * 5

def show_files_in(path, underline_file=None):
    path = Path(path)
    structure = build_file_structure(path, 0, 4, underline_file)
    col_width = os.get_terminal_size().columns // 2

    left_col, right_col = [], []
    print_structure(structure, [], left_col, right_col, underline_file=underline_file)

    if right_col:
        if len(left_col) < len(right_col):
            left_col = [None] * (len(right_col) - len(left_col)) + left_col
        if len(right_col) < len(left_col):
            right_col = [None] * (len(left_col) - len(right_col)) + right_col

    for left_str, right_str in zip_longest(left_col, right_col):
        if left_str:
            sys.stdout.write(left_str)
        if right_str:
            left_len = real_len(left_str) if left_str else 0
            if left_len <= col_width:
                sys.stdout.write(' ' * (col_width - left_len))
            else:
                sys.stdout.write('\b'  * (left_len - col_width))
                sys.stdout.write(' '  * min(col_width, left_len - col_width))
                sys.stdout.write('\b'  * min(col_width, left_len - col_width))
            sys.stdout.write(right_str)
        sys.stdout.write("\n")
