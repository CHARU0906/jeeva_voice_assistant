import os
import sys
import difflib
import time # Added for sleep to ensure audio playback

print("🔥 main.py is starting")

# Clear any existing Kivy environment variables that might cause conflicts
kivy_env_vars = [
    'KIVY_METRICS_DENSITY', 'KIVY_WINDOW', 'KIVY_GL_BACKEND',
    'KIVY_AUDIO', 'KIVY_IMAGE', 'KIVY_TEXT', 'KIVY_CLIPBOARD'
]

for var in kivy_env_vars:
    if var in os.environ:
        del os.environ[var]

# Set minimal required environment variables
os.environ["KIVY_NO_CONSOLELOG"] = "1"

# Increase recursion limit
sys.setrecursionlimit(10000)

try:
    print("📦 Importing model_loader...")
    from model_loader import ensure_model
    print("✅ model_loader imported successfully")
except ImportError as e:
    print(f"❌ Failed to import model_loader: {e}")
    exit(1)

try:
    print("📦 Importing vosk...")
    import vosk
    print("✅ vosk imported successfully")
except ImportError as e:
    print(f"❌ Failed to import vosk: {e}")
    exit(1)

try:
    print("📦 Importing other libraries...")
    import wave
    import json
    import sounddevice as sd
    import tempfile
    import threading
    from gtts import gTTS
    import re
    print("✅ All basic libraries imported successfully")
except ImportError as e:
    print(f"❌ Failed to import basic libraries: {e}")
    exit(1)

try:
    print("📦 Importing Kivy (clean import)...")
    
    # Import Kivy components one by one to identify the problematic one
    print("   - Importing base kivy...")
    import kivy
    
    print("   - Setting kivy requirements...")
    kivy.require('2.0.0')
    
    print("   - Importing kivy.app...")
    from kivy.app import App
    
    print("   - Importing kivy.uix.boxlayout...")
    from kivy.uix.boxlayout import BoxLayout
    
    print("   - Importing kivy.uix.button...")
    from kivy.uix.button import Button
    
    print("   - Importing kivy.uix.label...")
    from kivy.uix.label import Label
    
    print("✅ Kivy imported successfully")
