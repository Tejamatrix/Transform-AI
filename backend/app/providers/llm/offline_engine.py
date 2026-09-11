"""Offline deterministic "LLM" engine.

The service layer sends the same prompts it would send to a real LLM. This
engine parses the structured context blocks (---BLUEPRINT---, ---EVIDENCE---,
etc.) embedded in the prompt and produces schema-valid JSON responses using
rule-based extraction and composition.

This keeps the entire product workflow (analyze -> blueprint -> generate ->
validate -> edit -> export) fully functional with zero API keys, and gives
tests a deterministic provider. Swapping LLM_PROVIDER=openai upgrades quality
without touching any other code.
"""
from __future__ import annotations

import json
import re

import numpy as np

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

DOMAIN_KEYWORDS = {
    "cybersecurity": ["cyber", "malware", "ransomware", "breach", "phishing", "hack", "vulnerab", "exploit", "ddos", "botnet", "incident response", "apt", "zero-day", "firewall", "encryption", "threat actor", "patch"],
    "health": ["health", "disease", "outbreak", "patient", "clinical", "hospital", "vaccine", "symptom", "medical", "who ", "cdc"],
    "finance": ["finance", "market", "revenue", "investment", "fiscal", "budget", "economic", "inflation", "stock", "banking"],
    "policy": ["policy", "regulation", "legislation", "government", "ministry", "act ", "compliance", "directive", "guideline"],
    "technology": ["software", "platform", "ai ", "cloud", "api", "data center", "startup", "product launch", "digital"],
    "infrastructure": ["grid", "railway", "highway", "utility", "infrastructure", "construction", "water supply", "power outage"],
}

INTENT_KEYWORDS = {
    "alert": ["urgent", "alert", "warning", "critical", "immediate", "breach", "attack", "outage"],
    "awareness": ["awareness", "educate", "inform", "understand", "learn"],
    "report": ["report", "findings", "analysis", "assessment", "review"],
    "promote": ["launch", "announce", "celebrate", "introducing", "proud"],
}

ENTITY_TYPES = {
    "Organisation": r"\b([A-Z][A-Za-z0-9&.\- ]{2,60}(?:Inc|Ltd|LLC|Corp|Corporation|Ministry|Department|Authority|Agency|Bank|University|Institute|Systems|Group|Solutions))\b",
    "Location": r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b(?=\s+(?:City|State|Province|Region|District))",
    "Technology": r"\b(Windows|Linux|Apache|OpenSSL|VPN|IoT|API|AI|ML|AWS|Azure|Active Directory|VPN|MFA|SQL|SSH|TLS|HTTP)\b",
    "Threat": r"\b(ransomware|phishing|malware|botnet|data breach|zero-day|DDoS|social engineering|insider threat|credential stuffing)\b",
    "Person": r"\b(Mr\.|Ms\.|Dr\.|Prof\.)\s?([A-Z][a-z]+(?: [A-Z][a-z]+)?)",
    "Policy": r"\b([A-Z][A-Za-z ]{4,60}(?:Act|Policy|Regulation|Directive|Framework|Guideline))\b",
}

THREAT_WORDS = ["risk", "threat", "vulnerab", "breach", "exposure", "attack", "compromis", "outage", "impact", "disruption", "loss", "unauthorized", "malicious"]
RECO_WORDS = ["should", "must", "recommend", "advise", "ensure", "implement", "enable", "update", "patch", "verify", "review", "consider", "rotate", "reset"]
STAT_RE = re.compile(r"\b\d[\d,.]*\s?(?:%|percent|users|accounts|records|systems|servers|departments|employees|customers|hours|days|minutes|GB|TB|MB|million|thousand|lakh|crore)?\b")

OUTPUT_LABELS = {
    "executive_summary": "Executive Summary", "advisory": "Security Advisory",
    "linkedin": "LinkedIn Post", "x_thread": "X Thread", "presentation": "Presentation",
    "infographic": "Infographic", "video_package": "Video Package",
}

AUDIENCE_LABELS = {
    "general_public": "the general public", "government_officials": "government officials",
    "executives": "executive leadership", "technical_teams": "technical teams",
    "security_professionals": "security professionals", "students": "students",
    "customers": "customers", "internal_employees": "internal employees",
    "custom": "the target audience",
}

