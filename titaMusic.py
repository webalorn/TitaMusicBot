import asyncio
import os
import json
from collections import deque

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

# ========== BOT ==========

bot = commands.Bot(command_prefix='Tita ', help_command=None)

TEST_FILE = "/Volumes/Alveran/jdr/music/@settings/demon-lord/ambiance/calme/ASKII - Reach.mp3"
song_queue = deque([str(dir_path / '__private__/celtic.opus')])

def play_next(play_channel):
    source = song_queue.popleft()
    song_queue.append(source)
    play_channel.play(discord.FFmpegPCMAudio(source=source), after=lambda e: play_next(play_channel))

    name = Path(source).stem
    asyncio.run_coroutine_threadsafe(
        bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=name)),
        bot.loop)

async def join_author_chan(ctx):
    if ctx.author.voice is None:
        await ctx.send(f"{ctx.author.mention} you should be in an audio channel!")
    elif not ctx.voice_client or ctx.voice_client.channel.id != ctx.author.voice.channel.id:
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        return await ctx.author.voice.channel.connect()

@bot.command()
async def join(ctx):
    await join_author_chan(ctx)

@bot.command()
async def music(ctx, path=None):
    chan = await join_author_chan(ctx)
    if chan:
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
async def help(ctx):
    await ctx.send(f"""`join`, `music`, `stop`, `pause`, `resume`, `skip`""")

@tasks.loop(seconds=0.05)
async def botLoop():
    message = pipe.read()
    if message:
        files = json.loads(message)
        if files:
            song_queue.clear()
            song_queue.extend(files)
            for vc in bot.voice_clients:
                if vc.is_playing():
                    vc.stop()
                else:
                    play_next(vc)

@bot.event
async def on_ready():
    print('Bot logged in as {0.user}'.format(bot))

    if 'admin_id' in CONFIG:
        guilds = bot.guilds
        for guild in guilds:
            try:
                member = await guild.fetch_member(CONFIG['admin_id'])
            except discord.errors.NotFound:
                continue
            if member.voice:
                chan = await member.voice.channel.connect()
                # play_next(chan)
                break

def main():
    botLoop.start()
    try:
        bot.run(CONFIG['token'])
    except KeyboardInterrupt:
        bot.logout()
        bot.close()

if __name__ == "__main__":
    main()