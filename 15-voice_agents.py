import streamlit as st
import asyncio
import numpy as np
import io
import wave
import base64
import hashlib
import os
from html import escape
from dotenv import load_dotenv


# Backend imports
from agents import Agent
from agents.voice import (
    AudioInput,
    SingleAgentVoiceWorkflow,
    TTSModelSettings,
    VoicePipeline,
    VoicePipelineConfig,
)

load_dotenv()

def get_api_key():
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return None

API_KEY = get_api_key()

if API_KEY:
    os.environ["OPENAI_API_KEY"] = API_KEY

import threading

@st.cache_resource
def get_background_loop():
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    return loop

def run_async(coro):
    loop = get_background_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


SAMPLE_RATE = 24_000

# Female / Male voice mapping (aur voices: nova, shimmer = female | echo, ash = male)
VOICES = {"FEMALE": "coral", "MALE": "onyx"}
LANGUAGES = ["AUTO", "URDU", "HINDI", "ENGLISH"]

BASE_INSTRUCTIONS = (
    "You are Aura, a friendly and knowledgeable voice assistant. "
    "You can answer questions on any topic. "
    "Keep spoken answers short, natural and easy to follow: 2-3 sentences max. "
    "Your reply is spoken aloud, so never use markdown, bullet lists, or emojis."
)

LANGUAGE_RULES = {
    "AUTO": (
        "Reply in the same language the user spoke. Urdu and Hindi sound almost identical "
        "when spoken, so if the user uses Urdu words (for example shukriya, mehrbani, zaroor, "
        "khuda hafiz, Urdu poetry or Urdu-style phrases), reply in Urdu script. "
        "Reply in Hindi (Devanagari) only if the user clearly speaks Hindi."
    ),
    "URDU": (
        "The user speaks Urdu. ALWAYS reply in Urdu, written in Urdu (Nastaliq) script, "
        "using Urdu vocabulary. NEVER reply in Hindi or Devanagari, even if the user's words "
        "sound similar to Hindi."
    ),
    "HINDI": (
        "The user speaks Hindi. ALWAYS reply in Hindi, written in Devanagari script."
    ),
    "ENGLISH": (
        "The user speaks English. ALWAYS reply in English."
    ),
}

# 1. Streamlit Page Config
st.set_page_config(page_title="Aura Voice Agent", layout="wide", initial_sidebar_state="collapsed")

