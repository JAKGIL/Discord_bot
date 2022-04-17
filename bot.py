# bot.py
import argparse
from glob import glob
import os
from socket import timeout
from termios import CLNEXT
import time
from waiting import wait, TimeoutExpired
import asyncio

import discord
from discord import FFmpegPCMAudio
from dotenv import load_dotenv
from discord.ext import commands,tasks
import urllib
import re
import youtube_dl
import pafy
import requests

# Queue 
queue = []
queue_titles = []

# Global var to check if user want to skip while queue is on
wantToSkip = False


FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn'}

# Youtube settings 
ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # Bind to ipv4 since ipv6 addresses cause issues sometimes
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)# Set format options


load_dotenv() # Load an env
TOKEN = os.getenv('DISCORD_TOKEN')# Get token

bot = commands.Bot(command_prefix='!')# Set prefix


@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    """Command to conect bot to voice chanel

    Args:
      ctx - a user settings where he is etc.

    Returns:
      Nothing, just connect bot to channel 
    """    
    if not ctx.message.author.voice: # If user is not conected to voice channel
        await ctx.send("Sorry but you're not connected to any channel")
        return
    else: 
         channel = ctx.message.author.voice.channel
    await channel.connect() # If he is, connect to channel

@bot.command(name='leave', help='Tells the bot to leave the current voice channel')
async def leave(ctx):
    """Disconect bot from chanell

    Args:
      ctx - a user settings where he is etc.

    Returns:
      Nothing, but bot leaves channel
    """  
    channel = ctx.guild.voice_client
    await channel.disconnect() 
    await ctx.send('Bye bye :wave:')
    queue.clear()
    queue_titles.clear()

@bot.command(name='play', help='Adding song to queue')
async def add(ctx, *msg_got):
    """Add a song to queue and plays it when there 
    is no song in queue
    Args:
      ctx - a user settings where he is etc.
      *msg_got - a tuple with each word that user
                typed when using "play" command
    Returns:
      Nothing
    """  

    msg = "" # We create a msg form messages we got
    i = 0
    while i < len(msg_got):
        msg = msg + msg_got[i] + "+"
        i += 1
    # When it's url it's just url with "+" at the end
    # Youtube seems to accept this so, well...

    if not ctx.message.author.voice: # If user is not connected to any channel, send:
        await ctx.send("Sorry but you're not connected to any channel")
        return
    
    else:
        try:
            await join(ctx=ctx)
        finally:

            server = ctx.message.guild
            voice_channel = server.voice_client

            try: # If it's a url
                song = pafy.new(msg)  # Creates a new pafy object
            except: #If it's just worlds
                # Make a html version of site form url 
                html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + msg)
                # Seach for url that contains "watch....", then decode it to string
                video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())

                #Create url to song
                song_link = "https://www.youtube.com/watch?v=" + video_ids[0]
                song = pafy.new(song_link)

            audio = song.getbestaudio()  # Gets an audio source

            queue.append(audio.url)
            queue_titles.append(song.title)

            # Things to send to user
            await ctx.send("Adding to queue:") 
            await ctx.send(song.title)

            # If nothing is playing now, start playing a queue
            if not (ctx.voice_client.is_playing()):
                await play(ctx=ctx)


async def play(ctx):
    """Plays a queue

    Args:
      ctx - a user settings where he is etc.

    Returns:
      Nothing
    """ 
    server = ctx.message.guild
    voice_channel = server.voice_client
    
    # We have to get acces to global queue if we want to modify it 
    # later 
    global queue 
    global queue_titles

    theteIsMore = True # Var to chck if there is more songs in queue
    global wantToSkip # Acces to global var
    i = 0 

    # Little disclamer, we always want bot to wait for next song
    # even when it's no more in queue right now.
    # It's becouse a user will ofen add a new song when there is 
    # no more songs in queue.
    # "try" will make a job here. Becouse we can get "list out 
    # of index"
    while theteIsMore and (not wantToSkip): #main loop while plaing
        
        while (ctx.voice_client.is_playing() and (not wantToSkip)):
            await asyncio.sleep(1) #Waiting for end of currnet song
        
        if i >= len(queue):
            theteIsMore = False
        
        if wantToSkip: # If you want to skip there is exception
            if i == len(queue): # If you are at the end, just clear queue
                queue.clear()
                queue_titles.clear()
            voice_channel.stop() # Stop music and go to next song
            wantToSkip = False # Set to false to prevent stopping the loop
        
        try: # Try to play next song
            source = discord.FFmpegPCMAudio(source=queue[i], **FFMPEG_OPTIONS)
            voice_channel.play(source=source, after=voice_channel.stop())
        except: # If you can't probably it's end of a queue (or an error)
                # so clear a queue
            queue.clear()
            queue_titles.clear()
        finally:
            i += 1
            time.sleep(2) # Wait for a moment after changing a song
                          # if not, somtimes it generate error
    

@bot.command(name='que', help='Showing a queue')
async def queue_check(ctx):
    """Shows a queue after call

    Args:
      ctx - a user settings where he is etc.

    Returns:
      Nothing
    """ 
    for i in range(len(queue_titles)):
        await ctx.send(str(i+1) + ' ' + queue_titles[i])

@bot.command(name='skip', help='Skip a current song')
async def skip_song(ctx):
    """Changes wantToSkip to true after a !skip 
    commend

    Args:
      ctx - a user settings where he is etc.

    Returns:
      Nothing
    """ 
    global wantToSkip
    wantToSkip= True

bot.run(TOKEN) #join server as bot