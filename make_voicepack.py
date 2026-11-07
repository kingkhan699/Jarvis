"""Makes voicepack.json: short, instant Jarvis phrases spoken by Kokoro (bm_george).

Run once from the OpenJarvis folder:  .venv/bin/python make_voicepack.py
Takes a few minutes. The Jarvis app then stores the phrases inside itself.
"""
import base64
import io
import json
import sys
import time
from pathlib import Path

from openjarvis.speech.kokoro_tts import KokoroTTSBackend

VOICE = "bm_george"
SPEED = 0.95

CLIPS = {
    # openers: the app asks the brain to begin replies with one of these
    "a_certainly": "Certainly, sir.",
    "a_ofcourse": "Of course, sir.",
    "a_rightaway": "Right away, sir.",
    "a_verygood": "Very good, sir.",
    "a_aswish": "As you wish, sir.",
    # fillers: played if the answer is slow to start
    "f_moment": "One moment, sir.",
    "f_working": "Working on it, sir.",
    "f_allow": "Allow me a moment, sir.",
    "f_think": "Let me think about that, sir.",
    # while a tool works
    "t_weather": "Let me check the weather, sir.",
    "t_search": "Let me look into that for you, sir.",
    "t_eyes": "Let me have a look, sir.",
    # greetings
    "g_morning": "Good morning, sir. How may I be of service?",
    "g_afternoon": "Good afternoon, sir. How may I be of service?",
    "g_evening": "Good evening, sir. How may I be of service?",
    # errors
    "e_net": "I am afraid I cannot reach the network, sir.",
    "e_key": "I am afraid my access key was rejected, sir.",
    "e_limit": "I am afraid the free limit has been reached, sir. Please give me a moment.",
    "e_gen": "I beg your pardon, sir. Something went wrong.",
    "e_model": "That model appears to be unavailable, sir.",
    "e_mic": "I cannot hear you, sir. Please check the microphone permission.",
    # common replies
    "c_noted": "Noted, sir.",
    "c_welcome": "You are most welcome, sir.",
    "c_service": "At your service, sir.",
    "c_bye": "Very good, sir. I shall be here when you need me.",
}


def encode(wav):
    """Shrink to Ogg/Vorbis if possible, otherwise keep the WAV."""
    try:
        import soundfile as sf

        data, rate = sf.read(io.BytesIO(wav))
        buf = io.BytesIO()
        sf.write(buf, data, rate, format="OGG", subtype="VORBIS")
        return buf.getvalue(), "audio/ogg"
    except Exception:
        return wav, "audio/wav"


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("voicepack.json")
    print("Loading the voice...", flush=True)
    tts = KokoroTTSBackend()
    pack = {"voice": VOICE, "speed": SPEED, "clips": {}}
    total = len(CLIPS)
    for i, (key, text) in enumerate(CLIPS.items(), 1):
        t0 = time.time()
        wav = tts.synthesize(text, voice_id=VOICE, speed=SPEED, output_format="wav").audio
        blob, mime = encode(wav)
        pack["clips"][key] = {
            "text": text,
            "data": "data:%s;base64,%s" % (mime, base64.b64encode(blob).decode()),
        }
        print("[%d/%d] %s  (%.1fs, %d KB)" % (i, total, key, time.time() - t0, len(blob) // 1024), flush=True)
    out_path.write_text(json.dumps(pack))
    print("Done! Wrote %s (%.1f MB)" % (out_path, out_path.stat().st_size / 1e6), flush=True)


if __name__ == "__main__":
    main()
