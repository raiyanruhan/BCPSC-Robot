![Google logo](https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png "Google Search Engine Logo")
# BCPSC Robot – System Design (Based on Notebook Notes)

## Input & Sensing

* **Camera**

  * **ESP32-CAM**:

    * Always running, lightweight human presence detector.
    * Sends “Human Detected” signal → then goes to sleep.
  * **Raspberry Pi Camera Module 3**:

    * Activated after ESP32 signal.
    * Handles **face recognition** and checks against **local DB**.
    * If recognized → passes person ID to Task Manager.
* **Microphone**

  * Single boundary microphone (strategically placed away from speaker to reduce echo/feedback).

---

## Greeting & Interaction Flow

1. ESP32 detects a person → Robot plays a **random pre-recorded greeting audio**.
2. If face **recognized in DB** → Greeting is **personalized/generated** by AI.
3. Conversation continues via STT + AI models.

---

## AI Models & Text Generation

* **Gemma:2B (Google)**

  * Main **English RAG model** for question-answering.
  * Works with local database for controlled knowledge.

* **Google Gemini API**

  * Used for **Bangla response generation**.
  * Prompt built in Python → sends to API → converts to Bangla TTS.

* **Pollinations API**

  * Fallback for Bangla if Gemini API fails.

* **Gemini + News API (newsdata.io)**

  * Used for **news updates**.

* **Offline Backup (No Internet)**

  * Gemma generates English.
  * Translated to Bangla using `shhossain/opus-mt-en-to-bn` Hugging Face model.

---

## Speech-to-Text (STT)

* **English**: `vosk-model-en-us-0.22`
* **Bangla**: `BanglaSpeech2Text (small)`
* **Dynamic Switching**: Triggered by user command:

  * Example: *“Talk with me in Bangla”* / *“আমার সাথে বাংলায় কথা বলো”*.
* **Post-STT Processing**:

  * Fuzzy name matching.
  * Grammar correction before sending to AI.

---

## Task Manager (TM)

* Core **decision-making unit**.
* Reads inputs from:

  * Face recognition
  * STT results
  * AI models
* Assigns tasks to:

  * Text models
  * Movement subsystem
  * Face-tracking subsystem

Runs **three main parallel sectors** on Raspberry Pi:

1. **Models (AI processing)**
2. **Face recognition**
3. **Movement tasks**

---

## Text-to-Speech (TTS)

* **English**: `KittenML/KittenTTS` (fast, lightweight, clear).
* **Bangla**:

  * **Primary**: `IndicTTS` (local model).
  * **Preferred**: **11Labs API** (more natural).
  * **Fallback**: Switch back to IndicTTS if API fails.

---

## System Philosophy

* Flexible → always provide a response.
* Layered fallback design → no “dead ends.”
* Offline-first mindset → robot keeps working even without internet.

👉 Do you want me to also draw a **system architecture diagram** (with arrows: ESP32 → Pi Camera → TM → AI Models → TTS → Output)? That might help you present it better to your team.