# Offline localization: section headings for demo multi-language support.
# Full native text is produced by a live LLM provider (see prompts LANGUAGE RULE).
LANG_HEADINGS = {
    "hindi": {
        "Executive Overview": "à¤•à¤¾à¤°à¥à¤¯à¤•à¤¾à¤°à¥€ à¤…à¤µà¤²à¥‹à¤•à¤¨",
        "Key Findings": "à¤®à¥à¤–à¥à¤¯ à¤¨à¤¿à¤·à¥à¤•à¤°à¥à¤·",
        "Important Statistics": "à¤®à¤¹à¤¤à¥à¤µà¤ªà¥‚à¤°à¥à¤£ à¤†à¤‚à¤•à¤¡à¤¼à¥‡",
        "Risks": "à¤œà¥‹à¤–à¤¿à¤®",
        "Business / Operational Impact": "à¤µà¥à¤¯à¤¾à¤µà¤¸à¤¾à¤¯à¤¿à¤• / à¤ªà¤°à¤¿à¤šà¤¾à¤²à¤¨ à¤ªà¥à¤°à¤­à¤¾à¤µ",
        "Recommendations": "à¤¸à¤¿à¤«à¤¼à¤¾à¤°à¤¿à¤¶à¥‡à¤‚",
        "Conclusion": "à¤¨à¤¿à¤·à¥à¤•à¤°à¥à¤·",
        "Timeline of Events": "à¤˜à¤Ÿà¤¨à¤¾à¤“à¤‚ à¤•à¥€ à¤¸à¤®à¤¯à¤°à¥‡à¤–à¤¾",
        "Recommendations & Next Steps": "à¤¸à¤¿à¤«à¤¼à¤¾à¤°à¤¿à¤¶à¥‡à¤‚ à¤”à¤° à¤…à¤—à¤²à¥‡ à¤•à¤¦à¤®",
        "Finding": "à¤¨à¤¿à¤·à¥à¤•à¤°à¥à¤·",
    },
    "telugu": {
        "Executive Overview": "à°•à°¾à°°à±à°¯à°¨à°¿à°°à±à°µà°¾à°¹à°• à°…à°µà°²à±‹à°•à°¨à°‚",
        "Key Findings": "à°®à±à°–à±à°¯à°®à±ˆà°¨ à°†à°µà°¿à°·à±à°•à°°à°£à°²à±",
        "Important Statistics": "à°®à±à°–à±à°¯à°®à±ˆà°¨ à°—à°£à°¾à°‚à°•à°¾à°²à±",
        "Risks": "à°ªà±à°°à°®à°¾à°¦à°¾à°²à±",
        "Business / Operational Impact": "à°µà±à°¯à°¾à°ªà°¾à°° / à°•à°¾à°°à±à°¯à°¾à°šà°°à°£ à°ªà±à°°à°­à°¾à°µà°‚",
        "Recommendations": "à°¸à°¿à°«à°¾à°°à°¸à±à°²à±",
        "Conclusion": "à°®à±à°—à°¿à°‚à°ªà±",
        "Timeline of Events": "à°¸à°‚à°˜à°Ÿà°¨à°² à°•à°¾à°²à°•à±à°°à°®à°‚",
        "Recommendations & Next Steps": "à°¸à°¿à°«à°¾à°°à°¸à±à°²à± à°®à°°à°¿à°¯à± à°¤à°¦à±à°ªà°°à°¿ à°šà°°à±à°¯à°²à±",
        "Finding": "à°†à°µà°¿à°·à±à°•à°°à°£",
    },
}


def _t(config: dict, key: str) -> str:
    lang = (config.get("language") or "English").lower()
    return LANG_HEADINGS.get(lang, {}).get(key, key)

TONE_OPENERS = {
    "professional": "", "formal": "", "neutral": "",
    "urgent": "URGENT: ", "educational": "", "persuasive": "", "technical": "", "conversational": "",
}


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    # protect common abbreviations so splitting stays accurate
    text = re.sub(r"\b(e\.g|i\.e|vs|etc|Dr|Mr|Ms|Prof|Inc|Ltd|No|approx|Fig)\.\s", r"\1<DOT> ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text)
    cleaned = [re.sub(r"<DOT>", ".", p).strip() for p in parts]
    return [p for p in cleaned if len(p) > 20][:200]


_INFO_MARKERS = re.compile(
    r"\d[\d,.]*\s?(?:%|percent|users|records|systems|servers|departments|hours|days|GB|TB|million|thousand|lakh|crore)?\b"
    r"|CVE-\d+-\d+|\b(?:should|must|will|detected|exposed|encrypted|restored|completed|issued|launched|affected)\b", re.IGNORECASE)


def _informativeness(sentence: str) -> int:
    score = 0
    score += len(_INFO_MARKERS.findall(sentence)) * 2
    if re.search(r"\d", sentence):
        score += 2
    score += min(3, sum(1 for w in sentence.split() if w[0].isupper()))  # named entities
    return score


def _parse_context(user_prompt: str) -> dict[str, str]:
    blocks = {}
    matches = list(re.finditer(r"^---([A-Z_]+)---\s*$", user_prompt, flags=re.MULTILINE))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(user_prompt)
        blocks[m.group(1)] = user_prompt[m.end():end].strip()
    return blocks


def _load_json(block: str, default):
    try:
        return json.loads(block)
    except Exception:
        return default


def _detect_domain(text_lower: str) -> str:
    scores = {d: sum(text_lower.count(k) for k in kws) for d, kws in DOMAIN_KEYWORDS.items()}
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] > 0 else "general"


def _detect_intent(text_lower: str) -> str:
    scores = {i: sum(text_lower.count(k) for k in kws) for i, kws in INTENT_KEYWORDS.items()}
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] > 0 else "inform"


