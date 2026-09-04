"""E2E multi-language generation test: Hindi + Telugu outputs through the API."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_lang.db"
if os.path.exists("test_lang.db"):
    os.remove("test_lang.db")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
r = client.post("/api/auth/register", json={"email": "lang@example.com", "name": "T", "password": "S3curePass!x"})
H = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = client.post("/api/projects", json={"name": "Lang Demo"}, headers=H)
pid = r.json()["id"]

report = """
Cybersecurity Incident Report - Q1 Network Compromise

On 14 March 2026, Meridian Financial Systems detected unauthorized access to its
core banking network. The ShadowLock ransomware variant was deployed through a
phishing campaign targeting 12 employees.

14 departments were affected, including Treasury and Client Services.
Approximately 38,000 customer records were exposed. 230 servers were encrypted;
31 were restored by 20 March 2026. The attackers exploited a zero-day
vulnerability in OpenSSL (CVE-2026-1138).

The organisation should enforce MFA on all remote access, patch affected systems
immediately, rotate privileged credentials, and review email filtering policies.
"""
r = client.post("/api/sources/text", json={"project_id": pid, "title": "Incident Report", "text": report}, headers=H)
print("source:", r.json().get("status"))
r = client.post(f"/api/analysis/{pid}", headers=H)
bp = r.json()["id"]
print("blueprint:", r.status_code)

import time
ok = True

def gen_and_check(output, lang, expect_script_first):
    r = client.post("/api/generate", headers=H, json={
        "project_id": pid, "blueprint_id": bp, "outputs": [output],
        "configuration": {"audience": "government_officials", "tone": "formal",
                          "language": lang, "detail": "brief", "objective": "alert"},
    })
    job = r.json()["id"]
    for _ in range(60):
        time.sleep(0.5)
        r = client.get(f"/api/generate/job/{job}", headers=H)
        if r.json().get("status") in ("completed", "failed"):
            break
    if r.json().get("status") != "completed":
        print(f"[FAIL] {output}/{lang}: generation failed - {r.json().get('detail','')}")
        return False
    r = client.get(f"/api/generate/project/{pid}", headers=H)
    out = [o for o in r.json() if o["output_type"] == output and o["config"].get("language") == lang]
    if not out:
        print(f"[FAIL] {output}/{lang}: output missing")
        return False
    content = out[-1]["content"]
    # check a sample of user-visible strings for the target script
    sample = str(content)[:1200]
    ranges = {"Hindi": ("\u0900", "\u097F"), "Telugu": ("\u0C00", "\u0C7F")}
    lo, hi = ranges[lang]
    hits = sum(1 for ch in sample if lo <= ch <= hi)
    passed = hits > 10
    print(f"[{'PASS' if passed else 'FAIL'}] {output}/{lang}: native chars in content = {hits}")
    return passed

ok &= gen_and_check("executive_summary", "Hindi", True)
ok &= gen_and_check("linkedin", "Hindi", True)
ok &= gen_and_check("advisory", "Telugu", True)
ok &= gen_and_check("x_thread", "Hindi", True)

# agent in Hindi
r = client.post("/api/agent", json={"project_id": pid,
                 "question": "मुख्य जोखिम क्या हैं?", "headers": None} if False else
                {"project_id": pid, "question": "मुख्य जोखिम क्या हैं?"}, headers=H)
ans = r.json().get("answer", "")
hindi_chars = sum(1 for ch in ans if "\u0900" <= ch <= "\u097F")
passed = hindi_chars > 10
print(f"[{'PASS' if passed else 'FAIL'}] agent/Hindi question -> hindi chars = {hindi_chars}")
print("   ->", ans[:160].replace("\n", " "))
ok &= passed

if os.path.exists("test_lang.db"):
    try:
        os.remove("test_lang.db")
    except PermissionError:
        pass

print()
print("RESULT:", "ALL LANGUAGE CHECKS PASSED" if ok else "LANGUAGE CHECKS FAILED")
import sys
sys.exit(0 if ok else 1)
