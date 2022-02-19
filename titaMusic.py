import yaml
import discord
import pyaudio
from discord.ext import commands
from discord.opus import Encoder as OpusEncoder
import threading
from queue import Queue
import time

# ========== CONFIG & AUDIO ==========

# FORMAT = pyaudio.paInt16
# CHANNELS = 1
# RATE = 44100
# CHUNK = 2048
audio = pyaudio.PyAudio()

with open('config.yml') as config_file:
    CONFIG = yaml.load(config_file, Loader=yaml.FullLoader)

info = audio.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
devices_names = {}
for i in range(0, numdevices):
    if audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels') > 0:
        devices_names[audio.get_device_info_by_host_api_device_index(0, i).get('name')] = i

if CONFIG['input'] not in devices_names:
    print(f"Can't find any device named '{CONFIG['input']}'")
    print("List of detected devices:")
    for name in devices_names:
        print(f"- '{name}'")
    exit(0)
input_device_index = devices_names[CONFIG['input']]
audio_device = audio.get_device_info_by_index(input_device_index)

# ========== BOT ==========

bot = commands.Bot(command_prefix='Tita ', help_command=None)


@bot.event
async def on_ready():
    print('Bot logged in as {0.user}'.format(bot))

# async def play_audio_in_voice(voice_client):
#     p = pyaudio.PyAudio()
#     # input_stream = audio.open(format=FORMAT, channels=CHANNELS,
#     #             rate=RATE, input=True, input_device_index = input_device_index,
#     #             frames_per_buffer=CHUNK)
#     input_stream = audio.open(
#         format=audio.get_format_from_width(2),
#         channels=int(audio_device['maxInputChannels']),
#         rate=int(audio_device['defaultSampleRate']),
#         input=True,
#         input_device_index=input_device_index
#     )
#     while True:
#         await play_voice(voice_client, input_stream)

# async def play_voice(voice_client, input_stream):
#         data = input_stream.read(CHUNK, exception_on_overflow = False)
#         voice_client.send_audio_packet(data, encode=False)

class AudioStream:
    def __init__(self, **kwargs):
        self.stream = audio.open(**kwargs)
        self.frame_size = OpusEncoder.FRAME_SIZE // 4
        self.data = Queue(maxsize=25)

        self.data_thread = threading.Thread(target=self.preload, args=())
        self.data_thread.start()

        # self.data = []
        # frame_size = 960
        # for _ in range(2000):
        #     self.data.append(self.stream.read(frame_size, exception_on_overflow=False))

        # self.data = self.data[::-1]
    
    def preload(self):
        while True:
            self.data.put(self.stream.read(self.frame_size, exception_on_overflow=False))

    def read(self, frame_size):
        return self.data.get()

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()

class AudioStreamSimple:
    # https://gist.github.com/skmendez/ebbbfcb7e4338a078e5144ddd5dabc48
    """temporary solution to pyaudio quadrupling samples returned"""
    def __init__(self, **kwargs):
        self.stream = audio.open(**kwargs)

    def read(self, frame_size):
        return self.stream.read(int(frame_size/4), exception_on_overflow=False)

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()


stream = AudioStream(
    format=audio.get_format_from_width(2),
    channels=int(audio_device['maxInputChannels']),
    rate=int(audio_device['defaultSampleRate']),
    input=True,
    input_device_index=input_device_index,
    frames_per_buffer=OpusEncoder.FRAME_SIZE,
)
# FORMAT = pyaudio.paInt16
# CHANNELS = 1
# RATE = 44100
# CHUNK = 512
# RECORD_SECONDS = 5
# stream = AudioStream(
#     format=FORMAT
#     channels=CHANNELS,
#     rate=int(audio_device['defaultSampleRate']),
#     input=True,
#     input_device_index=input_device_index,
#     frames_per_buffer=OpusEncoder.FRAME_SIZE,
# )

@bot.command()
async def music(ctx):
    if ctx.author.voice is None:
        await ctx.send(f"{ctx.author.mention} you should be in an audio channel!")
    else:
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        channel = ctx.author.voice.channel
        play_channel = await channel.connect()
        
        # guild = ctx.message.guild
        # play_channel.play(discord.FFmpegPCMAudio(source='heroic_demise.wav'))
        # await play_audio_in_voice(play_channel)

        # print('a')
        # time.sleep(1)
        # print('b')
        play_channel.play(discord.PCMAudio(stream))

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            await ctx.voice_client.stop()
        await ctx.voice_client.disconnect()

@bot.command()
async def help(ctx):
    await ctx.send(f"""Hello! :relaxed::relaxed:
Yon can use me with the following commands :
`music`, `stop`
Always call me by my name (Tita) before a command, and I shall follow your orders!""")

bot.run(CONFIG['token'])

def main():
    pass

if __file__ == "__main__":
    main()