def _extract_dates(text: str) -> list[tuple[str, tuple[int, int, int]]]:
    found = []
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b", text, re.IGNORECASE):
        found.append((m.group(0), (int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))))
    for m in re.finditer(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", text, re.IGNORECASE):
        found.append((m.group(0), (int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))))
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        found.append((m.group(0), (int(m.group(1)), int(m.group(2)), int(m.group(3)))))
    return found


def _make_entities(text: str) -> list[dict]:
    entities: dict[str, dict] = {}
    for etype, pattern in ENTITY_TYPES.items():
        for m in re.finditer(pattern, text):
            name = (m.group(1) or m.group(0)).strip().rstrip(".,;")
            if 2 < len(name) < 70 and name.lower() not in {"the", "this", "that"}:
                entities.setdefault(name, {"name": name, "type": etype, "description": ""})
    return list(entities.values())[:24]


# ---------------------------------------------------------------- analysis

def run_analyzer(text: str, source_title: str) -> dict:
    # strip structural artifacts that must not leak into facts
    text = re.sub(r"###\s*SOURCE:.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[Page \d+\]", " ", text)
    sentences = _split_sentences(text)
    lower = text.lower()
    domain = _detect_domain(lower)
    intent = _detect_intent(lower)

    key_facts, statistics, risks, recommendations, quotes = [], [], [], [], []
    for i, s in enumerate(sentences):
        if re.search(r"\"(.+?)\"", s) and len(quotes) < 6:
            quotes.append(re.search(r"\"(.+?)\"", s).group(1))
        if re.search(r"\d", s) and len(key_facts) < 18:
            key_facts.append({"text": s, "source_refs": [], "_score": _informativeness(s)})
            stats = [m.group(0).strip() for m in STAT_RE.finditer(s) if re.search(r"\d", m.group(0))]
            for st in stats[:2]:
                if len(statistics) < 12:
                    statistics.append(f"{st} — {s[:90]}{'â€¦' if len(s) > 90 else ''}")
        if any(w in s.lower() for w in THREAT_WORDS) and len(risks) < 8:
            risks.append(s)
        if any(w in s.lower() for w in RECO_WORDS) and len(recommendations) < 8:
            recommendations.append(s)
    # most informative facts first (numbers, entities, outcomes)
    key_facts.sort(key=lambda f: -f.pop("_score", 0))

    timeline = []
    for match_text, (y, mo, d) in _extract_dates(text):
        idx = lower.find(match_text.lower())
        context = text[max(0, idx - 130): idx + 130]
        sent = next((s for s in _split_sentences(context) if match_text.lower() in s.lower()), context.strip())
        timeline.append({"date": f"{y:04d}-{mo:02d}-{d:02d}", "label": match_text, "event": sent[:220]})
    timeline.sort(key=lambda t: t["date"])
    # dedupe by date
    seen, uniq = set(), []
    for t in timeline:
        if t["date"] not in seen:
            seen.add(t["date"])
            uniq.append(t)
    timeline = uniq[:12]

    recommended = ["executive_summary", "advisory", "presentation", "infographic"]
    if intent in ("awareness", "promote"):
        recommended = ["executive_summary", "linkedin", "presentation", "infographic"]
    if domain == "cybersecurity":
        recommended = ["advisory", "executive_summary", "presentation", "infographic"]

    total = len(sentences)
    confidence = min(0.95, 0.45 + 0.02 * min(total, 25) + 0.01 * len(statistics))

    summary_text = " ".join(sentences[:3]) if sentences else text[:300]

    return {
        "domain": domain,
        "intent": intent,
        "summary": summary_text,
        "audience": AUDIENCE_LABELS.get("general_public", ""),
        "communication_objective": intent,
        "entities": _make_entities(text),
        "key_facts": key_facts,
        "statistics": statistics,
        "timeline": timeline,
        "risks": risks,
        "recommendations": recommendations,
        "important_quotes": quotes,
        "source_references": [],
        "conflicts": [],
        "recommended_outputs": recommended,
        "confidence": round(confidence, 2),
        "_source_title": source_title,
    }


# ---------------------------------------------------------------- helpers

def _facts_block(bp: dict, limit: int = 8) -> list[str]:
    facts = [f.get("text", "") for f in bp.get("key_facts", []) if f.get("text")]
    return facts[:limit]


def _context_lines(bp: dict) -> dict:
    return {
        "title_hint": bp.get("summary", "")[:120],
        "facts": _facts_block(bp),
        "stats": bp.get("statistics", [])[:6],
        "timeline": bp.get("timeline", [])[:8],
        "risks": bp.get("risks", [])[:5],
        "recs": bp.get("recommendations", [])[:5],
        "entities": [e.get("name", "") for e in bp.get("entities", [])][:10],
        "domain": bp.get("domain", "general"),
        "intent": bp.get("intent", "inform"),
    }


