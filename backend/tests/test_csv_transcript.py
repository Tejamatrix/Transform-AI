"""E2E: CSV ingestion + video transcript export endpoint."""
import io
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_csv.db"
if os.path.exists("test_csv.db"):
    os.remove("test_csv.db")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
r = client.post("/api/auth/register", json={"email": "csv@example.com", "name": "T", "password": "S3curePass!x"})
H = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = client.post("/api/projects", json={"name": "Data"}, headers=H)
pid = r.json()["id"]

ok = True

# ---- CSV ingestion ----
CSV = """Department,Incidents,Records_Exposed,Hours_Downtime
Treasury,4,12000,30
Client Services,3,15000,28
Risk,2,6000,18
IT Operations,5,5000,20
"""
r = client.post("/api/sources/upload",
                files={"file": ("incidents.csv", io.BytesIO(CSV.encode()), "text/csv")},
                data={"project_id": pid}, headers=H)
print("csv upload:", r.status_code)
body = r.json()
print("  status:", body.get("status"), "| type:", body.get("source_type"), "| chars:", body.get("char_count"))
if body.get("status") != "ready" or body.get("source_type") != "csv":
    ok = False
    print("  error:", body.get("error") or body.get("detail"))

# analysis should read the data
r = client.post(f"/api/analysis/{pid}", headers=H)
print("analysis:", r.status_code)
if r.status_code == 201:
    c = r.json()["content"]
    print("  stats:", len(c["statistics"]), "| facts:", len(c["key_facts"]))
    joined = str(c["statistics"]) + str(c["summary"])
    if "14" not in joined and "5000" not in joined:
        print("  WARN: numbers not referenced")
else:
    ok = False
    print("  detail:", str(r.json())[:200])

# ---- transcript endpoint (on the video from earlier fixtures if available) ----
FIX = os.path.join(os.environ.get("TEMP", "/tmp"), "tai_fixtures")
vid = os.path.join(FIX, "briefing_speech.mp4")
if os.path.exists(vid):
    r = client.post("/api/sources/upload",
                    files={"file": ("briefing.mp4", open(vid, "rb"), "video/mp4")},
                    data={"project_id": pid}, headers=H)
    sid = r.json().get("id")
    print("video upload:", r.status_code, body.get("status"))
    r = client.get(f"/api/sources/{sid}/transcript", headers=H)
    print("transcript endpoint:", r.status_code)
    if r.status_code == 200:
        j = r.json()
        print("  transcript len:", len(j.get("transcript", "")))
        print("  excerpt:", j["transcript"][:120])
    else:
        ok = False
        print("  detail:", str(r.json())[:150])

if os.path.exists("test_csv.db"):
    try:
        os.remove("test_csv.db")
    except PermissionError:
        pass

print()
print("RESULT:", "CSV + TRANSCRIPT PASSED" if ok else "CHECKS FAILED")
import sys
sys.exit(0 if ok else 1)
