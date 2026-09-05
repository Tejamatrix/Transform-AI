"""Fixture: video WITH spoken audio via Windows SAPI TTS + FFmpeg."""
import os
import subprocess
import sys

FIX = os.path.join(os.environ.get("TEMP", "/tmp"), "tai_fixtures")
os.makedirs(FIX, exist_ok=True)

# 1. spoken audio via Windows SAPI
try:
    import comtypes  # noqa
except ImportError:
    pass

ps_script = r'''
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = 0
$s.SetOutputToWaveFile("SPEECH_PATH")
$s.Speak("Security briefing, March 2026. On 14 March, Meridian Financial Systems detected unauthorized access to its core banking network. Fourteen departments were affected and approximately thirty eight thousand customer records were exposed. Mitigation was completed by 20 March. Enable multi factor authentication and patch all affected systems immediately.")
$s.Dispose()
'''
ps_script = ps_script.replace("SPEECH_PATH", os.path.join(FIX, "speech.wav"))
ps_file = os.path.join(FIX, "tts.ps1")
with open(ps_file, "w") as f:
    f.write(ps_script)
r = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_file],
                   capture_output=True, timeout=120)
wav = os.path.join(FIX, "speech.wav")
if not os.path.exists(wav) or os.path.getsize(wav) < 10000:
    print("TTS FAILED:", r.stderr.decode(errors="replace")[:200])
    sys.exit(1)
print("speech.wav:", os.path.getsize(wav), "bytes")

# 2. slide frames (reuse from make_fixtures if present, else draw)
from PIL import Image, ImageDraw, ImageFont
FONT = r"C:\Windows\Fonts\arial.ttf"

def slide(lines, path):
    img = Image.new("RGB", (1280, 720), "white")
    d = ImageDraw.Draw(img)
    y = 240
    for text, size in lines:
        f = ImageFont.truetype(FONT, size)
        w = d.textlength(text, font=f)
        d.text(((1280 - w) / 2, y), text, font=f, fill="black")
        y += size + 40
    img.save(path)

slide([("SECURITY BRIEFING", 54), ("MARCH 2026", 36)], os.path.join(FIX, "v_frame0.png"))
slide([("ACTION ITEMS: MFA AND PATCHING", 40)], os.path.join(FIX, "v_frame1.png"))

# 3. mux: slides video + TTS audio
ffmpeg = subprocess.run(["where", "ffmpeg"], capture_output=True).stdout.decode().strip().splitlines()[0]
silent = os.path.join(FIX, "vid_silent.mp4")
subprocess.run([ffmpeg, "-y", "-v", "error", "-loop", "1", "-i", os.path.join(FIX, "v_frame0.png"),
                "-t", "8", "-pix_fmt", "yuv420p", silent], check=True)
final = os.path.join(FIX, "briefing_speech.mp4")
subprocess.run([ffmpeg, "-y", "-v", "error", "-i", silent, "-i", wav,
                "-c:v", "copy", "-c:a", "aac", "-shortest", final], check=True)
print("briefing_speech.mp4:", os.path.getsize(final), "bytes")