def _tone_wrap(text: str, config: dict) -> str:
    tone = config.get("tone", "professional")
    aud = AUDIENCE_LABELS.get(config.get("audience", "general_public"), "stakeholders")
    if tone == "urgent":
        return f"URGENT — Attention required: {text}"
    if tone == "educational":
        return f"To help {aud} understand: {text}"
    return text


def _impact(ctx: dict, facts: list[str] | None = None) -> str:
    risks = ctx.get("risks", [])
    numbers = [f for f in (facts or []) if re.search(r"\d", f)]
    parts: list[str] = []
    if numbers:
        parts.append(f"What is at stake, concretely: {numbers[0][:180]}")
    if risks:
        parts.append(f"Primary risk: {risks[0][:180]}")
        if len(risks) > 1:
            parts.append(f"Secondary exposure: {risks[1][:160]}")
    if not parts:
        return "Business and operational impact appears limited based on the source material; monitor for further developments."
    parts.append("Unaddressed, these factors compound — operational continuity, compliance posture and stakeholder confidence are the areas most exposed.")
    return " ".join(parts)


def _depth(config: dict) -> int:
    return {"brief": 3, "moderate": 5, "detailed": 7, "highly_detailed": 9}.get(config.get("detail", "moderate"), 5)


# ---------------------------------------------------------------- generators

