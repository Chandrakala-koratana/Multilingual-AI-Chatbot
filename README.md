# Multilingual-AI-Chatbot
# 🌐 Multilingual AI Chatbot

A high-performance, real-time AI chatbot built with **Python**, **Google Gemini**, and **Tkinter**. This application features automatic language detection, supporting over 20+ languages with both text and voice capabilities.

---

## ✨ Features

* **Multilingual Support:** Seamlessly communicate in English, Telugu, Hindi, Tamil, Spanish, French, Japanese, and many more.
* **Smart Detection:** Automatically identifies the input language using Unicode script analysis and `langdetect`.
* **Voice Integration:**
    * **STT:** Speech-to-Text using `SpeechRecognition` (Google Web Speech API).
    * **TTS:** Text-to-Speech using `gTTS` and `pygame` for high-quality audio playback.
* **Modern UI:** Premium "Dark Mode" interface with scrollable chat bubbles and responsive design.
* **Dual-Mode Interaction:** Choose between Text, Speech, or both for AI responses.

---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Brain** | Google Gemini API (`google-genai`) |
| **GUI** | Tkinter |
| **Speech-to-Text** | `SpeechRecognition` (PyAudio) |
| **Text-to-Speech** | `gTTS` (Google Text-to-Speech) |
| **Audio Engine** | `pygame` |
| **Language Logic** | `langdetect` |

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have **Python 3.9+** installed. You will also need a **Google Gemini API Key**.

### 2. Install Dependencies
You may need to install `portaudio` first for microphone support:
* **Windows:** Usually included with PyAudio.
* **Linux:** `sudo apt-get install python3-pyaudio`

Then, install the required Python libraries:
```bash
pip install google-genai speechrecognition gtts pygame langdetect



**Runn the app using:**
python chatbot.py
