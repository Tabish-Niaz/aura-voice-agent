# Aura Voice Agent

Aura is a voice-based AI assistant built with Streamlit. Speak into your microphone, and Aura answers out loud in the language you choose.

## Features

- **Voice input:** Record from your browser microphone. The recording is sent directly to the AI.
- **Voice output:** Aura's reply plays in a custom audio player with a waveform, play/pause, seek, and a timer.
- **Female / Male voice:** Choose the voice from the selector in the top-right corner.
- **Language selector:** Choose AUTO, URDU, HINDI, or ENGLISH. The reply is given in that language.
- **Any topic:** Aura can answer questions on any subject.
- **Conversation memory:** Aura remembers earlier messages within the same session.
- **Sci-fi UI:** Animated rings, neon glow, and live status messages.

## Tech Stack

- [Streamlit](https://streamlit.io/): web interface
- [OpenAI Agents SDK (voice)](https://github.com/openai/openai-agents-python): speech-to-text, LLM, and text-to-speech
- `gpt-4o-mini`: language model
- NumPy and python-dotenv

## Project Structure

```text
aura-voice-agent/
├── 15-voice_agents.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── .gitignore          # Files Git should ignore
└── README.md           # This file
```

## Prerequisites

- Python 3.10 or newer
- An OpenAI API key with access to the models used
- A browser with microphone support (Chrome, Edge, or Firefox recommended)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Tabish-Niaz/aura-voice-agent.git
cd aura-voice-agent
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
```

Activate it:

- **Windows:** `.venv\Scripts\activate`
- **macOS / Linux:** `source .venv/bin/activate`

### 3. Install the dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your API key

Create a file named `.env` in the project root:

```text
OPENAI_API_KEY=sk-your-real-key
```

> **Warning:** Never commit or share your `.env` file.

### 5. Run the app

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser and allow microphone access when asked.

## Usage

1. Select a voice (**FEMALE** or **MALE**) in the top-right corner.
2. Select a language (**AUTO**, **URDU**, **HINDI**, or **ENGLISH**).
3. Click the microphone button, speak your question, and stop recording.
4. Aura's reply plays automatically. Use the player controls to pause, resume, or seek.

For the most accurate Urdu replies, select **URDU** instead of **AUTO**. Urdu and Hindi sound very similar when spoken, so AUTO can sometimes reply in Hindi.

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again inside your virtual environment. |
| `OPENAI_API_KEY` not found | Make sure the `.env` file is in the project root. |
| Microphone does not work | Allow microphone permission for the site in your browser. |
| Reply is in Hindi instead of Urdu | Select **URDU** in the language selector. |
| `st.components.v1.html` deprecation warning | This app uses `st.iframe`. Upgrade Streamlit with `pip install -U streamlit`. |
| Status shows **ERROR** | Read the message shown in the status line. It usually points to a missing key, a network issue, or a quota limit. |

## Security

- Keep your API key in `.env` and never commit it to Git.
- If a key is ever pushed to GitHub, revoke it immediately in the OpenAI dashboard and create a new one. Deleting the file is not enough, because the key remains in Git history.


