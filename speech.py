# speech.py

import speech_recognition as sr
from elevenlabs import generate, play, set_api_key
import os
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
set_api_key(os.getenv("ELEVENLABS_API_KEY"))

def speak(text, voice_name="Rachel"):
    """
    Convert text to speech using ElevenLabs and play the audio.
    """
    try:
        print(f"AI: {text}")
        audio = generate(text=text, voice=voice_name)
        play(audio)
    except Exception as e:
        print(f"[TTS ERROR] {e}")

def listen(timeout=5, phrase_time_limit=10):
    """
    Listen to the user's speech using microphone and convert to text.
    """
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening... (Speak now)")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            user_input = recognizer.recognize_google(audio)
            print(f"User: {user_input}")
            return user_input
        except sr.WaitTimeoutError:
            print("[STT] Listening timed out.")
            return "Sorry, I didn’t hear anything."
        except sr.UnknownValueError:
            print("[STT] Could not understand audio.")
            return "Sorry, I didn’t catch that."
        except sr.RequestError as e:
            print(f"[STT ERROR] {e}")
            return "Sorry, speech recognition service failed."
