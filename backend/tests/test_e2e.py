"""End-to-end workflow smoke test: register -> project -> source -> analyze ->
blueprint -> multi-generate -> validate -> edit -> versions -> export."""
import io
import sys

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FAILS = []


def check(name, cond, extra=""):
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name} {extra}")
    if not cond:
        FAILS.append(name)


# 1. health
r = client.get("/api/health")
check("health", r.status_code == 200)

# 2. register
email = "demo@example.com"
r = client.post("/api/auth/register", json={"email": email, "name": "Demo Operator", "password": "S3curePass!x"})
check("register", r.status_code == 201, r.json().get("detail", "") if r.status_code != 201 else "")
token = r.json().get("access_token", "")
H = {"Authorization": f"Bearer {token}"}

# duplicate register rejected
r2 = client.post("/api/auth/register", json={"email": email, "name": "X", "password": "S3curePass!x"})
check("duplicate register rejected", r2.status_code == 409)

# login
r = client.post("/api/auth/login", json={"email": email, "password": "S3curePass!x"})
check("login", r.status_code == 200)

# bad login
r = client.post("/api/auth/login", json={"email": email, "password": "wrongpass123"})
check("bad login rejected", r.status_code == 401)

# 3. project
r = client.post("/api/projects", json={"name": "Cybersecurity Campaign", "description": "Demo"}, headers=H)
check("create project", r.status_code == 201)
project_id = r.json()["id"]

# 4. text source (simulated incident report)
report = """
Cybersecurity Incident Report — Q1 Network Compromise

On 14 March 2026, Meridian Financial Systems detected unauthorized access to its
core banking network. The investigation confirmed that the "ShadowLock" ransomware
variant was deployed through a phishing campaign targeting 12 employees.

Key findings:
- 14 departments were affected, including Treasury and Client Services.
- Approximately 38,000 customer records were exposed.
- 230 servers were encrypted; 31 were restored from backups by 20 March 2026.
- The attackers exploited a zero-day vulnerability in OpenSSL (CVE-2026-1138).
- Downtime lasted 96 hours across primary data centers in Singapore City.

"We isolated the affected segment within 40 minutes of detection," said the CISO.

Timeline:
14 March 2026 — Initial incident detected by SOC analysts.
15 March 2026 — Investigation started with external forensics team.
17 March 2026 — Government advisory issued by the National Cyber Authority.
20 March 2026 — Mitigation implemented and systems restored.

Risks: further credential stuffing attacks, reputational damage, regulatory
penalties under the Data Protection Act, and possible extortion attempts.

Recommendations: The organisation should enforce MFA on all remote access,
patch affected systems immediately, rotate privileged credentials, and review
email filtering policies. Employees must complete phishing-awareness training.
"""
r = client.post("/api/sources/text", json={"project_id": project_id, "title": "Cybersecurity Incident Report.pdf", "text": report}, headers=H)
check("add text source", r.status_code == 201, str(r.json()) if r.status_code != 201 else "")
source_id = r.json().get("id", "")
check("source ready", r.json().get("status") == "ready" and r.json().get("chunk_count", 0) > 0)

# 5. analysis -> blueprint
r = client.post(f"/api/analysis/{project_id}", headers=H)
check("analyze -> blueprint", r.status_code == 201, str(r.json())[:200] if r.status_code != 201 else "")
bp = r.json()
check("domain detected", bp["content"]["domain"] == "cybersecurity", bp["content"]["domain"])
check("intent detected", bp["content"]["intent"] == "alert", bp["content"]["intent"])
check("entities extracted", len(bp["content"]["entities"]) >= 3, str(len(bp["content"]["entities"])))
check("key facts extracted", len(bp["content"]["key_facts"]) >= 5, str(len(bp["content"]["key_facts"])))
check("timeline extracted", len(bp["content"]["timeline"]) >= 3, str(len(bp["content"]["timeline"])))
check("recommendations extracted", len(bp["content"]["recommendations"]) >= 1)
check("recommended outputs", "advisory" in bp["content"]["recommended_outputs"])
blueprint_id = bp["id"]

