"""Source ingestion service — pluggable extractors per source type."""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import uuid

from abc import ABC, abstractmethod

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document as DocxDocument

from app.core.config import settings
from app.utils.errors import IngestionError

MAX_CHARS = 200_000

_TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def _find_tesseract() -> str | None:
    exe = shutil.which("tesseract")
    if exe:
        return exe
    for path in _TESSERACT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def _find_ffprobe() -> str | None:
    return shutil.which("ffprobe") or shutil.which("ffmpeg")


class BaseExtractor(ABC):
    source_type: str = "base"

    @abstractmethod
    def extract(self, data: bytes | str) -> tuple[str, dict]:
        """Return (raw_text, metadata)."""


class TextExtractor(BaseExtractor):
    source_type = "text"

    def extract(self, data: bytes | str) -> tuple[str, dict]:
        text = (data if isinstance(data, str) else data.decode("utf-8", errors="replace")).strip()
        if not text:
            raise IngestionError("The provided text is empty.")
        return text[:MAX_CHARS], {"char_count": len(text)}


class PdfExtractor(BaseExtractor):
    source_type = "pdf"

    def extract(self, data: bytes | str) -> tuple[str, dict]:
        try:
            reader = PdfReader(io.BytesIO(data))
            if len(reader.pages) == 0:
                raise IngestionError("The PDF contains no pages.")
            pages = []
            for i, page in enumerate(reader.pages):
                t = (page.extract_text() or "").strip()
                pages.append(t)
            full = "\n\n".join(f"[Page {i + 1}]\n{t}" for i, t in enumerate(pages) if t)
            if not full.strip():
                raise IngestionError("No readable text found (scanned images require OCR, coming soon).")
            return full[:MAX_CHARS], {"page_count": len(reader.pages)}
        except IngestionError:
            raise
        except Exception:
            raise IngestionError("The PDF appears to be corrupted or unreadable.")


class DocxExtractor(BaseExtractor):
    source_type = "docx"

    def extract(self, data: bytes | str) -> tuple[str, dict]:
        try:
            doc = DocxDocument(io.BytesIO(data))
            paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            if not paras:
                raise IngestionError("The DOCX document is empty.")
            return "\n\n".join(paras)[:MAX_CHARS], {"paragraph_count": len(paras)}
        except IngestionError:
            raise
        except Exception:
            raise IngestionError("The DOCX document appears to be corrupted.")


class TxtFileExtractor(TextExtractor):
    source_type = "txt"


class UrlExtractor(BaseExtractor):
    source_type = "url"

    def extract(self, data: bytes | str) -> tuple[str, dict]:
        url = str(data).strip()
        if not re.match(r"^https?://", url):
            raise IngestionError("URL must start with http:// or https://")
        try:
            resp = httpx.get(url, timeout=20, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (compatible; TransformAI/1.0)"})
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise IngestionError("The URL took too long to respond.")
        except httpx.HTTPStatusError:
            raise IngestionError(f"The URL returned an error (HTTP {resp.status_code}).")
        except httpx.HTTPError:
            raise IngestionError("The URL could not be reached.")
        ctype = resp.headers.get("content-type", "")
        if "html" not in ctype and "text" not in ctype and ctype:
            raise IngestionError("The URL does not point to a readable web page.")
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))
        if len(text) < 60:
            raise IngestionError("No meaningful content found at that URL.")
        return text[:MAX_CHARS], {"url": url, "title": title}


class ImageExtractor(BaseExtractor):
    """PNG/JPG/WebP ingestion via Tesseract OCR."""
    source_type = "image"

    def extract(self, data: bytes | str) -> tuple[str, dict]:
        if isinstance(data, str):
            raise IngestionError("Invalid image payload.")
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data))
            img.load()
            fmt = (img.format or "").lower()
            if fmt not in ("png", "jpeg", "jpg", "webp"):
                raise IngestionError("Unsupported image format. Use PNG, JPG or WebP.")
            # OCR accuracy: upscale small images, grayscale, autocontrast
            from PIL import ImageOps, ImageFilter
            width, height = img.size
            if img.mode not in ("L", "RGB"):
                img = img.convert("RGB")
            if width < 1000:
                scale = 1000 / width
                img = img.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
            img = ImageOps.autocontrast(ImageOps.grayscale(img))
            img = img.filter(ImageFilter.SHARPEN)
        except IngestionError:
            raise
        except Exception:
            raise IngestionError("The image file appears to be corrupted or unreadable.")

        tesseract = _find_tesseract()
        if not tesseract:
            raise IngestionError("OCR engine is not available on the server. Install Tesseract to enable image ingestion.")

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            img.save(tmp_path, format="PNG")
        try:
            proc = subprocess.run(
                [tesseract, tmp_path, "stdout", "--psm", "3", "-l", "eng"],
                capture_output=True, timeout=120,
            )
            text = (proc.stdout or b"").decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            raise IngestionError("OCR took too long on this image. Try a smaller or clearer image.")
        except Exception:
            raise IngestionError("OCR failed on this image.")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) < 20:
            raise IngestionError("No readable text found in the image. Clearer or higher-resolution images work better.")
        return text[:MAX_CHARS], {
            "ocr": True,
            "image_format": fmt,
            "dimensions": f"{width}x{height}",
            "char_count": len(text),
        }


