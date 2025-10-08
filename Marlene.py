import os
from openai import OpenAI
from dotenv import load_dotenv
import discord
from discord import app_commands
from prompts import prompts
import requests

load_dotenv()

bot_token = os.getenv("DISCORD_TOKEN")

class Marlene(discord.Client):
    def __init__(self):
        status = discord.Activity(type=discord.ActivityType.watching, name="over you")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.emojis = True
        intents.emojis_and_stickers = True
        super().__init__(intents=intents, activity=status)
        self.tree = app_commands.CommandTree(self)
        self.synced=False

    async def setup_hook(self):
        #put em here
        pass

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


#=============================================#
##############MESSAGE HANDLING#################
#=============================================#
@bot.event 
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == bot.user:
        return
    
    '''if message.author.bot:
        bot_check = bl.handle_bot_message(message.author.name)
        if bot_check == -1:
            return
        if bot_check == 0:
            pass'''
    
     # Check if the bot is mentioned in the message

    #if bot.user in message.mentions:
    async with message.channel.typing():
        msg = message.content.replace(f"<@{bot.user.id}>", "")
        prompt = {'role': 'user', 'name': message.author.global_name, "content": f"This message is from the user {message.author.global_name}: {msg}"}
        if message.attachments:
            # Filter for image attachments
            image_attachments = [attachment for attachment in message.attachments if attachment.content_type and attachment.content_type.startswith('image/')]

            if image_attachments:
                image_url = image_attachments[0].url
                # Download the image
                response = requests.get(image_url)
                if response.status_code == 200:
                    # Save the image to a file
                    file_path = os.path.join("images", image_attachments[0].filename)  # Specify the directory and filename
                    os.makedirs("images", exist_ok=True)  # Create the directory if it doesn't exist

                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    prompt = {'role': 'user', 'name': message.author.global_name, 'content': f"This message is from the user {message.author.global_name}: {msg}", 'images': [file_path]}
                    
        completion = client.chat.completions.create(
        model="qwen-plus", # Model list: https://www.alibabacloud.com/help/en/model-studio/getting-started/models
        messages=[{"role": "system", "content": prompts["system"]},
        prompt])
        await message.reply(completion.choices[0].message.content, mention_author=True)


            



bot.run(bot_token)