# blueprint edit
r = client.patch(f"/api/blueprints/{blueprint_id}", json={"content": {"summary": "Edited summary for demo."}}, headers=H)
check("blueprint edit", r.status_code == 200 and r.json()["content"]["summary"] == "Edited summary for demo.")
# revert
r = client.patch(f"/api/blueprints/{blueprint_id}", json={"content": {"summary": bp["content"]["summary"]}}, headers=H)

# 6. multi-output generation
r = client.post("/api/generate", json={
    "project_id": project_id, "blueprint_id": blueprint_id,
    "outputs": ["advisory", "executive_summary", "linkedin", "presentation", "infographic", "video_package", "x_thread"],
    "configuration": {"audience": "government_officials", "tone": "formal", "language": "English",
                      "detail": "detailed", "objective": "alert"},
}, headers=H)
check("generate accepted", r.status_code == 202, str(r.json())[:200] if r.status_code != 202 else "")
job_id = r.json()["id"]

import time
outputs = []
for _ in range(60):
    time.sleep(0.5)
    r = client.get(f"/api/generate/job/{job_id}", headers=H)
    if r.json().get("status") in ("completed", "failed"):
        break
check("generation job completed", r.json().get("status") == "completed", r.json().get("detail", ""))

r = client.get(f"/api/generate/project/{project_id}", headers=H)
outputs = r.json()
check("7 outputs generated", len(outputs) == 7, str(len(outputs)))
by_type = {o["output_type"]: o for o in outputs}

check("advisory has severity", by_type["advisory"]["content"].get("severity") in ("HIGH", "MEDIUM", "LOW"))
check("advisory actions", len(by_type["advisory"]["content"].get("recommended_actions", [])) >= 1)
check("exec summary sections", len(by_type["executive_summary"]["content"].get("sections", [])) >= 6)
check("linkedin variants", len(by_type["linkedin"]["content"].get("variants", [])) >= 1)
check("presentation slides", len(by_type["presentation"]["content"].get("slides", [])) >= 4)
check("video scenes", len(by_type["video_package"]["content"].get("scenes", [])) >= 3)
check("x posts <= 280", all(len(p) <= 280 for p in by_type["x_thread"]["content"].get("posts", [])))

# 7. validation (FactTrace)
adv_id = by_type["advisory"]["id"]
r = client.post(f"/api/validate/{adv_id}", headers=H)
check("validation run", r.status_code == 201, str(r.json())[:200] if r.status_code != 201 else "")
summary = r.json().get("summary", {})
check("validation counts", summary.get("total", 0) > 0, str(summary))

r = client.get(f"/api/validate/{adv_id}", headers=H)
check("validation fetch", r.json().get("validated") is True)
claims = r.json().get("claims", [])
supported = [c for c in claims if c["status"] in ("VERIFIED", "PARTIALLY_SUPPORTED") and c.get("evidence")]
check("facttrace evidence attached", len(supported) >= 1, f"{len(supported)} claims with evidence")

# 8. quality score
r = client.post(f"/api/export/{adv_id}/quality", headers=H)
check("quality score", r.status_code == 200 and "overall" in r.json(), str(r.json())[:150])

# 9. editing + versions
r = client.post(f"/api/generate/output/{adv_id}/edit", json={"action": "shorten", "section": "Risk"}, headers=H)
check("edit shorten", r.status_code == 200, str(r.json())[:150] if r.status_code != 200 else "")
r = client.post(f"/api/generate/output/{adv_id}/edit", json={"action": "change_tone", "tone": "urgent"}, headers=H)
check("edit tone", r.status_code == 200)
r = client.post(f"/api/generate/output/{adv_id}/edit",
                json={"action": "edit", "content": by_type["advisory"]["content"] | {"summary": "Operator-verified summary."}},
                headers=H)
