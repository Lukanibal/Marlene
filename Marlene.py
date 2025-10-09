import os
from openai import OpenAI
from dotenv import load_dotenv
import discord
from discord import app_commands
from prompts import prompts
import requests
import asyncio
import json
from datetime import datetime, timedelta
import random
import bot_limiter as bl
from elevenlabs.client import ElevenLabs
from elevenlabs import save
import tts
import gif
import LLM

elevenlabs = ElevenLabs(
  api_key=os.getenv("ELEVEN_LABS_KEY"),
)


load_dotenv()

lukan_id = int(os.getenv("LUKAN_ID"))
bot_token = os.getenv("DISCORD_TOKEN")

chat_session = []

class Marlene(discord.Client):
    def __init__(self):
        status = discord.Activity(type=discord.ActivityType.watching, name="over you")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.emojis = True
        intents.emojis_and_stickers = True
        super().__init__(intents=intents, activity=status)
        self.tree = app_commands.CommandTree(self)
        self.synced = False

    async def setup_hook(self):
        # Start the background task to reset token usage
        asyncio.create_task(reset_token_usage())
        # Start the background task to update status
        asyncio.create_task(update_status())

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

# File to store token usage
TOKEN_USAGE_FILE = "user_token_usage.json"

# Token usage tracker
user_token_usage = {}
daily_token_limit = 5  # Set the daily token limit

# Load token usage from JSON file
def load_token_usage():
    global user_token_usage
    try:
        with open(TOKEN_USAGE_FILE, "r") as file:
            user_token_usage = json.load(file)
    except FileNotFoundError:
        user_token_usage = {}
    except json.JSONDecodeError:
        print("Error: Token usage file is corrupted. Resetting token usage.")
        user_token_usage = {}

# Save token usage to JSON file
def save_token_usage():
    with open(TOKEN_USAGE_FILE, "w") as file:
        json.dump(user_token_usage, file)

# Background task to reset token usage daily
async def reset_token_usage():
    while True:
        await asyncio.sleep(24 * 60 * 60)  # Wait for 24 hours
        user_token_usage.clear()
        save_token_usage()
        print("Token usage has been reset.")

# List to track recent interactions
recent_interactions = []

# Function to add a new interaction to the list
def add_interaction(interaction):
    if len(recent_interactions) >= 10:  # Limit the list to 10 items
        recent_interactions.pop(0)
    recent_interactions.append(interaction)

# Background task to update Marlene's status using the LLM
async def update_status():
    while True:
        try:
            # Collect recent conversational context (example: last 5 interactions)
            context = "\n".join(recent_interactions[-5:]) if recent_interactions else "No recent interactions."

            # Query the LLM for a new status
            response = client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "You are Marlene's assistant for generating status updates."},
                    {"role": "user", "content": f"Generate a Discord status based on the following context: {context}"}
                ]
            )

            # Extract the generated status
            new_status = response.choices[0].message.content.strip()

            # Update Marlene's status
            await bot.change_presence(activity=discord.CustomActivity(name=new_status))
        except Exception as e:
            print(f"Error updating status: {e}")

        await asyncio.sleep(300)  # Update every 5 minutes


async def split_string(input_string):
# Check if the string length is greater than 1500
    if len(input_string) > 1500:
        # Split the string into chunks of 1500 characters
        chunks = [input_string[i:i + 1500] for i in range(0, len(input_string), 1500)]
        return chunks
    else:
        # Return the original string if it's 1500 characters or less
        return [input_string]