class VideoExtractor(BaseExtractor):
    """MP4/MOV/WEBM/AVI/MKV ingestion: ffprobe metadata + sampled frame OCR.

    Text visible in frames (slides, titles, lower-thirds, charts) is
    extracted via OCR at sampled timestamps; frame descriptions are recorded
    as contextual information alongside the transcript-like text layer.
    """
    source_type = "video"

    FRAME_COUNT = 8  # frames sampled across the video

    def extract(self, data: bytes | str) -> tuple[str, dict]:
        if isinstance(data, str):
            raise IngestionError("Invalid video payload.")
        ffprobe = _find_ffprobe()
        if not ffprobe or ffprobe.endswith("ffmpeg.exe"):
            ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            raise IngestionError("Video processing is not available on the server. Install FFmpeg to enable video ingestion.")

        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="tai_video_")
        video_path = os.path.join(tmp_dir, "input.bin")
        try:
            with open(video_path, "wb") as f:
                f.write(data)

            # metadata
            try:
                meta_proc = subprocess.run(
                    [ffprobe, "-v", "quiet", "-print_format", "json",
                     "-show_format", "-show_streams", video_path],
                    capture_output=True, timeout=60,
                )
                meta = json.loads(meta_proc.stdout or b"{}")
            except Exception:
                raise IngestionError("The video file appears to be corrupted or unreadable.")

            fmt_info = meta.get("format", {})
            duration = float(fmt_info.get("duration", 0) or 0)
            if duration <= 0:
                raise IngestionError("Could not read the video duration.")
            streams = meta.get("streams", [])
            vstream = next((s for s in streams if s.get("codec_type") == "video"), None)
            astream = next((s for s in streams if s.get("codec_type") == "audio"), None)
            width = vstream.get("width", 0) if vstream else 0
            height = vstream.get("height", 0) if vstream else 0
            has_audio = astream is not None

            tesseract = _find_tesseract()
            frame_texts: list[str] = []
            frames_dir = os.path.join(tmp_dir, "frames")
            os.makedirs(frames_dir, exist_ok=True)

            # sample frames at evenly spaced timestamps (skip first/last second)
            n = self.FRAME_COUNT
            start = min(1.0, duration * 0.05)
            span = max(duration - 2 * start, 0.1)
            timestamps = [start + span * i / (n - 1) for i in range(n)] if n > 1 else [duration / 2]

            ffmpeg = shutil.which("ffmpeg") or ffprobe
            for i, ts in enumerate(timestamps):
                frame_path = os.path.join(frames_dir, f"frame_{i:02d}.png")
                try:
                    subprocess.run(
                        [ffmpeg, "-y", "-v", "quiet", "-ss", f"{ts:.2f}", "-i", video_path,
                         "-frames:v", "1", "-vf", "scale=1200:-1", frame_path],
                        capture_output=True, timeout=60,
                    )
                except Exception:
                    continue
                if not os.path.exists(frame_path):
                    continue
                if tesseract:
                    try:
                        ocr = subprocess.run(
                            [tesseract, frame_path, "stdout", "--psm", "3", "-l", "eng"],
                            capture_output=True, timeout=60,
                        )
                        ftext = (ocr.stdout or b"").decode("utf-8", errors="replace")
                        ftext = re.sub(r"[ \t]+", " ", ftext)
                        ftext = re.sub(r"\n{2,}", "\n", ftext).strip()
                        if len(ftext) >= 12:
                            mm, ss = divmod(int(ts), 60)
                            frame_texts.append(f"[Frame at {mm:02d}:{ss:02d}]\n{ftext}")
                    except Exception:
                        continue

            parts = [f"Video metadata: duration {int(duration)}s, resolution {width}x{height}, "
                     f"audio {'present' if has_audio else 'absent'}."]
            if frame_texts:
                parts.append("Text extracted from sampled video frames (OCR):")
                parts.extend(frame_texts)
            else:
                parts.append("No readable on-screen text was found in the sampled frames; "
                             "the video content is described only by metadata. "
                             "Note: spoken audio transcription is not yet available.")
            text = "\n\n".join(parts)[:MAX_CHARS]

            return text, {
                "video_duration_seconds": int(duration),
                "video_resolution": f"{width}x{height}",
                "video_has_audio": has_audio,
                "frames_sampled": len(timestamps),
                "frames_with_text": len(frame_texts),
                "ocr": True,
            }
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


EXTRACTORS: dict[str, BaseExtractor] = {
    e.source_type: e for e in [
        TextExtractor(), PdfExtractor(), DocxExtractor(), TxtFileExtractor(),
        UrlExtractor(), ImageExtractor(), VideoExtractor(),
    ]
}


def register_extractor(ext: BaseExtractor) -> None:
    EXTRACTORS[ext.source_type] = ext


def get_extractor(source_type: str) -> BaseExtractor:
    ext = EXTRACTORS.get(source_type)
    if ext is None:
        raise IngestionError(f"Unsupported source type '{source_type}'.")
    return ext


IMAGE_EXTENSIONS = {"png": "image", "jpg": "image", "jpeg": "image", "webp": "image"}
VIDEO_EXTENSIONS = {"mp4": "video", "mov": "video", "webm": "video", "avi": "video", "mkv": "video"}
ALLOWED_UPLOAD_TYPES = {
    "pdf": "pdf",
    "docx": "docx",
    "txt": "txt",
    **IMAGE_EXTENSIONS,
    **VIDEO_EXTENSIONS,
}
MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_MB * 1024 * 1024


def validate_upload(filename: str, size: int, content_type: str) -> str:
    """Return the extractor source type for the upload, or raise. Enforces type + size."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    source_type = ALLOWED_UPLOAD_TYPES.get(ext)
    if not source_type:
        raise IngestionError(
            f"Unsupported file type '.{ext}'. Supported: PDF, DOCX, TXT, PNG, JPG, WebP, MP4, MOV, WebM."
        )
    if size > MAX_UPLOAD_BYTES:
        raise IngestionError(f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit.")
    return source_type
