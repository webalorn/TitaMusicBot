import time
import os
import json
from collections import deque
import threading
from queue import Queue, Empty

from util import *
from macosKeys import run_event_loop

# ========== CONFIG & AUDIO ==========

CONFIG = read_config()
pipe = open_pipe_read()
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# ========== PLAYER ==========

class Player():
    def __init__(self):
        self.proc = None
        self.volume = CONFIG.get('player_volume', 100)

    def is_playing(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if self.is_playing():
            self.proc.kill()

    def play(self, source, start_at=None):
        self.stop()
        start_at = start_at or "00:00:00"
        self.proc = subprocess.Popen(
            f"ffplay -autoexit -nodisp -volume {self.volume} -ss {start_at} \"{source}\"",
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
    if is_youtube(source):
        song_info = ytdl.extract_info("https://www.youtube.com/watch?v=4E-_Xpj0Mgo&t=12s", download=False)
        source = song_info['url']
    else:
        if MODE_MIX is None and 'mix' in Path(source).name.lower():
            MODE_MIX = 'once'
        if MODE_MIX:
            start_at = get_random_audio_point(source, end_max=0.9)
            if MODE_MIX == 'once':
                MODE_MIX = None

    if MODE_ONCE:
        song_queue.clear()

    player.play(source, start_at=start_at)

key_queue = Queue()
event_thread = threading.Thread(target=run_event_loop, args=[key_queue])
event_thread.start()

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
            if cmd == 'resume' and song_queue:
                song_queue.appendleft(song_queue.pop())
            play_next()
        elif cmd == "leave":
            player.stop()
            exit()
        else:
            print(f"Unknown command: {cmd}")

    while True:
        try:
            key = key_queue.get(False)
            if not song_queue:
                continue
            if key == 'play_pause':
                if PAUSE:
                    song_queue.appendleft(song_queue.pop())
                    play_next()
                else:
                    player.stop()
                    PAUSE = True
            elif key == 'previous':
                player.stop()
                song_queue.appendleft(song_queue.pop())
                song_queue.appendleft(song_queue.pop())
                play_next()
            elif key == 'next':
                play_next()
        except Empty:
            break

    time.sleep(0.05)
