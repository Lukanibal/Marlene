import discord
import Qwen
import json
import asyncio

#split a string into 1500 character chunks
async def split_string(input_string):
# Check if the string length is greater than 1500
    if len(input_string) > 1500:
        # Split the string into chunks of 1500 characters
        chunks = [input_string[i:i + 1500] for i in range(0, len(input_string), 1500)]
        return chunks
    else:
        # Return the original string if it's 1500 characters or less
        return [input_string]


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



async def think(interaction: discord.Interaction, thought: str, chat_session=[]):
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

    # Process the think command
    await interaction.response.defer()
    answer_content = await Qwen.generate_response(thought, think=True)

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
    
    return chat_session

    #await interaction.followup.send(f"{answer_content}")