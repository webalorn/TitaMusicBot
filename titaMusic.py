import asyncio
import json
import random
from collections import deque
from pathlib import Path

import yaml
import discord
from discord.ext import commands, tasks
import youtube_dl

from util import *

# ========== CONFIG & AUDIO ==========

CONFIG = read_config()
pipe = open_pipe_read()
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# ========== MUSIC FROM YT ==========


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    def from_url(cls, url, *, loop=None, stream=False):
        data = ytdl.extract_info(url, download=not stream)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# ========== BOT ==========

def check_admin(ctx):
    return ctx.message.author.id == CONFIG['admin_id']

bot = commands.Bot(command_prefix='Tita ', help_command=None)

song_queue = deque([str(dir_path / '__private__/celtic.opus')])
MODE_ONCE = False
MODE_MIX = False

def play_next(play_channel):
    global MODE_ONCE, MODE_MIX
    source = song_queue.popleft()
    song_queue.append(source)

    options = []
    if MODE_MIX is None and 'mix' in Path(source).name.lower():
        MODE_MIX = 'once'
    if MODE_MIX:
        start_at = get_random_audio_point(source, end_max=0.9)
        options.append(f'-ss {start_at}')
        if MODE_MIX == 'once':
            MODE_MIX = None

    if is_youtube(source):
        audio_source = YTDLSource.from_url(source, stream=True)
        name = audio_source.title
    else:
        audio_source = discord.FFmpegOpusAudio(source=source, options=' '.join(options))
        name = Path(source).stem

    next_action = lambda e: play_next(play_channel)
    if MODE_ONCE:
        next_action = lambda e: play_channel.stop()

    play_channel.play(audio_source, after=next_action)

    asyncio.run_coroutine_threadsafe(
        bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=name)),
        bot.loop)

async def connect_vc(voice):
    voice = await voice.channel.connect()


async def join_author_chan(ctx):
    if ctx.author.voice is None:
        await ctx.send(f"{ctx.author.mention} you should be in an audio channel!")
    elif not ctx.voice_client or ctx.voice_client.channel.id != ctx.author.voice.channel.id:
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        return await connect_vc(ctx.author.voice)

@bot.command()
async def join(ctx):
    await join_author_chan(ctx)
            
@bot.command(aliases=['leave'])
@commands.check(check_admin)
async def stop(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await ctx.voice_client.disconnect()

@bot.command()
@commands.check(check_admin)
async def pause(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()

@bot.command(aliases=['play'])
@commands.check(check_admin)
async def resume(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()

@bot.command(aliases=['next'])
@commands.check(check_admin)
async def skip(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

@bot.command()
@commands.check(check_admin)
async def clear(ctx, amount=200):
    await ctx.channel.purge(limit=int(amount))

@bot.command()
@commands.check(check_admin)
async def help(ctx):
    await ctx.send(f"""`join`, `stop`, `pause`, `resume`, `skip`""")

async def try_connect_master():
    if 'admin_id' in CONFIG:
        guilds = bot.guilds
        for guild in guilds:
            try:
                member = await guild.fetch_member(CONFIG['admin_id'])
            except discord.errors.NotFound:
                continue
            if member.voice:
                chan = await connect_vc(member.voice)
                break

@tasks.loop(seconds=0.05)
async def botLoop():
    global MODE_ONCE, MODE_MIX
    message = pipe.read()
    if message:
        if len(bot.voice_clients) == 0:
            await try_connect_master()

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
                for vc in bot.voice_clients:
                    if vc.is_playing():
                        vc.stop()
                    else:
                        play_next(vc)
        elif cmd in ['pause', 'stop']:
            for vc in bot.voice_clients:
                if vc.is_playing():
                    vc.pause()
        elif cmd in ['next', 'skip']:
            for vc in bot.voice_clients:
                if vc.is_playing():
                    vc.stop()
        elif cmd in ['resume']:
            for vc in bot.voice_clients:
                if vc.is_paused():
                    vc.resume()
        elif cmd == "leave":
            for vc in bot.voice_clients:
                if vc.is_playing():
                    vc.stop()
                await vc.disconnect()
                exit()
        else:
            print(f"Unknown command: {cmd}")

@bot.event
async def on_ready():
    print('Bot logged in as {0.user}'.format(bot))
    await try_connect_master()

def main():
    botLoop.start()
    try:
        bot.run(CONFIG['token'])
    except KeyboardInterrupt:
        bot.logout()
        bot.close()

if __name__ == "__main__":
    main()