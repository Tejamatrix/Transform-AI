"""Create test fixtures: an advisory slide image + a 2-scene briefing video."""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

FIX = os.path.join(os.environ.get("TEMP", "/tmp"), "tai_fixtures")
os.makedirs(FIX, exist_ok=True)
FONT = r"C:\Windows\Fonts\arial.ttf"


def slide(lines, path):
    img = Image.new("RGB", (1280, 720), "white")
    d = ImageDraw.Draw(img)
    y = 200
    for text, size, color in lines:
        f = ImageFont.truetype(FONT, size)
        w = d.textlength(text, font=f)
        d.text(((1280 - w) / 2, y), text, font=f, fill=color)
        y += size + 30
    img.save(path, format="PNG")
    print("created", path)


def find(*names):
    for n in names:
        p = __import__("shutil").which(n)
        if p:
            return p
    return None


ffmpeg = find("ffmpeg")
ffprobe = find("ffprobe")
print("ffmpeg:", ffmpeg)
print("ffprobe:", ffprobe)

slide([
    ("SECURITY ADVISORY 2026", 48, "black"),
    ("Ransomware Incident Response", 36, "black"),
    ("Affected 14 departments and 38000 records", 24, (60, 60, 60)),
    ("Severity HIGH - Zero-day exploited", 24, (60, 60, 60)),
], os.path.join(FIX, "advisory_slide.png"))

slide([
    ("CYBER BRIEFING MARCH 2026", 44, "black"),
    ("Timeline: 14 March detection, 20 March mitigation", 28, "black"),
], os.path.join(FIX, "frame0.png"))

slide([
    ("RECOMMEND: Enable MFA and patch systems", 32, "black"),
], os.path.join(FIX, "frame4.png"))

if not ffmpeg:
    print("NO FFMPEG - video fixture skipped")
    sys.exit(0)

p1 = os.path.join(FIX, "part1.mp4")
p2 = os.path.join(FIX, "part2.mp4")
out = os.path.join(FIX, "briefing.mp4")
subprocess.run([ffmpeg, "-y", "-v", "error", "-loop", "1", "-i", os.path.join(FIX, "frame0.png"),
                "-t", "3", "-pix_fmt", "yuv420p", p1], check=True)
subprocess.run([ffmpeg, "-y", "-v", "error", "-loop", "1", "-i", os.path.join(FIX, "frame4.png"),
                "-t", "3", "-pix_fmt", "yuv420p", p2], check=True)
subprocess.run([ffmpeg, "-y", "-v", "error", "-i", p1, "-i", p2,
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[out]",
                "-map", "[out]", "-pix_fmt", "yuv420p", out], check=True)
print("created", out, os.path.getsize(out), "bytes")
