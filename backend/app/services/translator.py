"""Content localization service.

Offline mode: translates generated content values (JSON keys stay English)
via a free translation endpoint so Hindi/Telugu outputs work without a paid
LLM. Live LLM mode: the model writes natively per the prompt LANGUAGE RULE
and this layer is skipped.

Failures degrade gracefully — untranslated content is returned with the
original text rather than blocking generation.
"""
from __future__ import annotations

import re

import httpx

_LANG_CODES = {"hindi": "hi", "telugu": "te"}
_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
_TIMEOUT = 15

_SKIP_KEYS = {"hashtags", "language_note", "mode", "srt_ready", "_quality", "variant", "slide_number", "scene_number"}

_CACHE: dict[tuple[str, str], str] = {}


def _split_for_translation(text: str, limit: int = 2600) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    buf = ""
    for piece in re.split(r"(?<=[.!?…\n])\s+", text):
        if len(buf) + len(piece) + 1 > limit and buf:
            parts.append(buf)
            buf = piece
        else:
            buf = f"{buf} {piece}".strip()
    if buf:
        parts.append(buf)
    return parts


_last_google_call = 0.0
_GOOGLE_MIN_INTERVAL = 0.25


def _throttle_google():
    global _last_google_call
    import time as _time
    now = _time.monotonic()
    wait = _last_google_call + _GOOGLE_MIN_INTERVAL - now
    if wait > 0:
        _time.sleep(wait)
    _last_google_call = _time.monotonic()


def _via_google(text: str, target: str) -> str | None:
    # deep-translator uses a Google endpoint that tolerates higher volume
    # than the raw gtx API; falls back to gtx with backoff if unavailable.
    for attempt in range(2):
        try:
            from deep_translator import GoogleTranslator
            _throttle_google()
            return GoogleTranslator(source="en", target=target).translate(text) or None
        except Exception:
            import time as _time
            _time.sleep(0.8 * (attempt + 1))
    params = {"client": "gtx", "sl": "en", "tl": target, "dt": "t", "q": text}
    for attempt in range(2):
        try:
            _throttle_google()
            resp = httpx.get(_ENDPOINT, params=params, timeout=_TIMEOUT,
                             headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"})
            if resp.status_code == 429:
                import time as _time
                _time.sleep(1.0 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            translated = "".join(seg[0] for seg in data[0] if seg and seg[0])
            return translated.strip() or None
        except Exception:
            return None
    return None


def _via_mymemory(text: str, target: str) -> str | None:
    for attempt in range(2):
        try:
            resp = httpx.get("https://api.mymemory.translated.net/get",
                             params={"q": text, "langpair": f"en|{target}"}, timeout=_TIMEOUT,
                             headers={"User-Agent": "TransformAI/1.0"})
            if resp.status_code == 429:
                import time as _time
                _time.sleep(0.6 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            if int(data.get("responseStatus", 500)) != 200:
                return None
            translated = (data.get("responseData") or {}).get("translatedText", "")
            if translated and "MYMEMORY WARNING" not in translated:
                return translated.strip()
            return None
        except Exception:
            return None
    return None


def _translate_chunk(text: str, target: str) -> str:
    key = (text, target)
    if key in _CACHE:
        return _CACHE[key]
    result = _via_google(text, target) or _via_mymemory(text, target) or text
    _CACHE[key] = result
    return result


def _unique_strings(obj) -> list[str]:
    """Collect distinct translatable strings, in deterministic order."""
    found: list[str] = []
    seen: set[str] = set()

    def walk(node, key=None):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, list):
            if key == "hashtags":
                return
            for v in node:
                walk(v, key)
        elif isinstance(node, str):
            if key in _SKIP_KEYS or len(node) < 2:
                return
            if node not in seen:
                seen.add(node)
                found.append(node)

    walk(obj)
    return found


def _remap(obj, mapping: dict[str, str]):
    if isinstance(obj, dict):
        return {k: _remap(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        if isinstance(obj, list) and not obj:
            return obj
        return [_remap(v, mapping) for v in obj]
    if isinstance(obj, str):
        return mapping.get(obj, obj)
    return obj


def localize_content(obj, target: str):
    """Translate all user-visible string values, preserving structure and keys.

    Batch strategy: collect unique strings, translate all chunks concurrently,
    then remap. Failures leave the original English text in place.
    """
    if not isinstance(obj, (dict, list, str)):
        return obj
    strings = _unique_strings(obj)
    if not strings:
        return obj

    all_chunks: set[str] = set()
    chunks_by_string: dict[str, list[str]] = {}
    for s in strings:
        parts = _split_for_translation(s)
        chunks_by_string[s] = parts
        for p in parts:
            if (p, target) not in _CACHE:
                all_chunks.add(p)

    # concurrent translation of uncached chunks
    todo = sorted(all_chunks)
    if todo:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda p: (p, _translate_chunk(p, target)), todo))
        for p, translated in results:
            _CACHE[(p, target)] = translated

    mapping = {s: " ".join(_CACHE.get((p, target), p) for p in parts)
               for s, parts in chunks_by_string.items()}
    return _remap(obj, mapping)


def detect_script_language(text: str) -> str | None:
    """Detect Hindi (Devanagari) or Telugu script in free-form input."""
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te"
    return None