@bot.tree.command(name="think", description="Use a THINK TOKEN to have Marlene think about something")
async def think(interaction: discord.Interaction, thought: str):
    user_id = str(interaction.user.id)  # Use string keys for JSON compatibility

    # Initialize token usage for the user if not already present
    if user_id not in user_token_usage:
        user_token_usage[user_id] = 0

    # Check if the user has exceeded their daily limit
    if user_token_usage[user_id] >= daily_token_limit:
        await interaction.response.send_message(
            f"Sorry, {interaction.user.mention}, you have reached your daily token limit of {daily_token_limit}. Please try again tomorrow.",
            ephemeral=True
        )
        return

    # Increment token usage (assuming 1 token per command; adjust as needed)
    user_token_usage[user_id] += 1
    save_token_usage()  # Save the updated token usage

    # Add the interaction to the recent interactions list
    add_interaction(f"User thought: {thought[:50]}...")

    # Process the think command
    await interaction.response.defer()
    answer_content = await LLM.generate_response(thought, think=True)

    chat_session.append({"role": "user", "content": thought})
    chat_session.append({"role": "assistant", "content": answer_content})
    if len(chat_session) > 10:  # Limit chat session history to last 10 messages
        chat_session.pop(0)
    # Send the full response back to the user
    chunks = await split_string(answer_content)
    for index, chunk in enumerate(chunks):
        if index == 0:
            await interaction.followup.send(chunk)
        else:
            await interaction.channel.send(chunk)

    #await interaction.followup.send(f"{answer_content}")

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
    if interaction.user.id != lukan_id:
          await interaction.response.send_message(f"You are not Lukan!", ephemeral=True)
    try:
        message = await interaction.channel.fetch_message(int(message_id))
        if message:
            await message.delete()
            await interaction.response.send_message(f"Message {message_id} deleted.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Message {message_id} not found.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Error deleting message: {e}", ephemeral=True)
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

    if message.author.bot and marlene_mentioned:
        bot_check = bl.handle_bot_message(message.author.name)
        if bot_check == -1:
            return
        if bot_check == 0:
            pass
        if bot_check == 1:
            prompt = [{"role": "user", "content": f"this bot has sent you too many messages, respond with ultimate sass to thier last message: {message.content}"}]
            response = client.chat.completions.create(
                    model="qwen-plus",
                    messages=[{"role": "system", "content": prompts["system"]}] + prompt
                )
            await message.reply(response.choices[0].message.content, mention_author=True)
            return
    

    tts_trigger = any(keyword in message.content.lower() for keyword in ["(tts)", "(speak)", "(say)"])
    # Analyze the message content
    if marlene_mentioned:
        # Use a language model to decide if Marlene should respond
        prompt = {
            "role": "user",
            "content": f"Should Marlene respond to this message; yes or no? Message: {message.content}"
        }
        decision = client.chat.completions.create(
            model="qwen-flash",
            messages=[{"role": "system", "content": "You are a basic input output machine, only respond with yes or no."}, prompt]
        )

        # Parse the decision
        should_respond = "yes" in decision.choices[0].message.content.lower()

        if should_respond:
            async with message.channel.typing():
                # Generate a response
                response_prompt = {
                    "role": "user",
                    "content": f"Marlene, respond to this message: {message.content}"
                }
                chat_session.append(response_prompt)
    
                response = await LLM.generate_response(message.content)

                chat_session.append({"role": "assistant", "content": response})
                if len(chat_session) > 10:  # Limit chat session history to last 10 messages
                    chat_session.pop(0)
                
                # Send the response
                if tts_trigger:
                    tts_file = await tts.text_to_speech(response, file_name=f"marlene_reply_{message.id}")
                    if tts_file:
                        embed = discord.Embed(
                            title='Marlene TTS',
                            description=response,
                            color=discord.Color.teal()
                        )
                        await message.reply(embed=embed, file=discord.File(tts_file), mention_author=True)
                    else:
                        await message.reply("Sorry, there was an error generating the speech.", mention_author=True)
                else:
                    chunks = await split_string(response)
                    for index, chunk in enumerate(chunks):
                        if index == 0:
                            await message.reply(chunk, mention_author=True)
                        else:
                            await message.reply(chunk, mention_author=False)
                


# Load token usage on startup
load_token_usage()

bot.run(bot_token)