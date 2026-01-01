import os
from openai import OpenAI
from dotenv import load_dotenv
import discord
from discord import app_commands
from prompts import prompts, moods
import asyncio
from datetime import datetime, timedelta
import bot_limiter as bl
from elevenlabs.client import ElevenLabs
import tts
import gif
import Qwen
import bot_funcs as bf
import time
import random

elevenlabs = ElevenLabs(
  api_key=os.getenv("ELEVEN_LABS_KEY"),
)

load_dotenv()

lukan_id = os.getenv("LUKAN_ID")
bot_token = os.getenv("DISCORD_TOKEN")

current_mood = random.choice(moods)

chat_session = []
last_response_time = {}

async def change_mood(moods):
    global current_mood
    while True:
        await asyncio.sleep(720) 
        new_mood = random.choice(moods)
        while new_mood == current_mood:
            new_mood = random.choice(moods)
        current_mood = new_mood
        print(f"Marlene's mood has changed to: {current_mood}")

class Marlene(discord.Client):
    def __init__(self):
        status = discord.Activity(type=discord.ActivityType.watching, name="you")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.emojis = True
        intents.emojis_and_stickers = True
        super().__init__(intents=intents, activity=status)
        self.tree = app_commands.CommandTree(self)
        self.synced = False

    async def setup_hook(self):
        asyncio.create_task(bf.reset_token_usage())
        asyncio.create_task(update_status())
        asyncio.create_task(change_mood(moods))

    async def on_ready(self):
        if self.synced:
            return
        for guild in self.guilds:
            guild_obj = discord.Object(id=guild.id)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
        self.synced = True
        print(f"Synced to {len(self.guilds)} guilds")

bot = Marlene()

client = OpenAI(
    # The API keys for the Singapore and Beijing regions are different. To obtain an API key: https://www.alibabacloud.com/help/en/model-studio/get-api-key
    api_key=os.getenv("QWEN_TOKEN"), 
    # The following is the base_url for the Singapore region. If you use a model in the Beijing region, replace the base_url with https://dashscope.aliyuncs.com/compatible-mode/v1
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)

async def update_status():
    while True:
        try:
            response = await Qwen.generate_response(f"Generate a witty and engaging Discord status (under 128 characters) based on chat context", False, chat_session, current_mood)
            '''client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "You are Marlene's assistant for generating status updates."},
                    {"role": "user", "content": }
                ]
            )'''

            await bot.change_presence(activity=discord.CustomActivity(name=response, emoji='👀'))
        except Exception as e:
            print(f"Error updating status: {e} : {response}")

        await asyncio.sleep(3600) # Update every hour




@bot.tree.command(name="mood", description="Get or set Marlene's current mood")
async def mood(interaction: discord.Interaction, mood: str = None):
    global current_mood
    if mood:
        if interaction.user.id != int(lukan_id):
            await interaction.response.send_message("Only Lukan may set my mood", ephemeral=True)
            return
        if mood.lower() in moods:
            current_mood = mood.lower()
            await interaction.response.send_message(f"Marlene's mood has been set to: {current_mood}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Invalid mood. Available moods are: {', '.join(moods)}", ephemeral=True)
    else:
        await interaction.response.send_message(f"Marlene's current mood is: {current_mood}", ephemeral=True)

@bot.tree.command(name="think", description="Use a THINK TOKEN to have Marlene think about something")
async def think_command(interaction: discord.Interaction, thought: str):
    chat = await bf.think(interaction, thought, daily_token_limit, user_token_usage)
    chat_session.append(chat)

