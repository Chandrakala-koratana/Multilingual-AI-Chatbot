"""
Multilingual AI Chatbot
- Text & Speech input
- Auto language detection
- AI responds in the user's language (Google Gemini)
- Text & Speech output (gTTS + pygame)
- Premium dark UI with chat bubbles
"""

import tkinter as tk
from tkinter import ttk
import speech_recognition as sr
from gtts import gTTS
import os
import sys
import threading
import traceback
from google import genai
from datetime import datetime
from langdetect import detect, DetectorFactory
import pygame
import re
import tempfile
import time
import json

# Make langdetect deterministic
DetectorFactory.seed = 0

# ─── AI Configuration ────────────────────────────────────────────────
API_KEY = "AIzaSyChbXS5AvYi_Wru4oFwNom425GBR3D8bt8"
client = genai.Client(api_key=API_KEY)

# ─── Language Maps ───────────────────────────────────────────────────
LANG_NAMES = {
    "en": "English", "te": "Telugu", "hi": "Hindi", "ta": "Tamil",
    "kn": "Kannada", "ml": "Malayalam", "fr": "French", "de": "German",
    "es": "Spanish", "ja": "Japanese", "ko": "Korean", "zh-cn": "Chinese",
    "ar": "Arabic", "ru": "Russian", "pt": "Portuguese", "bn": "Bengali",
    "ur": "Urdu", "mr": "Marathi", "gu": "Gujarati", "pa": "Punjabi",
    "it": "Italian", "nl": "Dutch", "tr": "Turkish", "th": "Thai",
}

# gTTS language codes
GTTS_LANG_MAP = {
    "en": "en", "te": "te", "hi": "hi", "ta": "ta", "kn": "kn",
    "ml": "ml", "fr": "fr", "de": "de", "es": "es", "ja": "ja",
    "ko": "ko", "zh-cn": "zh-CN", "zh-tw": "zh-TW", "ar": "ar",
    "ru": "ru", "pt": "pt", "bn": "bn", "ur": "ur", "mr": "mr",
    "gu": "gu", "pa": "pa", "it": "it", "nl": "nl", "tr": "tr",
    "th": "th",
}

# Speech recognition language codes
SR_LANG_MAP = {
    "en": "en-IN", "te": "te-IN", "hi": "hi-IN", "ta": "ta-IN",
    "kn": "kn-IN", "ml": "ml-IN", "fr": "fr-FR", "de": "de-DE",
    "es": "es-ES", "ja": "ja-JP", "ko": "ko-KR", "zh-cn": "zh-CN",
    "ar": "ar-SA", "ru": "ru-RU", "pt": "pt-BR", "bn": "bn-IN",
    "ur": "ur-PK", "mr": "mr-IN", "gu": "gu-IN", "pa": "pa-IN",
    "it": "it-IT", "nl": "nl-NL", "tr": "tr-TR", "th": "th-TH",
}

# Unicode script ranges for detection
SCRIPT_RANGES = {
    "te": (0x0C00, 0x0C7F),
    "hi": (0x0900, 0x097F),
    "ta": (0x0B80, 0x0BFF),
    "kn": (0x0C80, 0x0CFF),
    "ml": (0x0D00, 0x0D7F),
    "bn": (0x0980, 0x09FF),
    "gu": (0x0A80, 0x0AFF),
    "pa": (0x0A00, 0x0A7F),
    "ur": (0x0600, 0x06FF),
    "ar": (0x0600, 0x06FF),
    "ja": (0x3040, 0x309F),
    "ko": (0xAC00, 0xD7AF),
    "th": (0x0E00, 0x0E7F),
    "ru": (0x0400, 0x04FF),
}


def detect_language(text):
    """Detect language using unicode scripts first, then langdetect."""
    if not text or not text.strip():
        return "en"

    # Unicode script detection (most reliable for non-Latin scripts)
    for lang, (start, end) in SCRIPT_RANGES.items():
        count = sum(1 for ch in text if start <= ord(ch) <= end)
        if count >= 2:  # At least 2 characters in that script
            return lang

    # langdetect fallback
    try:
        detected = detect(text)
        if detected in ("zh-cn", "zh-tw", "zh"):
            return "zh-cn"
        return detected
    except Exception:
        return "en"


