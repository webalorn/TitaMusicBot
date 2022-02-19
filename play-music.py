import sys, magic, random, json, os
from pathlib import Path

def is_audio(audio):
	return audio.is_file() and magic.from_file(audio, mime=True).split('/')[0] == 'audio'

if len(sys.argv) == 1:
	path = Path(__file__).absolute().parent / '__private__/celtic.opus'
else:
	path = Path(sys.argv[1]).resolve()
print("Play files in", str(path))

dest = str((Path.home() / 'tmp-playlist.m3u').resolve())

lines = ['#EXTM3U']
audio_files = []

if path.is_file():
	audio_files.append(path)
else:
	for audio in path.iterdir():
		if is_audio(audio):
			audio_files.append(audio)
	random.shuffle(audio_files)

pipe_path = "/tmp/titapipe"
with open(pipe_path, 'w') as fifo_write:
	fifo_write.write(json.dumps([str(p) for p in audio_files]))

os.system("tree -L 4 -dNFl --prune --noreport")