# 2. CSS
st.markdown("""
<style>
header, footer { display: none !important; }
html, body, .stApp {
    background-color: #050A15;
    color: #00FFFF;
    font-family: 'Courier New', Courier, monospace;
    overflow: hidden !important;
    height: 100vh !important;
}

[data-testid="block-container"] {
    padding: 2rem 1rem 1rem 1rem !important;
    max-width: 100% !important;
    height: 100vh !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
}

[data-testid="stVerticalBlock"] > div { margin-bottom: 0 !important; }

.sci-fi-title {
    color: #00FFFF; font-size: 48px; font-weight: bold; letter-spacing: 10px;
    text-align: center; margin-bottom: 30px;
    text-shadow: 0 0 10px #00FFFF, 0 0 20px #00FFFF, 0 0 40px #B026FF; text-transform: uppercase;
}

.visualizer-row { display: flex; justify-content: center; align-items: center; gap: 60px; width: 100%; margin-bottom: 40px; }

.ring-side {
    width: 280px; height: 280px; border-radius: 50%;
    display: flex; justify-content: center; align-items: center; position: relative; z-index: 1;
}
.ring-side.cyan { border: 6px solid rgba(0, 255, 255, 0.3); box-shadow: 0 0 30px rgba(0, 255, 255, 0.4), inset 0 0 20px rgba(0, 255, 255, 0.4); }
.ring-side.purple { border: 6px solid rgba(176, 38, 255, 0.3); box-shadow: 0 0 30px rgba(176, 38, 255, 0.4), inset 0 0 20px rgba(176, 38, 255, 0.4); }

.wave-complex { position: absolute; display: flex; align-items: center; justify-content: center; gap: 6px; width: 150%; z-index: 2; }
.w-bar {
    width: 6px; border-radius: 3px; background-color: #00FFFF; box-shadow: 0 0 8px #00FFFF;
    animation: pulse-wave 1s ease-in-out infinite alternate;
}
.ring-side.purple .w-bar { background-color: #B026FF; box-shadow: 0 0 8px #B026FF; }
@keyframes pulse-wave { 0% { opacity: 0.6; transform: scaleY(0.7); } 100% { opacity: 1; transform: scaleY(1.2); } }

.ring-center {
    width: 440px; height: 440px; border-radius: 50%;
    display: flex; justify-content: center; align-items: center; position: relative;
}
.ring-inner {
    position: absolute; width: 380px; height: 380px; border-radius: 50%;
    border: 10px solid #00FFFF; border-top-color: transparent; border-bottom-color: #B026FF;
    box-shadow: 0 0 30px rgba(0, 255, 255, 0.5), inset 0 0 30px rgba(0, 255, 255, 0.3);
    animation: spin 5s linear infinite;
}
.ring-outer {
    position: absolute; width: 460px; height: 460px; border-radius: 50%;
    border: 4px dashed rgba(176, 38, 255, 0.6); animation: spin-reverse 12s linear infinite;
}
@keyframes spin { 100% { transform: rotate(360deg); } }
@keyframes spin-reverse { 100% { transform: rotate(-360deg); } }

.equalizer-large { display: flex; gap: 10px; align-items: center; height: 140px; z-index: 3; }
.bar-l {
    width: 16px; background: linear-gradient(to top, #00FFFF, #B026FF);
    border-radius: 8px; box-shadow: 0 0 12px rgba(176, 38, 255, 0.6);
    animation: eq-large 0.9s ease-in-out infinite alternate;
}
.bar-l:nth-child(1) { height: 30%; animation-delay: 0.1s; }
.bar-l:nth-child(2) { height: 60%; animation-delay: 0.3s; }
.bar-l:nth-child(3) { height: 90%; animation-delay: 0.2s; }
.bar-l:nth-child(4) { height: 100%; animation-delay: 0.4s; }
.bar-l:nth-child(5) { height: 100%; animation-delay: 0.5s; }
.bar-l:nth-child(6) { height: 80%; animation-delay: 0.1s; }
.bar-l:nth-child(7) { height: 50%; animation-delay: 0.3s; }
.bar-l:nth-child(8) { height: 30%; animation-delay: 0.2s; }
@keyframes eq-large { 0% { transform: scaleY(0.4); } 100% { transform: scaleY(1); } }

.terminal-output {
    font-size: 16px; text-shadow: 0 0 8px #00FFFF; text-align: center; margin-bottom: 5px;
}

/* Audio input widget */
[data-testid="stAudioInput"] {
    background-color: #050A15 !important; border: 1px solid #00FFFF !important;
    border-radius: 12px; padding: 5px; box-shadow: 0 0 15px rgba(0, 255, 255, 0.15); width: 100%;
}


/* Voice selector: top-right corner */
.st-key-voice_choice {
    position: fixed; top: 16px; right: 24px; z-index: 100; width: auto !important;
    background: #050A15; border: 1px solid #B026FF; border-radius: 10px;
    padding: 6px 12px; box-shadow: 0 0 12px rgba(176, 38, 255, 0.35);
}

/* Language selector: voice ke neeche */
.st-key-language_choice {
    position: fixed; top: 80px; right: 24px; z-index: 100; width: auto !important;
    background: #050A15; border: 1px solid #00FFFF; border-radius: 10px;
    padding: 6px 12px; box-shadow: 0 0 12px rgba(0, 255, 255, 0.35);
}

.st-key-voice_choice label p, .st-key-language_choice label p {
    color: #00FFFF !important; font-family: 'Courier New', monospace !important;
    font-size: 13px !important; font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

def get_pipeline(voice: str, language: str) -> VoicePipeline:
    """Har (language) ke liye alag workflow, taake jawab ki zaban pakki rahe."""
    key = f"workflow_{language}"
    if key not in st.session_state:
        agent = Agent(
            name="Aura",
            instructions=BASE_INSTRUCTIONS + " " + LANGUAGE_RULES[language],
            model="gpt-4o-mini",
        )
        st.session_state[key] = SingleAgentVoiceWorkflow(agent)

    return VoicePipeline(
        workflow=st.session_state[key],
        config=VoicePipelineConfig(
            tts_settings=TTSModelSettings(voice=voice),
            trace_include_sensitive_audio_data=False,
        ),
    )


def process_audio_bytes(audio_bytes: bytes) -> AudioInput:
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        channels = wav_file.getnchannels()
        frames = wav_file.readframes(wav_file.getnframes())
    audio_np = np.frombuffer(frames, dtype=np.int16)
    if channels > 1:  # stereo ho to sirf pehla channel
        audio_np = audio_np.reshape(-1, channels)[:, 0]
    return AudioInput(buffer=audio_np)


async def run_pipeline(pipeline: VoicePipeline, audio_input: AudioInput) -> bytes:
    result = await pipeline.run(audio_input)
    audio_data = bytearray()
    async for event in result.stream():
        if event.type == "voice_stream_event_audio":
            audio_data.extend(event.data)
    return bytes(audio_data)


def pcm_to_wav(raw_pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(raw_pcm)
    return buf.getvalue()


PLAYER_HTML = """
<style>
  body { margin:0; background:transparent; font-family:'Courier New',monospace; }
  .label { text-align:center; color:#B026FF; font-size:14px; font-weight:bold;
           margin-bottom:6px; text-shadow:0 0 8px #B026FF; }
  .shell { border:1px solid #B026FF; border-radius:12px; padding:5px;
           box-shadow:0 0 15px rgba(176,38,255,.35); background:#050A15; }
  .player { display:flex; align-items:center; gap:14px; padding:12px 16px;
            background:#2a2a33; border-radius:8px; }
  .btn { width:34px; height:34px; border-radius:50%; border:1px solid #00FFFF;
         background:transparent; color:#00FFFF; cursor:pointer; display:flex;
         align-items:center; justify-content:center; flex-shrink:0;
         box-shadow:0 0 10px rgba(0,255,255,.4); transition:.2s; }
  .btn:hover { background:rgba(0,255,255,.15); box-shadow:0 0 16px rgba(0,255,255,.7); }
  .btn svg { width:14px; height:14px; fill:#00FFFF; }
  canvas { flex:1; height:44px; cursor:pointer; min-width:0; }
  .time { color:#9a9aa8; font-size:15px; min-width:48px; text-align:right; }
</style>

<div class="label" id="lbl">[ INCOMING TRANSMISSION ]</div>
<div class="shell">
  <div class="player">
    <button class="btn" id="btn">
      <svg id="icon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
    </button>
    <canvas id="wave"></canvas>
    <div class="time" id="time">00:00</div>
  </div>
</div>

<script>
const audio = new Audio("data:audio/wav;base64,__B64__");
const canvas = document.getElementById("wave");
const ctx = canvas.getContext("2d");
const btn = document.getElementById("btn");
const icon = document.getElementById("icon");
const timeEl = document.getElementById("time");
const BARS = 64;
let peaks = new Array(BARS).fill(0.15);

const PLAY = "M8 5v14l11-7z";
const PAUSE = "M6 5h4v14H6zM14 5h4v14h-4z";

function fmt(s){ s = Math.max(0, Math.floor(s||0));
  return String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0"); }

function resize(){
  const r = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * r;
  canvas.height = canvas.clientHeight * r;
  draw();
}

function draw(){
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0,0,W,H);
  const progress = audio.duration ? audio.currentTime/audio.duration : 0;
  const slot = W/BARS, bw = Math.max(2, slot*0.45);
  for(let i=0;i<BARS;i++){
    const h = Math.max(4, peaks[i]*H*0.95);
    const x = i*slot + (slot-bw)/2, y = (H-h)/2;
    ctx.fillStyle = (i/BARS) <= progress ? (i%2 ? "#00FFFF" : "#B026FF") : "#5a5a66";
    ctx.fillRect(x, y, bw, h);
  }
}

// Asal audio se waveform nikalna
fetch(audio.src).then(r=>r.arrayBuffer()).then(buf=>{
  const ac = new (window.AudioContext||window.webkitAudioContext)();
  return ac.decodeAudioData(buf);
}).then(decoded=>{
  const data = decoded.getChannelData(0), step = Math.floor(data.length/BARS);
  const raw = [];
  for(let i=0;i<BARS;i++){
    let max = 0;
    for(let j=0;j<step;j+=20){ max = Math.max(max, Math.abs(data[i*step+j]||0)); }
    raw.push(max);
  }
  const m = Math.max(...raw) || 1;
  peaks = raw.map(v => Math.max(0.08, v/m));
  timeEl.textContent = fmt(decoded.duration);
  draw();
}).catch(()=>{});

function loop(){
  draw();
  timeEl.textContent = fmt(audio.currentTime);
  if(!audio.paused) requestAnimationFrame(loop);
}

function setStatus(text, color, lbl){
  document.getElementById("lbl").textContent = lbl;
  try {
    const el = window.parent.document.querySelector('.terminal-output');
    if (el) { el.textContent = text; el.style.color = color; el.style.textShadow = '0 0 8px ' + color; }
  } catch(e) {}
}

btn.onclick = () => audio.paused ? audio.play() : audio.pause();
audio.onplay = () => {
  icon.innerHTML = '<path d="'+PAUSE+'"/>';
  setStatus('SYSTEM: AI SPEAKING - Transmitting response...', '#00FFFF', '[ AI SPEAKING... ]');
  loop();
};
audio.onpause = () => {
  icon.innerHTML = '<path d="'+PLAY+'"/>';
  if (!audio.ended) setStatus('SYSTEM: PAUSED - Transmission on hold.', '#B026FF', '[ PAUSED ]');
};
audio.onended = () => {
  icon.innerHTML = '<path d="'+PLAY+'"/>';
  setStatus('SYSTEM: STANDBY - Transmission complete.', '#00FFFF', '[ TRANSMISSION COMPLETE ]');
  audio.currentTime = 0; draw();
};
canvas.onclick = e => {
  if(!audio.duration) return;
  const r = canvas.getBoundingClientRect();
  audio.currentTime = ((e.clientX - r.left)/r.width) * audio.duration;
  draw();
};
window.addEventListener("resize", resize);
resize();
if (__AUTOPLAY__) audio.play().catch(()=>{});
</script>
"""


def custom_audio_player(wav_bytes: bytes, autoplay: bool = False):
    b64 = base64.b64encode(wav_bytes).decode()
    page = (PLAYER_HTML
            .replace("__B64__", b64)
            .replace("__AUTOPLAY__", "true" if autoplay else "false"))
    st.iframe(page, height=130)


# --- 4. UI RENDERING ---
raw_html = """
<div class="sci-fi-title">AURA VOICE AGENT</div>
<div class="visualizer-row">
<div class="ring-side cyan">
<div class="wave-complex">
<div class="w-bar" style="height: 15px;"></div><div class="w-bar" style="height: 35px;"></div><div class="w-bar" style="height: 60px;"></div><div class="w-bar" style="height: 95px;"></div><div class="w-bar" style="height: 130px;"></div><div class="w-bar" style="height: 70px;"></div><div class="w-bar" style="height: 40px;"></div><div class="w-bar" style="height: 110px;"></div><div class="w-bar" style="height: 140px;"></div><div class="w-bar" style="height: 55px;"></div><div class="w-bar" style="height: 30px;"></div><div class="w-bar" style="height: 15px;"></div>
</div>
</div>
<div class="ring-center">
<div class="ring-inner"></div>
<div class="ring-outer"></div>
<div class="equalizer-large">
<div class="bar-l"></div><div class="bar-l"></div><div class="bar-l"></div><div class="bar-l"></div><div class="bar-l"></div><div class="bar-l"></div><div class="bar-l"></div><div class="bar-l"></div>
</div>
</div>
<div class="ring-side purple">
<div class="wave-complex">
<div class="w-bar" style="height: 15px;"></div><div class="w-bar" style="height: 35px;"></div><div class="w-bar" style="height: 65px;"></div><div class="w-bar" style="height: 140px;"></div><div class="w-bar" style="height: 95px;"></div><div class="w-bar" style="height: 40px;"></div><div class="w-bar" style="height: 80px;"></div><div class="w-bar" style="height: 125px;"></div><div class="w-bar" style="height: 80px;"></div><div class="w-bar" style="height: 55px;"></div><div class="w-bar" style="height: 30px;"></div><div class="w-bar" style="height: 15px;"></div>
</div>
</div>
</div>
"""
st.markdown(raw_html, unsafe_allow_html=True)

terminal_placeholder = st.empty()


def set_status(text: str, color: str = "#00FFFF"):
    terminal_placeholder.markdown(
        f'<div class="terminal-output" style="color:{color}; text-shadow:0 0 8px {color};">{text}</div>',
        unsafe_allow_html=True,
    )


# Mic listener: recording shuru/khatam hone par status badalta hai
st.html("""
<script>
(function () {
  if (window.__voiceHooked) return;
  window.__voiceHooked = true;
  function setStatus(t, c) {
    const el = document.querySelector('.terminal-output');
    if (!el) return;
    el.textContent = t;
    el.style.color = c;
    el.style.textShadow = '0 0 8px ' + c;
  }
  const md = navigator.mediaDevices;
  if (!md || !md.getUserMedia) return;
  const orig = md.getUserMedia.bind(md);
  md.getUserMedia = async function (...args) {
    const stream = await orig(...args);
    if (args[0] && args[0].audio) {
      setStatus('SYSTEM: LISTENING - Recording voice input...', '#FF3B6B');
      stream.getAudioTracks().forEach(tr => {
        const origStop = tr.stop.bind(tr);
        tr.stop = function () {
          origStop();
          setStatus('SYSTEM: PROCESSING - Analyzing audio packets...', '#B026FF');
        };
      });
    }
    return stream;
  };
})();
</script>
""", unsafe_allow_javascript=True)

st.markdown(
    "<div style='text-align: center; color: #00FFFF; font-size: 14px; font-weight: bold; margin-bottom: 5px;'>[ INITIATE VOICE OVERRIDE ]</div>",
    unsafe_allow_html=True,
)

# Voice selector (CSS se top-right corner mein fixed hai)
voice_choice = st.radio(
    "Voice", list(VOICES.keys()), horizontal=True,
    label_visibility="collapsed", key="voice_choice",
)

language_choice = st.radio(
    "Language", LANGUAGES, horizontal=True,
    label_visibility="collapsed", key="language_choice",
)

# Centered Audio Widget (24kHz = AI pipeline ki sample rate ke barabar)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    audio_val = st.audio_input("Record Command", sample_rate=SAMPLE_RATE, label_visibility="collapsed")


# --- 5. BACKEND LOGIC ---
if audio_val:
    audio_bytes = audio_val.getvalue()
    audio_key = hashlib.md5(audio_bytes).hexdigest()
    is_new = st.session_state.get("last_key") != audio_key

    if is_new:
        set_status("SYSTEM: PROCESSING - Analyzing audio packets...", "#B026FF")
        wav_bytes, error = None, None
        try:
            audio_obj = process_audio_bytes(audio_bytes)
            pipeline = get_pipeline(VOICES[voice_choice], language_choice)
            with st.spinner("AI is computing response..."):
                raw_pcm = run_async(run_pipeline(pipeline, audio_obj))
            if raw_pcm:
                wav_bytes = pcm_to_wav(raw_pcm)
            else:
                error = "No audio response received."
        except Exception as e:
            error = escape(str(e))[:120]

        st.session_state.last_key = audio_key
        st.session_state.reply_wav = wav_bytes
        st.session_state.last_error = error

    if st.session_state.get("last_error"):
        set_status(f"SYSTEM: ERROR - {st.session_state.last_error}", "#FF3B6B")
    elif st.session_state.get("reply_wav"):
        set_status("SYSTEM: RESPONSE READY - Incoming transmission...")
        with col2:
            custom_audio_player(st.session_state.reply_wav, autoplay=is_new)
else:
    set_status("SYSTEM: ACTIVE - waiting for prompt...")