def run_generate(task: str, bp: dict, config: dict, evidence: list[str], blueprint_extra: dict | None = None) -> dict:
    ctx = _context_lines(bp)
    facts = ctx["facts"] or [bp.get("summary", "Source summary unavailable.")]
    aud = AUDIENCE_LABELS.get(config.get("audience", "general_public"), "stakeholders")
    lang = config.get("language", "English")
    title_hint = ctx["title_hint"] or "Source Material"
    domain_label = ctx["domain"].replace("_", " ").title() if ctx["domain"] != "general" else "General"

    lang_note = None
    if lang != "English":
        lang_note = (f"Offline engine: headings localized to {lang}; body text remains English. "
                     f"Configure a funded live LLM provider for fully native {lang} generation.")

    if task == "executive_summary":
        n = _depth(config)
        aud = AUDIENCE_LABELS.get(config.get("audience", "general_public"), "stakeholders")
        top_risk = ctx["risks"][0] if ctx["risks"] else ""
        sections = [
            {"heading": _t(config, "Executive Overview"), "body": _tone_wrap(
                f"Prepared for {aud}. {bp.get('summary', '')} The material warrants attention: "
                f"{len(ctx['facts'])} substantive findings were identified during analysis.", config)},
            {"heading": _t(config, "Key Findings"), "body": "\n".join(f"- {f}" for f in facts[:n])},
            {"heading": _t(config, "Important Statistics"), "body": "\n".join(f"- {s}" for s in ctx["stats"][:4]) or "No quantitative statistics were detected in the source."},
            {"heading": _t(config, "Risks"), "body": (
                ("The most significant exposure identified: " + top_risk[:220] + "\n\n" if top_risk else "")
                + "\n".join(f"- {r}" for r in ctx["risks"][:n])
            ) or "No explicit risks were identified in the source."},
            {"heading": _t(config, "Business / Operational Impact"), "body": _impact(ctx, facts)},
            {"heading": _t(config, "Recommendations"), "body": (
                "Priority actions, in order:\n" + "\n".join(f"- {r}" for r in ctx["recs"][:n])
            ) or "No explicit recommendations were found; further review is advised."},
            {"heading": _t(config, "Conclusion"), "body": (
                f"The {domain_label.lower()} situation described in the source is {('material and time-sensitive' if ctx['intent'] == 'alert' else 'relevant')} "
                f"for {aud}. Acting on the {len(ctx['recs']) or 'stated'} recommendations above — beginning with "
                f"'{(ctx['recs'][0][:120] if ctx['recs'] else 'a structured review of the source')}â€¦' — "
                f"addresses the primary exposures. Underlying analysis confidence: {int((bp.get('confidence', 0.7)) * 100)}%."
            )},
        ]
        return {"title": f"Executive Summary: {title_hint}", "sections": sections,
                "claims": facts[:n], "sources": bp.get("source_references", []), "language_note": lang_note}

    if task == "advisory":
        sev = "HIGH" if ctx["intent"] == "alert" or any("critical" in r.lower() for r in ctx["risks"]) else "MEDIUM"
        return {
            "advisory_title": f"Advisory: {title_hint}",
            "severity": sev,
            "summary": bp.get("summary", ""),
            "situation_overview": " ".join(facts[:3]),
            "affected_entities": [{"name": e, "type": "detected"} for e in ctx["entities"][:8]],
            "indicators": [s for s in ctx["stats"]] or ["Review the source document for technical indicators."],
            "risk": "\n".join(f"- {r}" for r in ctx["risks"]) or "Potential operational and reputational risk based on the reported situation.",
            "recommended_actions": [r for r in ctx["recs"]] or ["Review the full source document and apply organizational policy."],
            "mitigation": "Apply standard protective measures: restrict exposure, monitor affected assets, and follow the recommended actions above.",
            "references": [{"source_title": r.get("source_title", ""), "page": r.get("page", 0)} for r in bp.get("source_references", [])[:10]],
            "language_note": lang_note,
        }

    if task == "linkedin":
        hook = _tone_wrap(f"{title_hint}", config)
        variant_count = max(1, int(config.get("variants", 1)))
        variants = []
        for v in range(variant_count):
            lead = facts[v % max(len(facts), 1)] if facts else title_hint
            variants.append({
                "variant": v + 1,
                "hook": hook,
                "main_message": lead,
                "key_insights": facts[:4],
                "body": (
                    f"{lead}\n\n"
                    + "\n".join(f"â€¢ {f}" for f in facts[1:4])
                    + f"\n\nWhat does this mean for {aud}? The full breakdown is in our advisory."
                ),
                "cta": "Follow for updates and share your perspective.",
                "hashtags": ["#Prism", f"#{ctx['domain'].title()}", "#Insights", "#Leadership"],
            })
        return {"variants": variants, "language_note": lang_note}

    if task == "x_thread":
        posts = []
        posts.append(f"{_tone_wrap(title_hint, config)} A short thread. ðŸ§µ" if config.get("tone") == "conversational" else f"{_tone_wrap(title_hint, config)}")
        for f in facts[:5]:
            snippet = f if len(f) <= 270 else f[:267] + "â€¦"
            posts.append(snippet)
        posts.append(f"Bottom line: {ctx['recs'][0] if ctx['recs'] else 'Stay informed and review the full report.'}")
        posts = [p[:280] for p in posts]
        return {"mode": "thread", "posts": posts, "single_post": posts[0], "language_note": lang_note}

    if task == "presentation":
        slide_count = int(config.get("slide_count", 6))
        slides = [{"slide_number": 1, "title": title_hint, "content": bp.get("summary", ""),
                   "visual_recommendation": "Title slide with domain icon and minimal text",
                   "speaker_notes": f"Introduce the source and why it matters to {aud}."}]
        body_facts = facts[: max(1, slide_count - 3)]
        for i, f in enumerate(body_facts):
            slides.append({"slide_number": i + 2, "title": f"{_t(config, 'Finding')} {i + 1}",
                           "content": f, "visual_recommendation": "Supporting stat or diagram",
                           "speaker_notes": "Explain context and implication."})
        if ctx["timeline"]:
            tl = ctx["timeline"][:4]
            slides.append({"slide_number": len(slides) + 1, "title": _t(config, "Timeline of Events"),
                           "content": "\n".join(f"{t['date']}: {t['event'][:100]}" for t in tl),
                           "visual_recommendation": "Horizontal timeline", "speaker_notes": "Walk through chronology."})
        slides.append({"slide_number": len(slides) + 1, "title": _t(config, "Recommendations & Next Steps"),
                       "content": "\n".join(f"- {r}" for r in ctx["recs"][:4]) or "Review and act on findings.",
                       "visual_recommendation": "Checklist graphic", "speaker_notes": "Close with clear actions."})
        return {"deck_title": title_hint, "slide_count": len(slides), "slides": slides[:slide_count + 2], "language_note": lang_note}

    if task == "infographic":
        return {
            "title": title_hint,
            "main_message": facts[0] if facts else bp.get("summary", ""),
            "key_statistics": [{"value": s.split(" — ")[0], "label": s.split(" — ")[-1][:80]} for s in ctx["stats"][:5]],
            "supporting_facts": facts[1:5],
            "timeline": ctx["timeline"],
            "visual_hierarchy": ["Title (top, 10% height)", "Main message (banner)", "Statistics row (cards)", "Timeline (horizontal)", "CTA (bottom)"],
            "section_layout": {"columns": 1, "top_banner": "title + main message", "middle": "stat cards", "lower": "timeline", "footer": "CTA"},
            "cta": "Review the full advisory and share responsibly.",
            "language_note": lang_note,
        }

    if task == "video_package":
        scenes = []
        narration_facts = facts[:6]
        durations = [12, 20, 20, 20, 20, 16, 15]
        total = 0
        for i, f in enumerate(narration_facts):
            dur = durations[i % len(durations)]
            total += dur
            scenes.append({
                "scene_number": i + 1, "duration_seconds": dur,
                "visual_description": f"Supporting visual for: {f[:80]}",
                "narration": f, "on_screen_text": f[:60],
                "subtitle": f, "transition": "crossfade" if i else "fade-in",
                "visual_recommendation": "motion graphic / footage overlay",
            })
        script = " ".join(s["narration"] for s in scenes)
        return {
            "storyboard_title": title_hint,
            "scenes": scenes or [{"scene_number": 1, "duration_seconds": 15, "visual_description": "Title card", "narration": bp.get("summary", ""), "on_screen_text": title_hint, "subtitle": bp.get("summary", ""), "transition": "fade-in", "visual_recommendation": "title card"}],
            "narration_script": script,
            "subtitle_text": "\n".join(s["subtitle"] for s in scenes),
            "total_estimated_duration_seconds": total or 15,
            "srt_ready": True,
            "language_note": lang_note,
        }

    return {}


