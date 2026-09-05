"""E2E: video WITH spoken audio -> Whisper transcript via Groq."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_transcript.db"
if os.path.exists("test_transcript.db"):
    os.remove("test_transcript.db")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
r = client.post("/api/auth/register", json={"email": "av@example.com", "name": "T", "password": "S3curePass!x"})
H = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = client.post("/api/projects", json={"name": "Transcript Test"}, headers=H)
pid = r.json()["id"]

FIX = os.path.join(os.environ.get("TEMP", "/tmp"), "tai_fixtures")
with open(os.path.join(FIX, "briefing_speech.mp4"), "rb") as f:
    r = client.post("/api/sources/upload",
                    files={"file": ("briefing_speech.mp4", f, "video/mp4")},
                    data={"project_id": pid}, headers=H)
print("upload:", r.status_code)
body = r.json()
print("status:", body.get("status"), "| error:", body.get("error") or body.get("detail") or "-")

# inspect extracted text for the transcript
r = client.get(f"/api/sources?project_id={pid}", headers=H)
src = r.json()[0]
r = client.get(f"/api/sources/{src['id']}", headers=H)
text = r.json().get("raw_text", "")
meta = r.json().get("meta_json", {})
print("transcribed flag:", meta.get("transcribed"))
print("has 'Spoken audio transcript' section:", "Spoken audio transcript" in text)
probe_words = ["meridian", "fourteen", "march", "authentication", "records"]
found = [w for w in probe_words if w in text.lower()]
print("transcript probe words found:", found)
ok = bool(meta.get("transcribed")) and len(found) >= 3
print("transcript excerpt:", text[text.find("transcript"):text.find("transcript") + 200] if "transcript" in text else "-")

if os.path.exists("test_transcript.db"):
    try:
        os.remove("test_transcript.db")
    except PermissionError:
        pass

print()
print("RESULT:", "TRANSCRIPTION WORKS" if ok else "TRANSCRIPTION FAILED")
import sys
sys.exit(0 if ok else 1)
