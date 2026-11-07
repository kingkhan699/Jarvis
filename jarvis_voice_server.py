"""Tiny local voice server for the Jarvis web app.

Runs OpenJarvis's Kokoro voice on this phone and hands WAV audio to the app.
Listens on this phone only (127.0.0.1) and only answers the Jarvis app's website.
Also serves voicepack.json (the instant phrases made by make_voicepack.py).

Run from the OpenJarvis folder:  .venv/bin/python jarvis_voice_server.py
"""
import io
import json
import os
import re
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:  # use a sensible number of CPU threads on a phone (big and little cores)
    import torch

    torch.set_num_threads(int(os.environ.get("JARVIS_THREADS", "4")))
    print("[voice] using %d CPU threads" % torch.get_num_threads(), flush=True)
except Exception:
    pass

from openjarvis.speech.kokoro_tts import KokoroTTSBackend

PORT = int(os.environ.get("JARVIS_VOICE_PORT", "8880"))
ALLOWED = {"https://kingkhan699.github.io"}
ALLOWED.update(o for o in os.environ.get("JARVIS_EXTRA_ORIGINS", "").split(",") if o)
VOICE_RE = re.compile(r"^[a-z]{2}_[a-z]+$")
PACK = Path(__file__).with_name("voicepack.json")

lock = threading.Lock()
tts = KokoroTTSBackend()


def synth(text, voice, speed):
    with lock:
        t0 = time.time()
        audio = tts.synthesize(text, voice_id=voice, speed=speed, output_format="wav").audio
        took = time.time() - t0
    try:
        with wave.open(io.BytesIO(audio)) as w:
            secs = w.getnframes() / float(w.getframerate())
        print("[voice] made %.1fs of speech in %.1fs (%.1fx real time): %s"
              % (secs, took, secs / took if took else 0, text[:40]), flush=True)
    except Exception:
        print("[voice] synthesis took %.1fs: %s" % (took, text[:40]), flush=True)
    return audio


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[voice]", self.address_string(), fmt % args, flush=True)

    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "content-type")
            self.send_header("Access-Control-Allow-Private-Network", "true")

    def _send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        if self.path.startswith("/health"):
            self._send(200, b'{"ok":true}')
        elif self.path.startswith("/voicepack.json"):
            if PACK.exists():
                self._send(200, PACK.read_bytes())
            else:
                self._send(404, b'{"error":"no voicepack yet"}')
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        origin = self.headers.get("Origin")
        if origin and origin not in ALLOWED:
            return self._send(403, b'{"error":"origin not allowed"}')
        if self.path != "/tts":
            return self._send(404, b'{"error":"not found"}')
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0 or n > 20000:
                return self._send(413, b'{"error":"bad size"}')
            data = json.loads(self.rfile.read(n))
            text = str(data.get("text", "")).strip()[:600]
            voice = str(data.get("voice", "bm_george"))
            if not VOICE_RE.match(voice):
                voice = "bm_george"
            speed = min(1.4, max(0.6, float(data.get("speed", 0.95))))
            if not text:
                return self._send(400, b'{"error":"no text"}')
            wav = synth(text, voice, speed)
            self._send(200, wav, "audio/wav")
        except Exception as exc:  # keep the server alive whatever happens
            print("[voice] error:", exc, flush=True)
            self._send(500, json.dumps({"error": str(exc)}).encode())


if __name__ == "__main__":
    print("Loading the Jarvis voice (first time can take a minute)...", flush=True)
    synth("Voice online.", "bm_george", 0.95)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("Jarvis voice server ready on http://localhost:%d  (leave this window open)" % PORT, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
