"""Focused test: generic questions against the incident report."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_agent.db"
if os.path.exists("test_agent.db"):
    os.remove("test_agent.db")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
r = client.post("/api/auth/register", json={"email": "ag@example.com", "name": "T", "password": "S3curePass!x"})
H = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = client.post("/api/projects", json={"name": "Incident"}, headers=H)
pid = r.json()["id"]

report = """
Cybersecurity Incident Report - Q1 Network Compromise

On 14 March 2026, Meridian Financial Systems detected unauthorized access to its
core banking network. The investigation confirmed that the ShadowLock ransomware
variant was deployed through a phishing campaign targeting 12 employees.

14 departments were affected, including Treasury and Client Services.
Approximately 38,000 customer records were exposed. 230 servers were encrypted;
31 were restored from backups by 20 March 2026. The attackers exploited a
zero-day vulnerability in OpenSSL (CVE-2026-1138).

The organisation should enforce MFA on all remote access, patch affected systems
immediately, rotate privileged credentials, and review email filtering policies.
Employees must complete phishing-awareness training.
"""
client.post("/api/sources/text", json={"project_id": pid, "title": "Incident Report", "text": report}, headers=H)
client.post(f"/api/analysis/{pid}", headers=H)

QUESTIONS = [
    "What are the key facts?",
    "What is the timeline of events?",
    "What are the main risks?",
    "What actions are recommended?",
    "Who was affected?",
]

for q in QUESTIONS:
    r = client.post("/api/agent", json={"project_id": pid, "question": q}, headers=H)
    a = r.json().get("answer", "")
    fallback = a.startswith("The retrieved source context does not cover")
    status = "PASS" if (r.status_code == 200 and not fallback) else "FAIL"
    print(f"[{status}] {q}")
    print("   ->", a.replace("\n", " ")[:150])
    print("   evidence:", len(r.json().get("evidence", [])))

os.remove("test_agent.db")
