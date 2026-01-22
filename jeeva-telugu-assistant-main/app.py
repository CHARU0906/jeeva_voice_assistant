import streamlit as st
import sounddevice as sd
import wave
import tempfile
import os
import json
import difflib
from gtts import gTTS
import pygame
import time
from vosk import Model, KaldiRecognizer

# Load Vosk model once
@st.cache_resource
def load_model():
    model_path = "model"
    if not os.path.exists(model_path):
        st.error("Vosk model not found. Please download and extract it to a folder named 'model'")
        st.stop()
    return Model(model_path)

model = load_model()
samplerate = 16000
duration = 5  # seconds

# 🎧 Record audio
def record_audio():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
        file_path = tmpfile.name
    recording = sd.rec(int(samplerate * duration), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()
    with wave.open(file_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(recording.tobytes())
    return file_path

# 🧠 Recognize with Vosk
def recognize_audio(wav_path):
    rec = KaldiRecognizer(model, samplerate)
    rec.SetWords(True)
    with wave.open(wav_path, "rb") as wf:
        rec.AcceptWaveform(wf.readframes(wf.getnframes()))
        final_result = json.loads(rec.FinalResult())
    return final_result.get("text", "")

# 🧠 Correct common misrecognitions
def improve_recognition(text):
    corrections_map = {
        "vash": "varsham", "vasham": "varsham", "versham": "varsham",
        "help": "sahayam", "helo": "namaskaram", "fertalizer": "eruvu",
        "price": "dhara", "desease": "vyadi", "varsha": "varsham"
    }
    words = text.lower().split()
    for i, word in enumerate(words):
        for wrong, correct in corrections_map.items():
            if difflib.SequenceMatcher(None, word, wrong).ratio() > 0.75:
                words[i] = correct
                return " ".join(words)
    return text

# 🤖 Generate response
def generate_response(text):
    if "varsham" in text:
        return "నేడు వర్షం పడే అవకాశం 60% ఉంది."
    elif "sahayam" in text:
        return "నేను వ్యవసాయంపై సహాయం చేస్తాను."
    elif "eruvu" in text:
        return "ఈ పంటకు ఆర్గానిక్ ఎరువులు వాడండి."
    elif "vyadi" in text:
        return "నీం ఆయిల్ వాడండి వ్యాధులు నివారించేందుకు."
    elif "dhara" in text:
        return "ఈ రోజు ధర రూ.20 కిలోకు ఉంది."
    elif "namaskaram" in text:
        return "నమస్తే! నేను జీవ, మీకు సహాయం చేస్తాను."
    else:
        return "దయచేసి మరింత స్పష్టంగా చెప్పండి."

# 🔈 Speak response
def speak(text):
    tts = gTTS(text=text, lang='te')
    temp_mp3 = os.path.join(tempfile.gettempdir(), "response.mp3")
    tts.save(temp_mp3)
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(temp_mp3)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        st.error(f"Audio playback failed: {e}")

# 🎯 Streamlit UI
st.title("🗣️ Jeeva Telugu Voice Assistant (Web Demo)")
st.markdown("Click below to record your voice in Telugu. Jeeva will understand and reply accordingly.")

if st.button("🎙️ Speak Now"):
    with st.spinner("Recording..."):
        wav_path = record_audio()
    with st.spinner("Processing..."):
        raw_text = recognize_audio(wav_path)
        improved_text = improve_recognition(raw_text)
        response = generate_response(improved_text)
    st.success("✅ Done")
    st.write(f"**You said:** {improved_text}")
    st.write(f"**Jeeva says:** {response}")
    speak(response)
