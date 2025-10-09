import requests
import os
from dotenv import load_dotenv

load_dotenv()
'''
function request_gif(_q)
{
	global.gif_request := http_get($"https://tenor.googleapis.com/v2/search?key={global.gif_token}&q={__discord_url_encode(_q)}&contentfilter=medium&media_filter=tinygif&random=true&limit=1");
}
'''
gif_token = os.getenv("TENOR_TOKEN")

def get_gif(query):
    try:
        response = requests.get(f"https://tenor.googleapis.com/v2/search?key={gif_token}&q={query}&contentfilter=medium&media_filter=tinygif&random=true&limit=1")
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()
        if 'results' in data and len(data['results']) > 0:
            return data['results'][0]['media_formats']['tinygif']['url']
        else:
            return "No GIF found."
    except requests.RequestException as e:
        return f"Error fetching GIF: {e}"