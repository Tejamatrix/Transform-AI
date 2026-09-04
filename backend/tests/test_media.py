"""Ingestion test: image (OCR) and video (frame OCR + metadata) as sources."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_media.db"
for f in ("test_media.db",):
    if os.path.exists(f):
        os.remove(f)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
r = client.post("/api/auth/register", json={"email": "media@example.com", "name": "T", "password": "S3curePass!x"})
H = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = client.post("/api/projects", json={"name": "Media Sources"}, headers=H)
pid = r.json()["id"]

FIX = os.path.join(os.environ.get("TEMP", "/tmp"), "tai_fixtures")
ok = True

# ---- image ingestion ----
with open(os.path.join(FIX, "advisory_slide.png"), "rb") as f:
    r = client.post("/api/sources/upload",
                    files={"file": ("advisory_slide.png", f, "image/png")},
                    data={"project_id": pid}, headers=H)
print("image upload:", r.status_code)
body = r.json()
print("  status:", body.get("status"), "| type:", body.get("source_type"),
      "| chars:", body.get("char_count"), "| chunks:", body.get("chunk_count"))
if body.get("status") != "ready" or body.get("char_count", 0) < 50:
    ok = False
    print("  error:", body.get("error") or body.get("detail"))

# ---- video ingestion ----
with open(os.path.join(FIX, "briefing.mp4"), "rb") as f:
    r = client.post("/api/sources/upload",
                    files={"file": ("briefing.mp4", f, "video/mp4")},
                    data={"project_id": pid}, headers=H)
print("video upload:", r.status_code)
body = r.json()
print("  status:", body.get("status"), "| type:", body.get("source_type"),
      "| chars:", body.get("char_count"), "| chunks:", body.get("chunk_count"))
if body.get("status") != "ready" or body.get("char_count", 0) < 50:
    ok = False
    print("  error:", body.get("error") or body.get("detail"))

# ---- analysis over mixed media ----
r = client.post(f"/api/analysis/{pid}", headers=H)
print("analysis:", r.status_code)
if r.status_code == 201:
    c = r.json()["content"]
    print("  domain:", c["domain"], "| facts:", len(c["key_facts"]),
          "| entities:", len(c["entities"]), "| confidence:", c["confidence"])
    if len(c["key_facts"]) < 2:
        ok = False
else:
    ok = False
    print("  detail:", str(r.json())[:200])

# ---- generate from video+image derived blueprint ----
bp_id = r.json()["id"]
r = client.post("/api/generate", headers=H, json={
    "project_id": pid, "blueprint_id": bp_id, "outputs": ["advisory"],
    "configuration": {"audience": "security_professionals", "tone": "urgent"},
})
import time
job = r.json()["id"]
for _ in range(40):
    time.sleep(0.5)
    r = client.get(f"/api/generate/job/{job}", headers=H)
    if r.json().get("status") in ("completed", "failed"):
        break
print("generation:", r.json().get("status"))
if r.json().get("status") != "completed":
    ok = False

print()
print("RESULT:", "ALL MEDIA CHECKS PASSED" if ok else "MEDIA CHECKS FAILED")

import sys
sys.exit(0 if ok else 1)
