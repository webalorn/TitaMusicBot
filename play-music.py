import sys
import json
import os
from pathlib import Path

from util import *

COMMANDS = ['pause', 'stop', 'next', 'skip', 'resume', 'leave']
PLAY_COMMANDS = ['play', 'once', 'mix', 'start']
PLAY_AUTO_COMMANDS = ['default', 'def']
# Other commands : once
print(['once', 'pause', 'resume', 'next', 'leave', 'mix', 'start'])
play_path = None

if len(sys.argv) >= 2:
    if sys.argv[1] in COMMANDS:
        command = {'cmd': sys.argv[1], 'args': sys.argv[2:]}
    else:
        files = sys.argv[1]
        cmd_name = 'play'
        if is_youtube(files):
            audio_files = [files]
            print(f"Play youtube video {files}")
        else:
            if files in PLAY_COMMANDS:
                cmd_name = files
                files = sys.argv[2]

            if files in PLAY_AUTO_COMMANDS:
                CONFIG = read_config()
                if 'default' not in CONFIG:
                    exit(-1)
                path = dir_path / CONFIG['default']
            else:
                path = Path(files).resolve()
            play_path = path
            print("Play files in", str(path))

            audio_files = [str(p) for p in get_files_in(path)]
            # print(audio_files)
        command = {'cmd': cmd_name, 'args': audio_files}

    with open(pipe_path, 'w') as fifo_write:
        fifo_write.write(json.dumps(command))
else:
    print("No command, showing files")

# os.system("tree -L 4 -dNFln --prune --noreport")
show_files_in(".", play_path)
