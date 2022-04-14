import asyncio
import os
import json
import subprocess
import random
from collections import deque
from pathlib import Path

import yaml
import discord
from discord.ext import commands, tasks

from util import *

# ========== CONFIG & AUDIO ==========
CONFIG = read_config()


if not os.path.exists(pipe_path):
    os.mkfifo(pipe_path)
pipe_fd = os.open(pipe_path, os.O_RDONLY | os.O_NONBLOCK)
pipe = os.fdopen(pipe_fd)

def check_admin(ctx):
    return ctx.message.author.id == CONFIG['admin_id']

# ========== BOT ==========

bot = commands.Bot(command_prefix='Tita ', help_command=None)

TEST_FILE = "/Volumes/Alveran/jdr/music/@settings/demon-lord/ambiance/calme/ASKII - Reach.mp3"
song_queue = deque([str(dir_path / '__private__/celtic.opus')])
MODE_ONCE = False
MODE_MIX = False
FIRST_RUN = False

def format_time(seconds):
    return f'{(seconds//3600)%24:02d}:{(seconds//60)%60:02d}:{seconds%60:02d}'

def play_next(play_channel):
    global MODE_ONCE, MODE_MIX, FIRST_RUN
    source = song_queue.popleft()
    song_queue.append(source)

    options = []
    if FIRST_RUN and 'mix' in Path(source).name.lower():
        MODE_MIX = True
    if MODE_MIX:
        MODE_MIX = False
        duration = float(subprocess.check_output(f'ffprobe -i {source} -show_entries format=duration -v quiet -of csv="p=0"', shell=True).decode('utf-8'))
        start_at = int(random.random() * 0.9 * duration)
        options.append(f'-ss {start_at}')

    audio_source = discord.FFmpegOpusAudio(source=source, options=' '.join(options))
    FIRST_RUN = False

    next_action = lambda e: play_next(play_channel)
    if MODE_ONCE:
        next_action = lambda e: play_channel.stop()

    play_channel.play(audio_source, after=next_action)

    # if not isinstance(play_channel.source, discord.PCMVolumeTransformer):
    #     play_channel.source = discord.PCMVolumeTransformer(play_channel.source, volume=0.5)
    # play_channel.source.volume = 0.5

    name = Path(source).stem
    asyncio.run_coroutine_threadsafe(
        bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=name)),
        bot.loop)

async def connect_vc(voice):
    voice = await voice.channel.connect()
    # voice.source = discord.PCMVolumeTransformer(voice.source, volume=0.5)
    # voice.source.volume = 0.5
    return voice


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

@bot.command()
async def music(ctx, path=None):
    chan = await join_author_chan(ctx)
    if chan:
        FIRST_RUN = True
        play_next(chan)
            
@bot.command(aliases=['leave'])
async def stop(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await ctx.voice_client.disconnect()

@bot.command()
async def pause(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()

@bot.command(aliases=['play'])
async def resume(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()

@bot.command(aliases=['next'])
async def skip(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

@bot.command()
@commands.check(check_admin)
async def clear(ctx, amount=200):
    await ctx.channel.purge(limit=int(amount))
    # mgs = []
    # async for x in bot.logs_from(ctx.message.channel, limit = int(number)):
    #     mgs.append(x)
    # await bot.delete_messages(mgs)

@bot.command()
async def help(ctx):
    await ctx.send(f"""`join`, `music`, `stop`, `pause`, `resume`, `skip`""")

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
                # play_next(chan)
                break

@tasks.loop(seconds=0.05)
async def botLoop():
    global MODE_ONCE, MODE_MIX, FIRST_RUN
    message = pipe.read()
    if message:
        if len(bot.voice_clients) == 0:
            await try_connect_master()

        cmd_obj = json.loads(message)
        cmd, args = cmd_obj['cmd'], cmd_obj['args']
        if cmd in ['play', 'once', 'mix']:
            MODE_ONCE = (cmd == 'once')
            MODE_MIX = (cmd == 'mix')
            FIRST_RUN = True
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