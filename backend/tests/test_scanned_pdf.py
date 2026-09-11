"""E2E: scanned (image-only) PDF -> OCR extraction."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_scan.db"
if os.path.exists("test_scan.db"):
    os.remove("test_scan.db")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
r = client.post("/api/auth/register", json={"email": "scan@example.com", "name": "T", "password": "S3curePass!x"})
H = {"Authorization": "Bearer " + r.json()["access_token"]}
r = client.post("/api/projects", json={"name": "Scan"}, headers=H)
pid = r.json()["id"]

# build an IMAGE-ONLY PDF (no text layer) from a rendered text image
from PIL import Image, ImageDraw, ImageFont
FONT = r"C:\Windows\Fonts\arial.ttf"
img = Image.new("RGB", (1240, 700), "white")
d = ImageDraw.Draw(img)
lines = [
    ("Cybersecurity Incident Report", 44),
    ("14 March 2026 - Meridian Financial Systems", 28),
    ("14 departments affected, 38000 records exposed", 26),
    ("Enable MFA and patch all systems", 26),
]
y = 80
for text, size in lines:
    f = ImageFont.truetype(FONT, size)
    d.text((80, y), text, font=f, fill="black")
    y += size + 26
img_pdf = os.path.join(os.environ.get("TEMP", "/tmp"), "tai_fixtures", "scanned.pdf")
img.save(img_pdf, "PDF", resolution=150)
print("fixture:", os.path.getsize(img_pdf), "bytes (image-only PDF)")

import io
with open(img_pdf, "rb") as f:
    r = client.post("/api/sources/upload",
                    files={"file": ("scanned.pdf", f, "application/pdf")},
                    data={"project_id": pid}, headers=H)
print("upload:", r.status_code)
body = r.json()
print("status:", body.get("status"), "| type:", body.get("source_type"), "| chars:", body.get("char_count"))
print("error:", body.get("error") or body.get("detail") or "-")

ok = False
if body.get("status") == "ready":
    r = client.get(f"/api/sources?project_id={pid}", headers=H)
    sid = r.json()[0]["id"]
    r = client.get(f"/api/sources/{sid}", headers=H)
    text = r.json()["raw_text"]
    meta = r.json()["meta_json"]
    print("ocr flag:", meta.get("ocr"), "| ocr_pages:", meta.get("ocr_pages"))
    found = [w for w in ["meridian", "departments", "38000", "mfa"] if w in text.lower()]
    print("probe words:", found)
    ok = len(found) >= 3

if os.path.exists("test_scan.db"):
    try:
        os.remove("test_scan.db")
    except PermissionError:
        pass

print()
print("RESULT:", "SCANNED-PDF OCR WORKS" if ok else "SCANNED-PDF OCR FAILED")
import sys
sys.exit(0 if ok else 1)