except Exception as e:
    print(f"❌ Kivy import error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("🎯 All imports successful, proceeding with UI...")

class JeevaUI(BoxLayout):
    def __init__(self, **kwargs):
        print("📦 Initializing UI")
        super(JeevaUI, self).__init__(orientation="vertical", **kwargs)

        self.label = Label(text="Telugu lo matladataniki tap cheyandi", font_size=18)
        self.add_widget(self.label)

        self.btn = Button(text="🎙️ Matladandi", font_size=20, size_hint=(1, 0.3))
        self.btn.bind(on_press=self.start_listening)
        self.btn.bind(on_release=self.button_released)
        self.add_widget(self.btn)
        
        # Add keyboard support
        from kivy.core.window import Window
        Window.bind(on_key_down=self.on_key_down)

        try:
            print("📦 Loading Vosk model...")
            self.model_path = ensure_model()
            self.model = vosk.Model(self.model_path)
            print("✅ Vosk model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            self.label.text = f"❌ Failed to load model: {e}"
            return

        # Use optimal settings for Telugu recognition
        self.samplerate = 16000  # Standard rate
        self.duration = 10
        
        # Set up audio with better quality - MODIFIED SECTION
        try:
            # Set the default host API to WASAPI for Windows
            # You can check available host APIs with sd.query_hostapis()
            # Find the index for 'Windows WASAPI' or 'WASAPI'
            wasapi_index = -1
            for i, api in enumerate(sd.query_hostapis()):
                if 'WASAPI' in api['name']:
                    wasapi_index = i
                    break
            
            if wasapi_index != -1:
                sd.default.hostapi = wasapi_index
                print(f"📱 Set default host API to WASAPI (Index: {wasapi_index})")
            else:
                print("📱 WASAPI host API not found. Using default behavior.")

            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            
            if input_devices:
                # Filter for the specific device name and then choose by API if needed
                # Or, if WASAPI is set as default host API, sounddevice should pick the WASAPI version
                
                # Let's try to pick the first one that matches the name if multiple exist
                # This is a fallback if WASAPI default doesn't auto-resolve
                target_device_name = "Microphone Array (AMD Audio Device)"
                
                filtered_devices = [d for d in input_devices if target_device_name in d['name']]
                
                if filtered_devices:
                    # Prefer the WASAPI version if available
                    wasapi_device = next((d for d in filtered_devices if 'WASAPI' in d['name']), None)
                    if wasapi_device:
                        sd.default.device = (wasapi_device['name'], sd.default.device[1])
                        self.samplerate = int(wasapi_device['default_samplerate']) 
                        print(f"📱 Selected '{wasapi_device['name']}' using WASAPI.")
                    else:
                        # Fallback to the first found device with that name
                        first_matching_device = filtered_devices[0]
                        sd.default.device = (first_matching_device['name'], sd.default.device[1])
                        self.samplerate = int(first_matching_device['default_samplerate'])
                        print(f"📱 Selected '{first_matching_device['name']}' (first match).")
                else:
                    print(f"📱 No device matching '{target_device_name}' found. Using system default.")
            else:
                print("📱 No input devices found with max_input_channels > 0. Using system default.")

        except Exception as e:
            print(f"📱 Could not optimize audio device: {e}. Fallback to default audio settings.")
        
        # List available audio devices for debugging (this will now show which one is selected by default)
        print("📱 Available audio devices:")
        for i, device in enumerate(sd.query_devices()):
            if device['max_input_channels'] > 0:
                is_default = "*" if i == sd.default.device[0] else " " # Mark default device
                print(f" {is_default}{i}: {device['name']} (inputs: {device['max_input_channels']}) [Host API: {sd.query_hostapis(device['hostapi'])['name']}]")

        print("📱 Audio setup complete")
    
    def button_released(self, instance):
        print("Button released - this confirms button is working")
        
    def on_key_down(self, window, keycode, text, modifiers, scancode):
        # Press SPACE or ENTER to start listening
        if keycode in [32, 13]:  # 32 = space, 13 = enter
            self.start_listening(None)
            return True
        return False

    def start_listening(self, instance):
        print("🎤 Start listening triggered!")
        self.label.text = "🎧 Vintunna... Dayachesi matladandi!"
        self.btn.text = "🔴 Record chesthunna..."
        self.btn.disabled = True
        threading.Thread(target=self.record_and_process).start()

    def record_and_process(self):
        try:
            duration = self.duration
            print(f"🎤 Recording for {duration} seconds...")
            
            audio = sd.rec(int(self.samplerate * duration), 
                            samplerate=self.samplerate,
                            channels=1, 
                            dtype='int16',
                            blocking=True) # Keep blocking for simplicity with short commands
            sd.wait() # Ensure recording is complete
            print("🎤 Recording completed")

            # Create WAV file with better quality
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
                wav_file = tmpfile.name
                with wave.open(wav_file, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self.samplerate)
                    wf.writeframes(audio.tobytes())

            print("🎤 Processing audio with Vosk...")
            
            # Process with Vosk - simplified to process the whole audio for short clips
            with wave.open(wav_file, "rb") as wf:
                rec = vosk.KaldiRecognizer(self.model, self.samplerate)
                
                # Enable word-level timestamps and confidence
                rec.SetWords(True)
                
                # Read all audio frames at once
                data = wf.readframes(wf.getnframes())
                
                # Accept the waveform
                rec.AcceptWaveform(data)
                
                # Get raw and parsed results for debugging
                raw_result = rec.Result()
                print(f"🎤 RAW Vosk result: {raw_result}")
                result = json.loads(raw_result)
                
                raw_final_result = rec.FinalResult()
                print(f"🎤 RAW Vosk FinalResult: {raw_final_result}")
                final_result = json.loads(raw_final_result)

                # Combine results
                # Prioritize FinalResult as it often has a more complete utterance
                recognized_text = final_result.get("text", "").strip()
                if not recognized_text and "text" in result: # Fallback if final is empty but intermediate has something
                    recognized_text = result.get("text", "").strip()

                print(f"🎤 Complete recognized text (from Vosk): '{recognized_text}'")
                
                # Debugging word-level confidence
                all_words = []
                if 'result' in final_result:
                    for word_info in final_result['result']:
                        word = word_info.get('word', '')
                        conf = word_info.get('conf', 0)
                        all_words.append((word, conf))
                        print(f"🎤 Word: '{word}' (confidence: {conf})")
                elif 'result' in result: # Check intermediate result too
                     for word_info in result['result']:
                        word = word_info.get('word', '')
                        conf = word_info.get('conf', 0)
                        all_words.append((word, conf))
                        print(f"🎤 Word: '{word}' (confidence: {conf})")
                
            os.remove(wav_file) # Clean up the temporary WAV file

            # Apply phonetic correction AFTER initial Vosk recognition
            if recognized_text:
                recognized_text = self.improve_recognition(recognized_text)
                print(f"🎤 After phonetic correction: '{recognized_text}'")
            
            if not recognized_text:
                response = "Meeru edaina chebutara? Konchem gattiga matladandi (Please speak louder)"
                print("🎤 No text recognized")
            else:
                response = self.generate_response(recognized_text)
                print(f"🤖 Response generated: {response}")

            # UI update
            # Using Kivy's Clock.schedule_once to update UI from a non-main thread
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.update_ui_after_processing(recognized_text, response))

        except Exception as e:
            error_msg = f"❌ Error in record_and_process: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.update_ui_after_processing("", error_msg, error=True))
            
    def update_ui_after_processing(self, recognized_text, response, error=False):
        """Updates the UI elements on the main Kivy thread."""
        if error:
            self.label.text = response # In case of error, response is the error message
        else:
            self.label.text = f"Meeru cheppindi: {recognized_text}\nJeeva: {response}"
        
        self.btn.text = "🎙️ Matladandi"
        self.btn.disabled = False
        
        if not error: # Only speak if there wasn't a major processing error
            self.speak(response)

    def improve_recognition(self, text):
        """Improve recognition by correcting common misheard words using fuzzy matching."""
        # Common misrecognitions and their corrections
        # Keep this for common single-word corrections or distinct phrases
        corrections_map = {
            "bigg boss": "varsham",
            "big boss": "varsham", 
            "big bos": "varsham",
            "bigg bos": "varsham",
            "the boss": "varsham",
            "be boss": "varsham",
            "big bass": "varsham",
            "bag boss": "varsham",
            "pig boss": "varsham",
            "pick boss": "varsham",
            "varsam": "varsham",
            "varsa": "varsham",
            "varsha": "varsham",
            "versa": "varsham",
            "verso": "varsham",
            "first": "varsham",
            "worst": "varsham",
            "horse": "varsham",
            "course": "varsham",
            "source": "varsham",
            "force": "varsham",
            "boss": "varsham",
            "bos": "varsham",
            "bass": "varsham",
            "vas": "varsham",
            "v": "varsham",
            "vash": "varsham",
            "vash vash vash": "varsham",
            "vasss": "varsham",
            "help": "sahayam",
            "halp": "sahayam", 
            "help me": "sahayam",
            "hello": "namaskaram",
            "helo": "namaskaram",
            "halo": "namaskaram",
            "fertilizer": "eruvu",
            "fertiliser": "eruvu",
            "fertalizer": "eruvu",
            "price": "dhara",
            "prise": "dhara",
            "disease": "vyadi",
            "desease": "vyadi",
        }
        
        text_lower = text.lower()
        corrected_text = text_lower

        # Apply direct replacements first for strong matches
        for wrong, correct in corrections_map.items():
            if wrong in text_lower:
                corrected_text = text_lower.replace(wrong, correct)
                print(f"🔧 Direct corrected '{wrong}' to '{correct}'")
                return corrected_text # Return after first direct match

        # If no direct match, then try fuzzy matching against individual words
        # This part assumes you might have single words that are slightly off
        words = text_lower.split()
        for i, word in enumerate(words):
            for wrong, correct in corrections_map.items():
                # Check for single word matches that are fuzzy
                if len(wrong.split()) == 1: # Only apply fuzzy to single words in corrections map
                    similarity = difflib.SequenceMatcher(None, word, wrong).ratio()
                    if similarity > 0.75: # Higher threshold for single word fuzzy to prevent over-correction
                        words[i] = correct
                        print(f"🔧 Fuzzy corrected '{word}' to '{correct}' (similarity: {similarity:.2f})")
                        return " ".join(words) # Return after first fuzzy match
        
        return corrected_text # Return original if no correction found

    def generate_response(self, query):
        query_lower = query.lower().strip()
        print(f"🤖 Query process chesthunna: '{query_lower}'")
        print(f"🤖 Query length: {len(query_lower)}")
        
        # Enhanced word lists with phonetic variations and common misrecognitions
        eruvu_words = [
            # English
            "fertilizer", "fertiliser", "manure", "fertalizer", "fertlizer", "fertilizar",
            # Telugu transliterations
            "eruvu", "eruvulu", "eravu", "eruvula", "ervulu", "eravulu",
            # Telugu script
            "ఎరువు", "ఎరువులు", "ఎరవు", "మల ఎరువు", "సార ఎరువు",
            # Common misrecognitions
            "manyor", "manur", "manual", "annual", "air view", "eruvo" # Added more misrecognitions
        ]
        
        varsham_words = [
            "rain", "weather", "rein", "reyn", "wether", "wheather", "rainfall",
            "varsham", "varsha", "varshalu", "varsam", "varsa", "versa", "verso",
            "padathunga", "paduthunda", "paduthunga", "paduthanga",
            "shan", "sham", "shum", "shaan", "shaanu", "shamu", 
            "వర్షం", "వర్షలు", "వర్ష", "పడుతుంగా", "పడుతుందా", "వాతావరణం",
            "bigg boss", "big boss", "big bos", "bigg bos", "the boss", "be boss",
            "big bass", "bag boss", "pig boss", "pick boss", "first", "worst",
            "horse", "course", "source", "force", "boss", "bos", "bass",
            "vas","v","vash","vash vash vash","vasss", # Your previous additions
            "vasham", "virsham", "barsham", "warsham", "versham" # More phonetic misrecognitions
        ]

        vyadi_words = [
            # English
            "disease", "pest", "problem", "desease", "disese", "illness", "sickness",
            # Telugu transliterations
            "vyadi", "vyaadi", "nivarana", "rogam", "roga", "rogalu", "kida", "insect",
            # Telugu script
            "వ్యాధి", "వ్యాధులు", "రోగం", "రోగాలు", "కీడు", "కీడులు", "నిర్మూలన",
            # Common misrecognitions
            "video", "ready", "study", "buddy", "body", "vaadi", "vyaadhi" # Added more
        ]
        
        dhara_words = [
            # English
            "price", "rate", "cost", "prise", "pryse", "market", "markat", "value",
            # Telugu transliterations
            "dhara", "dara", "dhar", "rara", "vilava", "viluve", "dhara", "dhare",
            # Telugu script
            "ధర", "ధరలు", "దర", "దరలు", "విలువ", "విలువలు", "ధన", "ధనం",
            # Common misrecognitions
            "dollar", "data", "drama", "area", "sara", "para", "daraa", "thera" # Added more
        ]
        
        namaskaram_words = [
            # English
            "hello", "hi", "hey", "hai", "helo", "halo", "hallo", "hullo",
            # Telugu transliterations
            "namaste", "namaskar", "namaskaram", "namasthe", "namaskaar", "namaskar",
            # Telugu script
            "నమస్తే", "నమస్కారం", "నమస్కార", "హలో", "హాయ్", "హాయి", "హే",
            # Common misrecognitions
            "name", "master", "pasta", "faster", "after", "water", "namaskaar", "namskar" # Added more
        ]
        
        sahayam_words = [
            # English
            "help", "helap", "halp", "what", "whot", "wot", "how", "support",
            # Telugu transliterations
            "sahayam", "sahaya", "sahayamu", "enti", "ela", "emiti", "emti", "ela",
            # Telugu script
            "సహాయం", "సహాయము", "ఏమిటి", "ఎలా", "ఎంటి", "ఏమిటయ్యా", "సహాయ",
            # Common misrecognitions
            "saying", "playing", "staying", "paying", "laying", "praying", "sahayyam", "saayam" # Added more
        ]
        
        # Enhanced matching function with fuzzy matching
        def check_match(word_list, query_text, threshold=0.7):
            from difflib import SequenceMatcher
            
            query_words = query_text.lower().split()

            for word_in_list in word_list:
                for q_word in query_words:
                    similarity = SequenceMatcher(None, word_in_list.lower(), q_word).ratio()
                    if similarity > threshold:
                        print(f"🤖 Matched '{q_word}' ≈ '{word_in_list}' (similarity: {similarity:.2f})")
                        return True
            return False

        # Prathi category check chesthunna with enhanced matching
        print("🤖 Checking all categories...")
        
        # Increased threshold for more strict matching in check_match to balance with improve_recognition
        eruvu_match = check_match(eruvu_words, query_lower, threshold=0.75) 
        print(f"🤖 Eruvu match: {eruvu_match}")
        
        varsham_match = check_match(varsham_words, query_lower, threshold=0.70) # Slightly lower for "varsham" due to common issues
        print(f"🤖 Varsham match: {varsham_match}")
        
        vyadi_match = check_match(vyadi_words, query_lower, threshold=0.75)
        print(f"🤖 Vyadi match: {vyadi_match}")
        
        dhara_match = check_match(dhara_words, query_lower, threshold=0.75)
        print(f"🤖 Dhara match: {dhara_match}")
        
        namaskaram_match = check_match(namaskaram_words, query_lower, threshold=0.75)
        print(f"🤖 Namaskaram match: {namaskaram_match}")
        
        sahayam_match = check_match(sahayam_words, query_lower, threshold=0.75)
        print(f"🤖 Sahayam match: {sahayam_match}")
        
        # Response ivvadaniki check chesthunna
        if namaskaram_match:
            print("🤖 Namaskaram response isthunna")
            return "నమస్తే! నేను జీవ, మీకు వ్యవసాయంలో సహాయం చేస్తాను."
        elif sahayam_match:
            print("🤖 Sahayam response isthunna")
            return "నేను మీకు వ్యవసాయం, ఎరువులు, వాతావరణం మరియు మార్కెట్ ధరల గురించి చెప్పగలను."
        elif eruvu_match:
            print("🤖 Eruvu response isthunna")
            return "ఈ పంటకు ఆర్గానిక్ ఎరువులు, నైట్రోజన్ మరియు పొటాష్ వాడండి."
        elif varsham_match:
            print("🤖 Varsham response isthunna")
            return "నేడు వర్షం పడే అవకాశం 60% ఉంది."
        elif vyadi_match:
            print("🤖 Vyadi response isthunna")
            return "నీం ఆయిల్ వాడండి, ఇది వైరస్‌కు మంచిది."
        elif dhara_match:
            print("🤖 Dhara response isthunna")
            return "ఈ రోజు మార్కెట్‌లో టమోటో ధర రూ.20 కిలోకు ఉంది."
        else:
            print("🤖 No category match found")
            # Check if query contains any meaningful words
            if len(query_lower) > 2:
                return f"మీరు '{query}' అని అన్నారు. దయచేసి వ్యవసాయం, ఎరువులు, వర్షం, వ్యాధులు లేదా ధరల గురించి అడగండి."
            else:
                return "దయచేసి మీ ప్రశ్నను స్పష్టంగా చెప్పండి. నేను వ్యవసాయ సలహాలు ఇస్తాను."

    def speak(self, text, lang='te'):
        try:
            print(f"🔈 Speaking: {text}")
            tts = gTTS(text=text, lang=lang)
            audio_path = os.path.join(tempfile.gettempdir(), "response.mp3")
            tts.save(audio_path)
            
            # Use pygame for cross-platform playback within Kivy applications
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1) # Use time.sleep for non-blocking wait
                pygame.mixer.quit() # Clean up pygame mixer
            except ImportError:
                print("🔈 Pygame not installed. Trying system default players.")
                # Fallback to system specific commands if pygame is not available
                if sys.platform == "win32":
                    try:
                        os.system(f'start wmplayer "{audio_path}"')
                    except:
                        os.system(f'start "" "{audio_path}"')
                elif sys.platform == "darwin": # macOS
                    os.system(f'afplay "{audio_path}"')
                else: # Linux
                    os.system(f'mpg123 "{audio_path}"') # Requires mpg123
            
        except Exception as e:
            print(f"🔈 Error in TTS: {e}")
            self.label.text += f"\n🔈 TTS Error: {e}"


class JeevaApp(App):
    def build(self):
        print("🏗️ Building JeevaApp UI")
        return JeevaUI()


if __name__ == "__main__":
    print("✅ main.py reached this point!")
    try:
        print("🚀 Starting JeevaApp...")
        JeevaApp().run()
    except Exception as e:
        print(f"❌ Crash in Kivy App: {e}")
        import traceback
        traceback.print_exc()