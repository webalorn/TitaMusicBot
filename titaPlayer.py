import time
import os
import json
from collections import deque
import psutil

from util import *

# ========== CONFIG & AUDIO ==========

CONFIG = read_config()
pipe = open_pipe_read()

# ========== PLAYER ==========

class Player():
    def __init__(self):
        self.proc = None

    def is_playing(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if self.is_playing():
            self.proc.kill()

    def play(self, source, start_at=None):
        self.stop()
        start_at = start_at or "00:00:00"
        self.proc = subprocess.Popen(
            f"ffplay -autoexit -nodisp -ss {start_at} {source}",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

player = Player()
song_queue = deque()
MODE_ONCE = False
MODE_MIX = False
PAUSE = False

def play_next():
    global MODE_MIX, PAUSE
    if not song_queue:
        return

    PAUSE = False
    source = song_queue.popleft()
    song_queue.append(source)

    start_at = None
    if MODE_MIX is None and 'mix' in Path(source).name.lower():
        MODE_MIX = True
    if MODE_MIX:
        MODE_MIX = False
        start_at = get_random_audio_point(source, end_max=0.9)

    if MODE_ONCE:
        song_queue.clear()

    player.play(source, start_at=start_at)


player.play("__private__/celtic.ogg")

while True:
    if not player.is_playing() and not PAUSE:
        play_next()

    # Commands
    message = pipe.read()
    if message:
        cmd_obj = json.loads(message)
        cmd, args = cmd_obj['cmd'], cmd_obj['args']

        if cmd in ['play', 'once', 'mix', 'start']:
            MODE_ONCE = (cmd == 'once')
            MODE_MIX = True if cmd == 'mix' else None
            if cmd == 'start':
                MODE_MIX = False

            if args:
                song_queue.clear()
                song_queue.extend(args)
                play_next()
        elif cmd in ['pause', 'stop']:
            player.stop()
            PAUSE = True
        elif cmd in ['next', 'skip', 'resume']:
            play_next()
        elif cmd == "leave":
            player.stop()
            exit()
        else:
            print(f"Unknown command: {cmd}")

    time.sleep(0.05)
