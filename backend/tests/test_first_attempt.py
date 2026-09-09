"""First-attempt reliability test: run analyze N times in fresh projects.
Every attempt must produce a blueprint — no 'invalid structure' errors."""
import os
import time

os.environ["DATABASE_URL"] = "sqlite:///./test_first.db"
if os.path.exists("test_first.db"):
    os.remove("test_first.db")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
r = client.post("/api/auth/register", json={"email": "first@example.com", "name": "T", "password": "S3curePass!x"})
H = {"Authorization": f"Bearer {r.json()['access_token']}"}

REPORT = """
Cybersecurity Incident Report - Q1 Network Compromise

On 14 March 2026, Meridian Financial Systems detected unauthorized access to its
core banking network. The ShadowLock ransomware variant was deployed through a
phishing campaign targeting 12 employees.

14 departments were affected, including Treasury and Client Services.
Approximately 38,000 customer records were exposed. 230 servers were encrypted;
31 were restored by 20 March 2026.

The organisation should enforce MFA on all remote access, patch affected systems
immediately, rotate privileged credentials, and review email filtering policies.
"""

N = 4
passed = 0
for i in range(N):
    r = client.post("/api/projects", json={"name": f"First-attempt {i+1}"}, headers=H)
    pid = r.json()["id"]
    client.post("/api/sources/text", json={"project_id": pid, "title": "Report", "text": REPORT}, headers=H)
    t0 = time.time()
    r = client.post(f"/api/analysis/{pid}", headers=H)
    dt = time.time() - t0
    ok = r.status_code == 201
    detail = ""
    if ok:
        c = r.json()["content"]
        detail = f"domain={c['domain']} facts={len(c['key_facts'])} entities={len(c['entities'])}"
        passed += 1
    else:
        detail = str(r.json())[:120]
    print(f"[{'PASS' if ok else 'FAIL'}] attempt {i+1}: {dt:.1f}s - {detail}")
    time.sleep(1)

if os.path.exists("test_first.db"):
    try:
        os.remove("test_first.db")
    except PermissionError:
        pass

print()
print(f"RESULT: {passed}/{N} first-attempt analyses succeeded")
import sys
sys.exit(0 if passed == N else 1)