check("manual edit", r.status_code == 200 and r.json()["content"]["summary"] == "Operator-verified summary.")
check("version bumped", r.json()["current_version"] == 4, str(r.json()["current_version"]))

r = client.get(f"/api/generate/output/{adv_id}/versions", headers=H)
check("version history", r.status_code == 200 and len(r.json()) == 4, str(len(r.json())))

# 10. regenerate
r = client.post(f"/api/generate/output/{by_type['linkedin']['id']}/regenerate", headers=H)
check("regenerate", r.status_code == 200, str(r.json())[:150] if r.status_code != 200 else "")

# 11. export
for fmt, oid in [("md", adv_id), ("docx", adv_id), ("srt", by_type["video_package"]["id"]),
                 ("txt", by_type["x_thread"]["id"]), ("pptx", by_type["presentation"]["id"])]:
    r = client.post(f"/api/export/{oid}", json={"format": fmt}, headers=H)
    ok = r.status_code == 200 and len(r.content) > 50
    check(f"export {fmt}", ok, f"{len(r.content)} bytes")

# pptx magic bytes (ZIP)
r = client.post(f"/api/export/{by_type['presentation']['id']}", json={"format": "pptx"}, headers=H)
check("pptx valid zip", r.content[:2] == b"PK")

# hindi localized exec summary (offline headings)
r = client.post("/api/generate", json={
    "project_id": project_id, "blueprint_id": blueprint_id,
    "outputs": ["executive_summary"],
    "configuration": {"audience": "government_officials", "tone": "formal", "language": "Hindi",
                      "detail": "brief", "objective": "inform"},
}, headers=H)
hindi_job = r.json()["id"]
for _ in range(40):
    time.sleep(0.5)
    r = client.get(f"/api/generate/job/{hindi_job}", headers=H)
    if r.json().get("status") in ("completed", "failed"):
        break
check("hindi generation completed", r.json().get("status") == "completed", r.json().get("detail", ""))
r = client.get(f"/api/generate/project/{project_id}", headers=H)
hindi_out = [o for o in r.json() if o["output_type"] == "executive_summary" and o["config"].get("language") == "Hindi"]
check("hindi output exists", len(hindi_out) == 1)
if hindi_out:
    headings = [sec["heading"] for sec in hindi_out[0]["content"].get("sections", [])]
    check("hindi headings localized", any("\u0905" <= h[0] <= "\u097F" for h in headings if h), str(headings[:3]))

# 12. isolation: second user cannot see first user's project
r = client.post("/api/auth/register", json={"email": "intruder@example.com", "name": "Bad", "password": "S3curePass!x"})
H2 = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = client.get(f"/api/generate/project/{project_id}", headers=H2)
check("user isolation (outputs)", r.status_code == 403, str(r.status_code))
r = client.get(f"/api/blueprints/{blueprint_id}", headers=H2)
check("user isolation (blueprint)", r.status_code == 403)

# 13. AI agent (grounded Q&A over retrieved context)
r = client.post("/api/agent", json={"project_id": project_id, "question": "What are the key facts and risks?"}, headers=H)
check("agent ask", r.status_code == 200, str(r.json())[:200] if r.status_code != 200 else "")
ans = r.json().get("answer", "")
check("agent answer non-empty", len(ans) > 30, ans[:80])
check("agent cites sources", "page" in ans or len(r.json().get("evidence", [])) >= 1)

# agent rejects other user's project
r = client.post("/api/agent", json={"project_id": project_id, "question": "What happened?"}, headers=H2)
check("agent isolation", r.status_code == 403)

# 14. audit log
r = client.get("/api/audit", headers=H)
check("audit log", r.status_code == 200 and len(r.json()) >= 8, str(len(r.json())))
if FAILS:
    print(f"RESULT: {len(FAILS)} FAILED -> {FAILS}")
    sys.exit(1)
print("RESULT: ALL CHECKS PASSED")
