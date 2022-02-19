import sys, json, os
from util import *

if len(sys.argv) == 1:
    CONFIG = read_config()
    if 'default' not in CONFIG:
        exit(-1)

    path = dir_path / CONFIG['default']
else:
    path = Path(sys.argv[1]).resolve()
print("Play files in", str(path))

audio_files = [str(p) for p in get_files_in(path)]
print(audio_files)
with open(pipe_path, 'w') as fifo_write:
    fifo_write.write(json.dumps(audio_files))

os.system("tree -L 4 -dNFln --prune --noreport")