# ---------------------------------------------------------------- validation

def run_validate(output_text: str, evidence_chunks: list[dict]) -> dict:
    """Compare claims in the generated text against retrieved evidence chunks.

    Uses lexical overlap scoring (deterministic, offline). Each claim gets
    VERIFIED / PARTIALLY_SUPPORTED / UNSUPPORTED plus matching evidence refs.
    """
    from app.providers.embeddings import get_embedding_provider

    claims = []
    for s in _split_sentences(output_text):
        if len(s) > 25 and (re.search(r"\d", s) or len(s.split()) > 8):
            claims.append(s)
    claims = claims[:40]

    provider = get_embedding_provider()
    results = []
    chunk_texts = [c["text"] for c in evidence_chunks] or [""]
    chunk_vecs = provider.embed(chunk_texts)

    for claim in claims:
        cv = provider.embed([claim])[0]
        best, best_score = None, 0.0
        for idx, vec in enumerate(chunk_vecs):
            denom = (float(np.linalg.norm(cv)) * float(np.linalg.norm(vec))) or 1e-9
            score = float(np.dot(cv, vec) / denom)
            if score > best_score:
                best, best_score = evidence_chunks[idx], score
        if best_score >= 0.30:
            status = "VERIFIED"
        elif best_score >= 0.14:
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "UNSUPPORTED"
        refs = []
        if best is not None and best_score >= 0.14:
            refs.append({"source_id": best.get("source_id", ""), "source_title": best.get("source_title", ""),
                         "page": best.get("page", 0), "section": best.get("section", ""),
                         "paragraph": best.get("paragraph", 0), "chunk_index": best.get("chunk_index", 0),
                         "quote": best["text"][:300]})
        results.append({"claim": claim, "status": status, "confidence": round(min(0.99, best_score * 1.6), 2), "evidence": refs})

    v = sum(1 for r in results if r["status"] == "VERIFIED")
    p = sum(1 for r in results if r["status"] == "PARTIALLY_SUPPORTED")
    u = sum(1 for r in results if r["status"] == "UNSUPPORTED")
    return {"claims": results, "summary": {"verified": v, "partially_supported": p, "unsupported": u, "total": len(results)}}


def run_quality(output_content: dict, bp: dict, validation_summary: dict | None) -> dict:
    facts = [f.get("text", "") for f in bp.get("key_facts", [])]
    text_all = json.dumps(output_content).lower()
    fact_hits = sum(1 for f in facts if f[:40].lower() in text_all)
    fidelity = min(0.99, 0.55 + 0.3 * (fact_hits / max(len(facts), 1)) + 0.1)
    if validation_summary and validation_summary.get("total"):
        acc = (validation_summary["verified"] + 0.5 * validation_summary["partially_supported"]) / validation_summary["total"]
        accuracy = max(0.4, min(0.99, acc))
    else:
        accuracy = fidelity
    completeness = min(0.99, 0.5 + len(text_all) / 20000 + 0.2)
    readability = min(0.99, 0.75 + (0.15 if len(text_all) < 6000 else 0.05))
    scores = {
        "accuracy": round(accuracy * 100), "source_fidelity": round(fidelity * 100),
        "relevance": round(min(0.99, fidelity * 0.95 + 0.05) * 100),
        "readability": round(readability * 100),
        "audience_fit": round(min(0.99, 0.78 + 0.12) * 100),
        "completeness": round(completeness * 100),
    }
    scores["overall"] = round(sum(v for k, v in scores.items()) / len(scores))
    return scores


# ---------------------------------------------------------------- editing