@bot.tree.command(name="speak", description="Have Marlene speak a message using ElevenLabs")
async def speak(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    
    tts_file = await tts.text_to_speech(message, file_name=f"marlene_speak_{interaction.id}")
    if tts_file:
        embed = discord.Embed(
                            title='Marlene TTS',
                            description=message,
                            color=discord.Color.teal()
                        )
        await interaction.followup.send(embed=embed, file=discord.File(tts_file))
    else:
        await interaction.followup.send("Sorry, there was an error generating the speech.")

@bot.tree.command(name="help", description="Get a list of Marlene's commands")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(prompts["help"], ephemeral=True)

@bot.tree.command(name="delete", description="Delete a message in this channel")
async def delete_message(interaction: discord.Interaction, message_id: str):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id != int(lukan_id):
          await interaction.response.send_message(f"You are not Lukan!", ephemeral=True)
    else:
        try:
            message = await interaction.channel.fetch_message(int(message_id))
            if message:
                await message.delete()
                await interaction.followup.send(f"Message {message_id} deleted.", ephemeral=True)
            else:
                await interaction.followup.send(f"Message {message_id} not found.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error deleting message: {e}", ephemeral=True)
#=============================================#
##############MESSAGE HANDLING#################
#=============================================#
@bot.event 
async def on_message(message):
    # We do not want the bot to reply to itself
    if message.author == bot.user or message.channel.id == int(os.getenv("IGNORED_CHANNEL")):
        return
    
    # Check if Marlene is mentioned by user_id or name
    marlene_mentioned = bot.user in message.mentions or "marlene" in message.content.lower()

    should_reply = False if message.author.bot else marlene_mentioned

    if message.author.bot and marlene_mentioned:
        bot_check = bl.handle_bot_message(message.author.name)
        if bot_check == -1:
            return
        if bot_check == 0:
            pass
        if bot_check == 1:
            prompt = [{"role": "user", "content": f"this bot has sent you too many messages, respond with ultimate sass in a message to cut them off: {message.content}"}]
            response = client.chat.completions.create(
                    model="qwen-plus",
                    messages=[{"role": "system", "content": prompts["system"]}] + prompt
                )
            await message.reply(response.choices[0].message.content, mention_author=should_reply)
            return
    
    current_time = time.time()
    user_id = message.author.id 

    if message.author.bot:
        if user_id in last_response_time:
            if current_time - last_response_time[user_id] < 60:
                return

    last_response_time[user_id] = current_time

    tts_trigger = any(keyword in message.content.lower() for keyword in ["(tts)", "(speak)", "(say)"])

    gif_trigger = any(keyword in message.content.lower() for keyword in ["(gif)", "(meme)", "(jif)"])

    gif_choice = None
    if gif_trigger:
        gif_query = await Qwen.generate_response( f"Formulate a short tenorgif search query based this message for an extra sassy reply:{message.content.lower().replace("(gif)", "").replace("(meme)", "").replace("(jif)", "").strip()}", False, chat_session, current_mood)
        gif_choice = gif.get_gif(gif_query)

    if marlene_mentioned:
        if bot.user in message.mentions:
            should_respond = True
        else:
            prompt = {
                "role": "user",
                "content": f"Should Marlene respond to this message; yes or no? Message: {message.content}"
            }
            decision = client.chat.completions.create(
                model="qwen-flash",
                temperature=0.0,
                messages=[{"role": "system", "content": "You are a basic input output machine, only respond with yes or no."}, prompt]
            )
            # Parse the decision
            should_respond = "yes" in decision.choices[0].message.content.lower()

        if should_respond:
            chat_session.clear()
            msg = message;
            async for message in message.channel.history(limit=5):
                chat_session.append({"role": "user","name" : message.author.name, "content": message.content, "created_at": message.created_at.strftime("%Y-%m-%d %H:%M:%S")})
                print(f"{message.author.name}: {message.content} : {message.created_at}")

            # Debugging and validation for chat_session sorting
            print("BEFORE sorting:", chat_session)  # Debugging: Print chat_session before sorting

            chat_session.sort(key=lambda x: x['created_at'])

            print("AFTER sorting:", chat_session)  # Debugging: Print chat_session after sorting

            async with message.channel.typing():
                
                response = await Qwen.generate_response(msg, False, chat_session, current_mood)
                
                if tts_trigger:
                    tts_file = await tts.text_to_speech(response, file_name=f"marlene_reply_{message.id}")
                    if tts_file:
                        embed = discord.Embed(
                            title='Marlene TTS',
                            description=response,
                            color=discord.Color.teal()
                        )
                        await message.reply(embed=embed, file=discord.File(tts_file), mention_author=should_reply)
                    else:
                        await message.reply("Sorry, there was an error generating the speech.", mention_author=should_reply)
                else:
                    chunks = await bf.split_string(response)
                    for index, chunk in enumerate(chunks):
                        if index == 0:
                            if gif_choice is not None:
                                await message.reply(f"{chunk} [gif]({gif_choice})", mention_author=should_reply)
                            else:
                                await message.reply(chunk, mention_author=should_reply)
                        else:
                            await message.reply(chunk, mention_author=False)
                


# Load token usage on startup
# Token usage tracker
user_token_usage = {}
daily_token_limit = 5  # Set the daily token limit

bf.load_token_usage()

bot.run(bot_token)