# ─── Colors ──────────────────────────────────────────────────────────
COLORS = {
    "bg":           "#0a0f1a",
    "surface":      "#111827",
    "surface2":     "#1a2236",
    "chat_bg":      "#0d1321",
    "user_bubble":  "#1d4ed8",
    "user_bubble_fg": "#e0e7ff",
    "ai_bubble":    "#1e293b",
    "ai_bubble_fg": "#e2e8f0",
    "accent":       "#3b82f6",
    "danger":       "#ef4444",
    "success":      "#22c55e",
    "warning":      "#f59e0b",
    "text":         "#f1f5f9",
    "text_dim":     "#94a3b8",
    "border":       "#1e293b",
    "input_bg":     "#141b2d",
    "mic_bg":       "#dc2626",
    "mic_hover":    "#b91c1c",
    "send_bg":      "#2563eb",
    "send_hover":   "#1d4ed8",
    "header_bg":    "#1e3a5f",
}


class MultilingualChatbot:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Multilingual Chatbot")
        self.root.geometry("700x800")
        self.root.minsize(600, 700)
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(True, True)

        # State
        self.output_mode = tk.StringVar(value="Both")
        self.speech_lang = tk.StringVar(value="auto")
        self.is_listening = False
        self.recognizer = sr.Recognizer()
        self.message_count = 0
        self.audio_file_path = os.path.join(tempfile.gettempdir(), "chatbot_tts.mp3")

        # Initialize pygame mixer safely
        try:
            pygame.mixer.init()
            self.audio_available = True
        except Exception as e:
            print(f"[WARN] Audio init failed: {e}")
            self.audio_available = False

        self._build_ui()

        # Bind Enter key
        self.root.bind("<Return>", lambda e: self._send_text())

    # ══════════════════════════════════════════════════════════════════
    #  THREAD-SAFE UI HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _safe_ui(self, func, *args):
        """Schedule a UI update on the main thread."""
        try:
            self.root.after(0, func, *args)
        except Exception:
            pass

    def _set_status(self, text, color=None):
        """Thread-safe status update."""
        if color is None:
            color = COLORS["text_dim"]
        self._safe_ui(self._do_set_status, text, color)

    def _do_set_status(self, text, color):
        try:
            self.status_label.config(text=text, fg=color)
        except tk.TclError:
            pass

    def _add_message_safe(self, sender, text, lang_code=None):
        """Thread-safe message add."""
        self._safe_ui(self._add_message, sender, text, lang_code)

    # ══════════════════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self.main_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.main_frame.pack(fill="both", expand=True)

        self._build_header()
        self._build_controls()
        self._build_chat_area()
        self._build_input_area()

    def _build_header(self):
        header = tk.Frame(self.main_frame, bg=COLORS["header_bg"], height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        inner = tk.Frame(header, bg=COLORS["header_bg"])
        inner.pack(expand=True)

        tk.Label(
            inner, text="  Multilingual AI Chatbot",
            font=("Segoe UI", 18, "bold"),
            bg=COLORS["header_bg"], fg="#ffffff",
        ).pack(pady=(12, 0))

        tk.Label(
            inner, text="Speak or type in any language  |  AI responds in your language",
            font=("Segoe UI", 9),
            bg=COLORS["header_bg"], fg=COLORS["text_dim"],
        ).pack()

    def _build_controls(self):
        control_bar = tk.Frame(self.main_frame, bg=COLORS["surface"], pady=8, padx=15)
        control_bar.pack(fill="x")

        # Response Mode
        left = tk.Frame(control_bar, bg=COLORS["surface"])
        left.pack(side="left")

        tk.Label(
            left, text="Response:", font=("Segoe UI", 9, "bold"),
            bg=COLORS["surface"], fg=COLORS["text_dim"],
        ).pack(side="left", padx=(0, 6))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TRadiobutton",
            background=COLORS["surface"], foreground=COLORS["text"],
            font=("Segoe UI", 9),
        )
        style.map("Dark.TRadiobutton",
            background=[("active", COLORS["surface"])],
            foreground=[("active", COLORS["accent"])],
        )

        for label, val in [("Text", "Text"), ("Speech", "Speech"), ("Both", "Both")]:
            ttk.Radiobutton(
                left, text=label, variable=self.output_mode,
                value=val, style="Dark.TRadiobutton",
            ).pack(side="left", padx=3)

        # Speech Language Selector
        right = tk.Frame(control_bar, bg=COLORS["surface"])
        right.pack(side="right")

        tk.Label(
            right, text="Speech Lang:", font=("Segoe UI", 9, "bold"),
            bg=COLORS["surface"], fg=COLORS["text_dim"],
        ).pack(side="left", padx=(0, 4))

        self._speech_lang_keys = ["auto"] + sorted(LANG_NAMES.keys())
        lang_display = ["Auto Detect"] + [LANG_NAMES[k] for k in sorted(LANG_NAMES.keys())]

        self.speech_lang_combo = ttk.Combobox(
            right, values=lang_display, width=14,
            state="readonly", font=("Segoe UI", 9),
        )
        self.speech_lang_combo.current(0)
        self.speech_lang_combo.pack(side="left")
        self.speech_lang_combo.bind("<<ComboboxSelected>>", self._on_speech_lang_change)

        # Clear Button
        tk.Button(
            control_bar, text="Clear Chat", font=("Segoe UI", 9, "bold"),
            bg=COLORS["surface2"], fg=COLORS["text_dim"],
            activebackground=COLORS["danger"], activeforeground="white",
            bd=0, cursor="hand2", padx=10, pady=2,
            command=self._clear_chat,
        ).pack(side="right", padx=(0, 10))

    def _on_speech_lang_change(self, event):
        idx = self.speech_lang_combo.current()
        self.speech_lang.set(self._speech_lang_keys[idx])

    def _build_chat_area(self):
        tk.Frame(self.main_frame, bg=COLORS["border"], height=1).pack(fill="x")

        chat_container = tk.Frame(self.main_frame, bg=COLORS["chat_bg"])
        chat_container.pack(fill="both", expand=True)

        self.chat_canvas = tk.Canvas(
            chat_container, bg=COLORS["chat_bg"],
            highlightthickness=0, bd=0,
        )

        scrollbar = tk.Scrollbar(
            chat_container, orient="vertical",
            command=self.chat_canvas.yview,
        )

        self.chat_frame = tk.Frame(self.chat_canvas, bg=COLORS["chat_bg"])

        self.chat_frame.bind(
            "<Configure>",
            lambda e: self.chat_canvas.configure(
                scrollregion=self.chat_canvas.bbox("all")
            ),
        )
        self.chat_canvas_window = self.chat_canvas.create_window(
            (0, 0), window=self.chat_frame, anchor="nw"
        )
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.chat_canvas.pack(side="left", fill="both", expand=True)

        self.chat_canvas.bind("<Configure>", self._on_canvas_configure)
        self.chat_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.chat_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        self._add_welcome_message()

    def _on_canvas_configure(self, event):
        self.chat_canvas.itemconfig(self.chat_canvas_window, width=event.width)

    def _add_welcome_message(self):
        frame = tk.Frame(self.chat_frame, bg=COLORS["chat_bg"], pady=15)
        frame.pack(fill="x", padx=20)

        bubble = tk.Frame(frame, bg=COLORS["surface2"], padx=18, pady=14)
        bubble.pack(anchor="center")

        tk.Label(
            bubble, text="Welcome to AI Multilingual Chatbot!",
            font=("Segoe UI", 13, "bold"),
            bg=COLORS["surface2"], fg="#ffffff", wraplength=450,
        ).pack()

        tk.Label(
            bubble,
            text=(
                "Type or speak in any language.\n"
                "I'll detect your language and respond in it!\n\n"
                "Supported: English, Hindi, Telugu, Tamil, Kannada,\n"
                "Malayalam, French, German, Spanish, Japanese, Korean,\n"
                "Chinese, Arabic, Russian, Portuguese, Bengali, Urdu & more"
            ),
            font=("Segoe UI", 9),
            bg=COLORS["surface2"], fg=COLORS["text_dim"],
            wraplength=450, justify="center",
        ).pack(pady=(6, 0))

    def _build_input_area(self):
        tk.Frame(self.main_frame, bg=COLORS["border"], height=1).pack(fill="x")

        input_bar = tk.Frame(self.main_frame, bg=COLORS["surface"], pady=10, padx=12)
        input_bar.pack(fill="x", side="bottom")

        # Status
        self.status_label = tk.Label(
            input_bar, text="Ready", font=("Segoe UI", 8),
            bg=COLORS["surface"], fg=COLORS["text_dim"],
        )
        self.status_label.pack(fill="x", pady=(0, 5))

        # Input row
        input_row = tk.Frame(input_bar, bg=COLORS["surface"])
        input_row.pack(fill="x")

        # Text entry
        self.text_entry = tk.Entry(
            input_row, font=("Segoe UI", 12),
            bg=COLORS["input_bg"], fg=COLORS["text"],
            insertbackground=COLORS["text"], bd=0, relief="flat",
        )
        self.text_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 8))
        self.text_entry.insert(0, "Type your message...")
        self.text_entry.config(fg=COLORS["text_dim"])
        self.text_entry.bind("<FocusIn>", self._on_entry_focus_in)
        self.text_entry.bind("<FocusOut>", self._on_entry_focus_out)

        # Send button
        self.send_btn = tk.Button(
            input_row, text=" Send ",
            font=("Segoe UI", 12, "bold"),
            bg=COLORS["send_bg"], fg="white",
            activebackground=COLORS["send_hover"], activeforeground="white",
            bd=0, cursor="hand2", padx=14, pady=8,
            command=self._send_text,
        )
        self.send_btn.pack(side="left", padx=(0, 6))

        # Mic button
        self.mic_btn = tk.Button(
            input_row, text=" Mic ",
            font=("Segoe UI", 12, "bold"),
            bg=COLORS["mic_bg"], fg="white",
            activebackground=COLORS["mic_hover"], activeforeground="white",
            bd=0, cursor="hand2", padx=14, pady=8,
            command=self._start_voice_thread,
        )
        self.mic_btn.pack(side="left")

    def _on_entry_focus_in(self, event):
        if self.text_entry.get() == "Type your message...":
            self.text_entry.delete(0, tk.END)
            self.text_entry.config(fg=COLORS["text"])

    def _on_entry_focus_out(self, event):
        if not self.text_entry.get().strip():
            self.text_entry.insert(0, "Type your message...")
            self.text_entry.config(fg=COLORS["text_dim"])

    # ══════════════════════════════════════════════════════════════════
    #  CHAT BUBBLES
    # ══════════════════════════════════════════════════════════════════

    def _add_message(self, sender, text, lang_code=None):
        """Add a styled message bubble (must be called on main thread)."""
        is_user = (sender == "You")
        timestamp = datetime.now().strftime("%I:%M %p")
        lang_label = ""
        if lang_code and lang_code in LANG_NAMES:
            lang_label = f"  [{LANG_NAMES[lang_code]}]"

        row = tk.Frame(self.chat_frame, bg=COLORS["chat_bg"], pady=4)
        row.pack(fill="x", padx=16)

        bubble_color = COLORS["user_bubble"] if is_user else COLORS["ai_bubble"]
        text_color = COLORS["user_bubble_fg"] if is_user else COLORS["ai_bubble_fg"]
        anchor = "e" if is_user else "w"

        bubble = tk.Frame(row, bg=bubble_color, padx=14, pady=10)
        bubble.pack(anchor=anchor, padx=(60 if is_user else 0, 0 if is_user else 60))

        sender_display = "You" if is_user else "AI"
        tk.Label(
            bubble, text=f"{sender_display}{lang_label}",
            font=("Segoe UI", 8, "bold"),
            bg=bubble_color,
            fg="#93c5fd" if is_user else COLORS["text_dim"],
            anchor="w",
        ).pack(anchor="w")

        tk.Label(
            bubble, text=text, font=("Segoe UI", 11),
            bg=bubble_color, fg=text_color,
            wraplength=380, justify="left", anchor="w",
        ).pack(anchor="w", pady=(3, 3))

        tk.Label(
            bubble, text=timestamp, font=("Segoe UI", 7),
            bg=bubble_color, fg=COLORS["text_dim"], anchor="e",
        ).pack(anchor="e")

        # Auto-scroll
        self.chat_frame.update_idletasks()
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        self.chat_canvas.yview_moveto(1.0)
        self.message_count += 1

    # ══════════════════════════════════════════════════════════════════
    #  TEXT INPUT
    # ══════════════════════════════════════════════════════════════════

    def _send_text(self):
        """Handle typed text submission."""
        user_text = self.text_entry.get().strip()
        if not user_text or user_text == "Type your message...":
            return

        self.text_entry.delete(0, tk.END)

        lang = detect_language(user_text)

        if self.output_mode.get() in ("Text", "Both"):
            self._add_message("You", user_text, lang)

        # Get AI response in background
        threading.Thread(
            target=self._get_ai_response,
            args=(user_text, lang),
            daemon=True,
        ).start()

    # ══════════════════════════════════════════════════════════════════
    #  VOICE INPUT
    # ══════════════════════════════════════════════════════════════════

    def _start_voice_thread(self):
        if self.is_listening:
            return
        self.is_listening = True
        threading.Thread(target=self._process_voice, daemon=True).start()

    def _process_voice(self):
        try:
            self._safe_ui(self.mic_btn.config, bg=COLORS["success"], text=" REC ")
            self._set_status("Calibrating microphone...", COLORS["warning"])

            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                self._set_status("Listening... Speak now!", COLORS["success"])

                try:
                    audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=15)
                except sr.WaitTimeoutError:
                    self._set_status("No speech detected. Try again.", COLORS["warning"])
                    return

                self._set_status("Processing speech...", COLORS["accent"])

                # Determine recognition language
                selected_lang = self.speech_lang.get()

                user_text = None
                recognized_lang = "en"

                if selected_lang != "auto":
                    # User selected a specific language
                    sr_lang = SR_LANG_MAP.get(selected_lang, "en-IN")
                    try:
                        user_text = self.recognizer.recognize_google(audio, language=sr_lang)
                        recognized_lang = selected_lang
                    except sr.UnknownValueError:
                        self._set_status("Could not understand speech. Try again.", COLORS["danger"])
                        return
                    except sr.RequestError as e:
                        self._set_status(f"Speech service error: {e}", COLORS["danger"])
                        return
                else:
                    # Auto-detect: try common languages
                    try_langs = ["en-IN", "hi-IN", "te-IN", "ta-IN", "kn-IN"]
                    for try_lang in try_langs:
                        try:
                            user_text = self.recognizer.recognize_google(audio, language=try_lang)
                            if user_text and user_text.strip():
                                recognized_lang = detect_language(user_text)
                                break
                        except sr.UnknownValueError:
                            continue
                        except sr.RequestError as e:
                            self._set_status(f"Speech service error: {e}", COLORS["danger"])
                            return

                    if not user_text:
                        self._set_status("Could not understand speech. Try again.", COLORS["danger"])
                        return

                # Detect language from the transcribed text
                lang = detect_language(user_text)

                if self.output_mode.get() in ("Text", "Both"):
                    self._add_message_safe("You", user_text, lang)

                # Small delay to let UI update
                time.sleep(0.1)

                self._get_ai_response(user_text, lang)

        except OSError as e:
            self._set_status(f"Microphone error: {str(e)[:50]}", COLORS["danger"])
            print(f"[MIC ERROR] {e}")
        except Exception as e:
            self._set_status(f"Error: {str(e)[:50]}", COLORS["danger"])
            print(f"[VOICE ERROR] {traceback.format_exc()}")
        finally:
            self.is_listening = False
            self._safe_ui(self._reset_mic_button)

    def _reset_mic_button(self):
        try:
            self.mic_btn.config(bg=COLORS["mic_bg"], text=" Mic ")
        except tk.TclError:
            pass

    # ══════════════════════════════════════════════════════════════════
    #  AI RESPONSE (runs in background thread)
    # ══════════════════════════════════════════════════════════════════

    def _get_ai_response(self, user_text, lang):
        """Get AI response from Gemini with retry logic."""
        self._set_status("AI is thinking...", COLORS["accent"])

        lang_name = LANG_NAMES.get(lang, "English")
        now = datetime.now().strftime("%I:%M %p, %B %d, %Y")

        prompt = (
            f"Current time: {now}.\n"
            f"User said (language: {lang_name}): \"{user_text}\"\n\n"
            f"RULES:\n"
            f"- Reply ENTIRELY in {lang_name}.\n"
            f"- Keep it short, friendly, and helpful.\n"
            f"- Do NOT mix languages.\n"
            f"- Be conversational."
        )

        # Retry with backoff
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]
        last_error = None

        for model_name in models_to_try:
            for attempt in range(3):
                try:
                    self._set_status(
                        f"AI thinking... (attempt {attempt + 1})",
                        COLORS["accent"],
                    )

                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )

                    ai_text = response.text
                    if not ai_text:
                        continue

                    ai_text = ai_text.strip()
                    # Clean markdown
                    ai_text = re.sub(r"\*\*(.+?)\*\*", r"\1", ai_text)
                    ai_text = re.sub(r"\*(.+?)\*", r"\1", ai_text)
                    ai_text = re.sub(r"```[\s\S]*?```", "", ai_text)
                    ai_text = ai_text.strip()

                    if not ai_text:
                        continue

                    # Show AI message
                    if self.output_mode.get() in ("Text", "Both"):
                        self._add_message_safe("AI", ai_text, lang)

                    # Speak AI message
                    if self.output_mode.get() in ("Speech", "Both"):
                        self._speak(ai_text, lang)

                    self._set_status(
                        f"Responded in {lang_name}", COLORS["success"]
                    )
                    self._safe_ui(
                        self.root.after, 4000,
                        lambda: self._set_status("Ready"),
                    )
                    return  # Success!

                except Exception as e:
                    last_error = e
                    wait_time = (attempt + 1) * 2
                    self._set_status(
                        f"Retrying in {wait_time}s...",
                        COLORS["warning"],
                    )
                    print(f"[AI RETRY] model={model_name} attempt={attempt + 1} error={e}")
                    time.sleep(wait_time)

        # All retries failed — show error in chat
        error_msg = str(last_error)[:120] if last_error else "Unknown error"
        self._add_message_safe("AI", f"Sorry, I encountered an error: {error_msg}", lang)
        self._set_status("AI Error - try again", COLORS["danger"])
        print(f"[AI ERROR] All retries failed: {traceback.format_exc()}")

    # ══════════════════════════════════════════════════════════════════
    #  TEXT-TO-SPEECH
    # ══════════════════════════════════════════════════════════════════

    def _speak(self, text, lang):
        """Generate and play TTS audio."""
        if not self.audio_available:
            self._set_status("Audio not available", COLORS["warning"])
            return

        self._set_status("Speaking...", "#a78bfa")

        try:
            # Get gTTS language code
            tts_lang = GTTS_LANG_MAP.get(lang, "en")

            # Truncate very long text for TTS
            speak_text = text[:500] if len(text) > 500 else text

            tts = gTTS(text=speak_text, lang=tts_lang)
            tts.save(self.audio_file_path)

            # Stop any currently playing audio
            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                    time.sleep(0.1)
            except Exception:
                pass

            pygame.mixer.music.load(self.audio_file_path)
            pygame.mixer.music.play()

            # Wait for playback (non-blocking check)
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

        except Exception as e:
            self._set_status(f"TTS Error: {str(e)[:50]}", COLORS["warning"])
            print(f"[TTS ERROR] {traceback.format_exc()}")

    # ══════════════════════════════════════════════════════════════════
    #  CLEAR CHAT
    # ══════════════════════════════════════════════════════════════════

    def _clear_chat(self):
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        self.message_count = 0
        self._add_welcome_message()
        self._set_status("Chat cleared", COLORS["text_dim"])
        self.root.after(2000, lambda: self._set_status("Ready"))


# ─── Main ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = MultilingualChatbot(root)
    root.mainloop()