def run_edit(action: str, content: dict, section: str | None, tone: str | None,
             audience: str | None, instruction: str, bp: dict, config: dict) -> dict:
    new_content = json.loads(json.dumps(content))
    aud = AUDIENCE_LABELS.get(audience or config.get("audience", "general_public"), "stakeholders")

    def edit_text_block(text: str) -> str:
        sentences = _split_sentences(text) or [text]
        if action == "shorten":
            return " ".join(sentences[: max(1, len(sentences) // 2)])
        if action == "expand":
            extra = _facts_block(bp, 3)
            return text + "\n\n" + "\n".join(f"- {e}" for e in extra)
        if action == "change_tone" and tone:
            return _tone_wrap(text, {**config, "tone": tone})
        if action == "change_audience":
            return f"Prepared for {aud}: {text}"
        if action == "rewrite_section":
            facts = _facts_block(bp, 2)
            return " ".join(facts) if facts else text
        return text

    if "sections" in new_content and section:
        for s in new_content["sections"]:
            if s.get("heading") == section:
                s["body"] = edit_text_block(s.get("body", ""))
                return new_content
    if "sections" in new_content:
        for s in new_content["sections"]:
            s["body"] = edit_text_block(s.get("body", ""))
        return new_content
    # generic: apply to string leaves
    def walk(obj):
        if isinstance(obj, dict):
            return {k: walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [walk(v) for v in obj]
        if isinstance(obj, str) and len(obj) > 40:
            return edit_text_block(obj)
        return obj
    return walk(new_content)


# ---------------------------------------------------------------- dispatcher

def offline_generate(system_prompt: str, user_prompt: str) -> dict:
    """Route a prompt pair to the right heuristic engine based on TASK= marker."""
    blocks = _parse_context(user_prompt)
    m = re.search(r"TASK=([a-z_:]+)", system_prompt)
    task = m.group(1) if m else ""

    if task in ("analyzer", "code_analyzer"):
        text = blocks.get("SOURCE", "") or blocks.get("EVIDENCE", "") or user_prompt
        title_m = re.search(r"### (?:SOURCE|CODE): (.+?) \(", text)
        result = run_analyzer(text, title_m.group(1) if title_m else "Source")
        if task == "code_analyzer":
            # code-aware framing for the offline fallback
            lang_m = re.search(r"language=([a-z+#]+)", text)
            lang = lang_m.group(1) if lang_m else "unknown"
            lines = text.count("\n") + 1
            funcs = len(re.findall(r"(?:def |function |class |func |public |private )\w+", text))
            imports = re.findall(r"(?:import|from|#include|using)\s+[\w.<>]+", text)[:12]
            result["domain"] = "software"
            result["intent"] = "report"
            result["summary"] = (
                f"A {lang} source file of approximately {lines} lines containing {funcs} "
                f"functions, classes or methods. "
                + ("It imports: " + ", ".join(imports[:6]) + ". " if imports else "")
                + "Configure a live LLM provider for a full functional description of this code."
            )
            result["statistics"] = [f"{lines} lines", f"{funcs} functions/classes"]
            result["entities"] = [{"name": imp.split()[-1], "type": "Technology", "description": "import"} for imp in imports[:10]]
        return result

    if task.startswith("generate:"):
        bp = _load_json(blocks.get("BLUEPRINT", "{}"), {})
        cfg = _load_json(blocks.get("CONFIG", "{}"), {})
        evidence = [e for e in re.findall(r"\[.*?\]\n(.+)", blocks.get("EVIDENCE", ""))]
        return run_generate(task.split(":", 1)[1], bp, cfg, evidence)

    if task == "validator":
        out = _load_json(blocks.get("OUTPUT", "{}"), {})
        evidence_chunks = []
        for m2 in re.finditer(r"\[(.+?) \| page (\d+) \| para (\d+)\]\n(.+)", blocks.get("EVIDENCE", "")):
            evidence_chunks.append({"source_id": "", "source_title": m2.group(1), "page": int(m2.group(2)),
                                    "section": "", "paragraph": int(m2.group(3)), "chunk_index": 0,
                                    "text": m2.group(4)})
        if not evidence_chunks:
            evidence_chunks = [{"source_id": "", "source_title": "", "page": 0, "section": "",
                                "paragraph": 0, "chunk_index": 0, "text": blocks.get("EVIDENCE", "")[:1000]}]
        return run_validate(_flatten_output(out), evidence_chunks)

    if task == "quality":
        out = _load_json(blocks.get("OUTPUT", "{}"), {})
        bp = _load_json(blocks.get("BLUEPRINT", "{}"), {})
        val = _load_json(blocks.get("VALIDATION", "null"), None)
        return run_quality(out, bp, val if isinstance(val, dict) else None)

    if task == "editor":
        action_m = re.search(r"ACTION:\s*([a-z_]+)", user_prompt)
        section_m = re.search(r"SECTION:\s*(.+)", user_prompt)
        tone_m = re.search(r"TONE:\s*([a-z_]+)", user_prompt)
        aud_m = re.search(r"AUDIENCE:\s*([a-z_]+)", user_prompt)
        out = _load_json(blocks.get("OUTPUT", "{}"), {})
        bp = _load_json(blocks.get("BLUEPRINT", "{}"), {})
        cfg = _load_json(blocks.get("CONFIG", "{}"), {})
        return run_edit(action_m.group(1) if action_m else "rewrite_section", out,
                        section_m.group(1).strip() if section_m else None,
                        tone_m.group(1) if tone_m else None,
                        aud_m.group(1) if aud_m else None, "", bp, cfg)

    if task == "agent":
        question = blocks.get("QUESTION", "") or user_prompt[:200]
        evidence_chunks = []
        for m2 in re.finditer(r"\[(.+?) \| page (\d+) \| para (\d+)\]\n(.+)", blocks.get("EVIDENCE", "")):
            evidence_chunks.append({"source_id": "", "source_title": m2.group(1), "page": int(m2.group(2)),
                                    "section": "", "paragraph": int(m2.group(3)), "chunk_index": 0,
                                    "text": m2.group(4)})
        if not evidence_chunks:
            evidence_chunks = [{"source_id": "", "source_title": "", "page": 0, "section": "",
                                "paragraph": 0, "chunk_index": 0, "text": blocks.get("EVIDENCE", "")[:1000]}]
        return run_agent(question, evidence_chunks)

    return {}


def run_agent(question: str, evidence_chunks: list[dict]) -> dict:
    """Grounding assistant.

    Offline mode still FRAMES the answer: relevance-ranked evidence sentences
    are synthesized into a structured response (lead-in, framed points with
    citations, implication summary) instead of returning raw quotes. With a
    live LLM provider the same prompt yields fully fluent synthesis.
    """
    qv = _embed_provider().embed([question])[0]
    qnorm = float(np.linalg.norm(qv)) or 1e-9

    scored: list[tuple[float, str, dict]] = []
    for chunk in evidence_chunks:
        for sent in _split_sentences(chunk.get("text", "")):
            sv = _embed_provider().embed([sent])[0]
            denom = (qnorm * float(np.linalg.norm(sv))) or 1e-9
            scored.append((float(np.dot(qv, sv) / denom), sent, chunk))
    scored.sort(key=lambda x: -x[0])

    # Evidence was already relevance-ranked by retrieval — always answer from
    # the top matches. Absolute cutoffs reject generic questions ("What are
    # the key facts?") because hashed embeddings can score near or below zero
    # on low lexical overlap.
    relevant = scored
    if not relevant:
        if not evidence_chunks or not any(c.get("text", "").strip() for c in evidence_chunks):
            return {
                "answer": "This project has no processed source material yet. Add a source "
                          "(document, URL or text) first, then ask again.",
                "evidence": [],
            }
        return {
            "answer": "The retrieved source context does not cover this question. Add a source document "
                      "that discusses it, or ask about the facts already analyzed in this project.",
            "evidence": [],
        }

    # dedupe near-identical sentences, keep best per source paragraph
    seen_keys: set[str] = set()
    picked: list[tuple[float, str, dict]] = []
    for score, sent, chunk in relevant:
        key = _norm_key(sent)[:80]
        if key in seen_keys:
            continue
        seen_keys.add(key)
        picked.append((score, sent, chunk))
        if len(picked) >= 4:
            break

    used: dict[str, dict] = {}
    points: list[str] = []
    for score, sent, chunk in picked:
        title = (chunk.get("source_title") or "Source").strip()
        page = chunk.get("page") or 0
        clean = sent.strip().rstrip(".")
        points.append(f"{clean} — reported in {title}, page {page}.")
        used[f"{chunk.get('source_id')}:{chunk.get('paragraph')}"] = chunk

    lead = "Based on the analyzed source material, here is what the context establishes"
    if re.search(r"\brisk|threat|danger|impact\b", question, re.IGNORECASE):
        lead = "Regarding the risks and impact, the source material establishes the following"
    elif re.search(r"\bwhen|timeline|date|chronolog\b", question, re.IGNORECASE):
        lead = "The chronology described in the sources is as follows"
    elif re.search(r"\bwho|organisation|organization|entity\b", question, re.IGNORECASE):
        lead = "The entities involved, according to the sources, are the following"
    elif re.search(r"\bwhat should|recommend|action|mitigat\b", question, re.IGNORECASE):
        lead = "The sources support the following recommended actions"
    lead += ":"

    summary_line = f"In short, {'; '.join(p.split(' — reported')[0].strip('.').lower() for p in points[:2])}."

    answer = lead + "\n\n" + "\n".join(f"â€¢ {p}" for p in points) + "\n\n" + summary_line

    evidence = []
    for chunk in used.values():
        evidence.append({
            "source_id": chunk.get("source_id", ""),
            "source_title": chunk.get("source_title", ""),
            "page": chunk.get("page", 0),
            "paragraph": chunk.get("paragraph", 0),
            "quote": chunk.get("text", "")[:300],
        })
    return {"answer": answer, "evidence": evidence}


def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _embed_provider():
    from app.providers.embeddings import get_embedding_provider
    return get_embedding_provider()


def _flatten_output(content: dict) -> str:
    parts: list[str] = []

    def walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str):
            parts.append(obj)

    walk(content)
    return "\n".join(parts)


# ---------------------------------------------------------------- conflicts

def detect_conflicts(timelines_by_source: list[dict]) -> list[dict]:
    """Compare per-source timelines; same-ish dates with different events or
    same event labels with different dates are surfaced as conflicts."""
    conflicts = []
    by_label: dict[str, list] = {}
    for entry in timelines_by_source:
        for t in entry.get("timeline", []):
            by_label.setdefault(t.get("event", "")[:60].lower(), []).append({**t, "source": entry.get("source_title", "")})
    for label, items in by_label.items():
        dates = {i["date"] for i in items}
        if len(items) > 1 and len(dates) > 1:
            conflicts.append({"type": "date_conflict", "detail": label, "occurrences": items, "status": "requires_human_review"})
    return conflicts[:10]
