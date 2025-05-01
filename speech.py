# speech.py

import speech_recognition as sr
import os
from dotenv import load_dotenv
from elevenlabs import ElevenLabs

# Load API key from .env file
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Initialize ElevenLabs client
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Store the last speech recognition result
last_recognition_result = None

__all__ = ['speak', 'listen']

def speak(text, voice_id="21m00Tcm4TlvDq8ikWAM"):  # Default to Rachel voice
    """
    Convert text to speech using ElevenLabs API and return audio data for Streamlit.
    Uses the latest API parameters for optimal quality and performance.
    """
    try:
        print(f"[TTS] Starting text-to-speech conversion for text: {text[:50]}...")
        print(f"[TTS] Using voice ID: {voice_id}")
        
        # Convert text to speech using ElevenLabs client
        print("[TTS] Calling ElevenLabs API...")
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            optimize_streaming_latency=0,  # No latency optimization for best quality
            apply_text_normalization="auto",  # Auto text normalization
            apply_language_text_normalization=False,  # No language-specific normalization
            use_pvc_as_ivc=False,  # Use PVC version for better quality
            voice_settings={
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        )
        print("[TTS] Received audio generator from API")
        
        # Convert generator to bytes
        print("[TTS] Converting audio generator to bytes...")
        audio_data = b"".join(chunk for chunk in audio_generator)
        print(f"[TTS] Generated audio data size: {len(audio_data)} bytes")
        
        # For testing outside of Streamlit
        if __name__ == "__main__":
            print("[TTS] Testing audio playback...")
            with open("temp_audio.mp3", "wb") as f:
                f.write(audio_data)
            print("[TTS] Saved audio to temp_audio.mp3")
            os.system("start temp_audio.mp3")  # For Windows
            print("[TTS] Started audio playback")
            os.remove("temp_audio.mp3")
            print("[TTS] Cleaned up temporary file")
        
        print("[TTS] Successfully generated audio data")
        return audio_data
            
    except Exception as e:
        print(f"[TTS ERROR] {str(e)}")
        print(f"[TTS ERROR] Error type: {type(e)}")
        import traceback
        print(f"[TTS ERROR] Traceback: {traceback.format_exc()}")
        return None

def listen(timeout=5, phrase_time_limit=10):
    """
    Listen to the user's speech using microphone and convert to text using ElevenLabs.
    Returns the transcribed text as a string, while storing additional information in last_recognition_result.
    """
    global last_recognition_result
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening... (Speak now)")
        try:
            # Record audio
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            
            # Save audio to temporary file
            with open("temp_speech.wav", "wb") as f:
                f.write(audio.get_wav_data())
            
            # Convert speech to text using ElevenLabs
            with open("temp_speech.wav", "rb") as audio_file:
                result = client.speech_to_text.convert(
                    model_id="scribe_v1",  # Using Scribe model
                    file=audio_file,
                    language_code="en",  # Force English language
                    timestamps_granularity="word",  # Get word-level timestamps
                    tag_audio_events=True,  # Tag audio events like laughter
                    diarize=True  # Annotate speaker information
                )
            
            # Clean up temporary file
            os.remove("temp_speech.wav")
            
            if result and result.text:
                print(f"User: {result.text}")
                # Store the full result for later access
                last_recognition_result = {
                    "text": result.text,
                    "language_code": result.language_code,
                    "language_probability": result.language_probability,
                    "words": result.words if hasattr(result, 'words') else None
                }
                # Return just the text content
                return result.text
            else:
                print("[STT] No text detected.")
                last_recognition_result = None
                return "Sorry, I didn't catch that."
                
        except sr.WaitTimeoutError:
            print("[STT] Listening timed out.")
            last_recognition_result = None
            return "Sorry, I didn't hear anything."
        except sr.UnknownValueError:
            print("[STT] Could not understand audio.")
            last_recognition_result = None
            return "Sorry, I didn't catch that."
        except Exception as e:
            print(f"[STT ERROR] {e}")
            last_recognition_result = None
            return "Sorry, speech recognition service failed."

def get_last_recognition_details():
    """
    Returns the full details of the last speech recognition result.
    """
    return last_recognition_result

if __name__ == "__main__":
    # Test the functions
    audio_data = speak("Hello, this is a test.")
    response = listen()
    print(f"Response: {response}")
    if last_recognition_result:
        print("Full details:", last_recognition_result)
