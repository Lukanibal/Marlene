# Straight up stolen from Evanski's repo
# found here: https://github.com/EvanSkiStudios/marcojr/blob/main/colt/tools/elevenlabs_voice.py
import asyncio
import os
import re

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play, VoiceSettings
from elevenlabs.core.api_error import ApiError


# Load Env
load_dotenv()
API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

client = ElevenLabs(
    api_key=f"{API_KEY}"
)


def clean_text(text: str) -> str:
    # Remove *...* and [...] including the markers
    cleaned = re.sub(r"(\*.*?\*|\[.*?\])", "", text)
    # Remove specific symbols
    cleaned = re.sub(r"[!?\@$%^&\";:]", "", cleaned)
    # Remove extra spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Limit to at most 10 characters
    if cleaned == "":
        cleaned = 'text_to_speech'
    return cleaned[:14]


async def text_to_speech(text: str, file_name='text_to_speech'):
    print(f"Starting TTS Message")

    def _blocking_tts():
        try:
            audio = client.text_to_speech.convert(
                text=text,
                voice_id=VOICE_ID,
                model_id="eleven_flash_v2_5",
                output_format="mp3_44100_128",
                voice_settings=VoiceSettings(
                    stability=0.0,
                    similarity_boost=1.0,
                    style=0.0,
                    use_speaker_boost=True,
                    speed=1.0,
                ),
            )

            # Collect into bytes
            audio_bytes = b"".join(audio)

            # Save to file
            file_path = f"{clean_text(file_name)}.mp3"
            with open(file_path, "wb") as f:
                f.write(audio_bytes)

            print(f"✅ Audio saved as {os.path.abspath(file_path)}")
            return os.path.abspath(file_path)

        except ApiError as e:
            print(
                f"API Error while generating TTS: {e}\n"
                f"Status code: {e.status_code}\n"
                f"Response body: {e.body}"
            )
            return None
        except Exception as e:
            print(f"Unexpected error during TTS: {e}")
            return None

    # Run the blocking code in a separate thread
    file_path = await asyncio.to_thread(_blocking_tts)
    return file_path


# Optional: play it too
# if file_path:
#     with open(file_path, "rb") as f:
#         play(f.read())