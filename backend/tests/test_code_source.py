"""E2E: source-code file as a source -> code-aware blueprint -> outputs."""
import os
import time

os.environ["DATABASE_URL"] = "sqlite:///./test_code.db"
if os.path.exists("test_code.db"):
    os.remove("test_code.db")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
r = client.post("/api/auth/register", json={"email": "dev@example.com", "name": "T", "password": "S3curePass!x"})
H = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = client.post("/api/projects", json={"name": "Code Review"}, headers=H)
pid = r.json()["id"]

CODE = '''
import hashlib
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

def hash_password(password: str) -> str:
    """Hash a password for storage. NOTE: plain hash, no salt."""
    return hashlib.sha256(password.encode()).hexdigest()

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = '%s' AND password = '%s'"
                % (data["email"], data["password"]))
    user = cur.fetchone()
    conn.close()
    if user:
        return jsonify({"token": "static-hardcoded-token-123"})
    return jsonify({"error": "invalid"}), 401

API_KEY = "sk-live-1234567890abcdef"
'''

ok = True

# upload the code file
import io
r = client.post("/api/sources/upload",
                files={"file": ("auth_service.py", io.BytesIO(CODE.encode()), "text/x-python")},
                data={"project_id": pid}, headers=H)
print("code upload:", r.status_code)
body = r.json()
print("  status:", body.get("status"), "| type:", body.get("source_type"),
      "| chars:", body.get("char_count"))
if body.get("status") != "ready" or body.get("source_type") != "code":
    ok = False
    print("  error:", body.get("error") or body.get("detail"))

# analyze -> code-aware blueprint
r = client.post(f"/api/analysis/{pid}", headers=H)
print("analysis:", r.status_code)
if r.status_code == 201:
    c = r.json()["content"]
    print("  domain:", c["domain"], "| facts:", len(c["key_facts"]),
          "| risks:", len(c["risks"]), "| entities:", len(c["entities"]))
    print("  summary:", c["summary"][:180])
    if len(c["key_facts"]) < 2:
        ok = False
        print("  FAIL: too few facts extracted from code")
else:
    ok = False
    print("  detail:", str(r.json())[:200])

# generate an executive summary describing the code
bp = r.json()["id"]
r = client.post("/api/generate", headers=H, json={
    "project_id": pid, "blueprint_id": bp, "outputs": ["executive_summary"],
    "configuration": {"audience": "technical_teams", "tone": "technical",
                      "detail": "moderate", "objective": "inform"},
})
job = r.json()["id"]
for _ in range(90):
    time.sleep(0.5)
    r = client.get(f"/api/generate/job/{job}", headers=H)
    if r.json().get("status") in ("completed", "failed"):
        break
print("generation:", r.json().get("status"))
if r.json().get("status") != "completed":
    ok = False

if os.path.exists("test_code.db"):
    try:
        os.remove("test_code.db")
    except PermissionError:
        pass

print()
print("RESULT:", "ALL CODE CHECKS PASSED" if ok else "CODE CHECKS FAILED")
import sys
sys.exit(0 if ok else 1)
