"""Export service: TXT, Markdown, DOCX, SRT. Returns (filename, bytes, media_type)."""
from __future__ import annotations

import io
import json
import re

from app.utils.errors import AppError


def _flatten(content: dict) -> str:
    lines: list[str] = []

    def emit(obj, depth=0, key=""):
        if isinstance(obj, dict):
            heading_keys = {"title", "advisory_title", "deck_title", "storyboard_title", "heading"}
            for k, v in obj.items():
                if k in heading_keys and isinstance(v, str):
                    lines.append(f"{'#' * min(depth + 1, 3)} {v}\n")
                elif isinstance(v, (dict, list)):
                    emit(v, depth + 1, k)
                elif isinstance(v, str) and v.strip():
                    label = k.replace("_", " ").title() if not k.startswith("#") else ""
                    lines.append(f"**{label}**\n{v}\n" if label and len(v) < 300 else f"{v}\n")
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, str):
                    lines.append(f"- {item}")
                else:
                    emit(item, depth, key)

    emit(content)
    return "\n".join(lines)


def _to_markdown(output_type: str, content: dict) -> str:
    title = content.get("title") or content.get("advisory_title") or content.get("deck_title") \
        or content.get("storyboard_title") or output_type.replace("_", " ").title()
    body = _flatten(content)
    return f"# {title}\n\n{body}"


def _to_docx(content: dict, output_type: str) -> bytes:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    title = content.get("title") or content.get("advisory_title") or content.get("deck_title") \
        or content.get("storyboard_title") or output_type.replace("_", " ").title()
    doc.add_heading(title, 0)

    def emit(obj, depth=1):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, dict):
                    if k not in ("config",):
                        emit(v, depth)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            doc.add_paragraph(item, style="List Bullet")
                        elif isinstance(item, dict):
                            head = item.get("heading") or item.get("title") or f"Scene {item.get('scene_number', '')}"
                            doc.add_heading(str(head), level=min(depth + 1, 3))
                            emit(item, depth + 1)
                elif isinstance(v, str) and v.strip():
                    if k in ("heading", "title") and depth > 0:
                        doc.add_heading(v, level=min(depth, 3))
                    elif k == "slide_number" or k == "variant" or k == "scene_number":
                        continue
                    else:
                        p = doc.add_paragraph()
                        run = p.add_run(v)
                        run.font.size = Pt(11)
        elif isinstance(obj, list):
            for item in obj:
                emit({"items": [item]} if isinstance(item, str) else item, depth)

    emit(content, 1)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _seconds_to_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _to_srt(content: dict) -> bytes:
    lines: list[str] = []
    idx = 1
    t = 0.0
    scenes = content.get("scenes", [])
    for scene in scenes:
        dur = float(scene.get("duration_seconds", 10) or 10)
        start, end = t, t + dur
        t = end
        text = (scene.get("subtitle") or scene.get("narration") or "").strip()
        if not text:
            continue
        lines.append(f"{idx}\n{_seconds_to_srt_time(start)} --> {_seconds_to_srt_time(end)}\n{text}\n")
        idx += 1
    if not lines:
        raise AppError("This output has no subtitle scenes to export as SRT.")
    return "\n".join(lines).encode("utf-8")


def _to_pptx(content: dict) -> bytes:
    """Render a presentation structure into a clean, enterprise-style PPTX deck."""
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE

    # Light theme — projector/print friendly, clean hierarchy
    INK = RGBColor(0x2E, 0x34, 0x40)
    MUTED = RGBColor(0x64, 0x6B, 0x7A)
    ACCENT = RGBColor(0x5B, 0x8D, 0xEF)
    ACCENT_SOFT = RGBColor(0xE4, 0xEC, 0xFC)
    LINE = RGBColor(0xDF, 0xE4, 0xEB)
    WHITE = RGBColor(0xFF, 0xFF, 0xFF)

    SLIDE_W = 13.333
    SLIDE_H = 7.5
    MARGIN = 0.75
    FONT = "DM Sans"

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    blank = prs.slide_layouts[6]

    def solid_rect(slide, left, top, width, height, color, rounded=False):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
            Inches(left), Inches(top), Inches(width), Inches(height))
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.line.fill.background()
        shape.shadow.inherit = False
        return shape

    def textbox(slide, left, top, width, height):
        box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        return box, tf

    def put(tf, text, size, color, bold=False, italic=False, align=PP_ALIGN.LEFT,
            space_after=0, first=False):
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        run = p.add_run()
        run.text = text
        f = run.font
        f.size = Pt(size)
        f.bold = bold
        f.italic = italic
        f.color.rgb = color
        f.name = FONT
        return p

    def footer(slide, page_no):
        solid_rect(slide, MARGIN, SLIDE_H - 0.62, SLIDE_W - 2 * MARGIN, 0.012, LINE)
        _, tf = textbox(slide, MARGIN, SLIDE_H - 0.5, 4, 0.3)
        put(tf, "Prism", 9, MUTED, first=True)
        _, tf = textbox(slide, SLIDE_W - MARGIN - 1.2, SLIDE_H - 0.5, 1.2, 0.3)
        put(tf, str(page_no), 9, MUTED, align=PP_ALIGN.RIGHT, first=True)

    def title_block(slide, title, page_no):
        chip = solid_rect(slide, MARGIN, 0.62, 0.14, 0.42, ACCENT, rounded=True)
        chip.adjustments[0] = 0.5
        _, tf = textbox(slide, MARGIN + 0.3, 0.55, SLIDE_W - 2 * MARGIN - 0.3, 1.0)
        put(tf, title, 27, INK, bold=True, first=True)
        footer(slide, page_no)

    def bullets(slide, items, top, left, width, height, size=15):
        box, tf = textbox(slide, left, top, width, height)
        first = True
        for item in items:
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.space_after = Pt(10)
            p.line_spacing = 1.12
            dot = p.add_run()
            dot.text = "â€¢  "
            dot.font.size = Pt(size)
            dot.font.bold = True
            dot.font.color.rgb = ACCENT
            dot.font.name = FONT
            run = p.add_run()
            run.text = item
            run.font.size = Pt(size)
            run.font.color.rgb = INK
            run.font.name = FONT

    deck_title = str(content.get("deck_title") or content.get("title") or "Presentation")
    slides = content.get("slides", [])

    # ---- Title slide ----
    slide = prs.slides.add_slide(blank)
    solid_rect(slide, 0, 0, SLIDE_W, SLIDE_H, WHITE)
    solid_rect(slide, 0, 0, SLIDE_W, 0.14, ACCENT)
    chip = solid_rect(slide, MARGIN, 2.05, 1.75, 0.42, ACCENT_SOFT, rounded=True)
    ctf = chip.text_frame
    ctf.word_wrap = False
    cp = ctf.paragraphs[0]
    cp.alignment = PP_ALIGN.CENTER
    cr = cp.add_run()
    cr.text = "Prism"
    cr.font.size = Pt(11)
    cr.font.bold = True
    cr.font.color.rgb = ACCENT
    cr.font.name = FONT
    _, tf = textbox(slide, MARGIN, 2.75, SLIDE_W - 2 * MARGIN, 2.2)
    put(tf, deck_title, 42, INK, bold=True, first=True)
    _, tf = textbox(slide, MARGIN, 5.1, SLIDE_W - 2 * MARGIN, 0.6)
    put(tf, "Generated by Prism — grounded in your source material", 14, MUTED, first=True)

    # ---- Content slides ----
    for i, s in enumerate(slides):
        slide = prs.slides.add_slide(blank)
        solid_rect(slide, 0, 0, SLIDE_W, SLIDE_H, WHITE)
        title = str(s.get("title") or f"Slide {i + 1}")
        body = str(s.get("content") or "")
        items = [ln.strip().lstrip("-â€¢").strip() for ln in body.split("\n") if ln.strip()]
        if not items:
            items = [""]
        title_block(slide, title, i + 1)

        size = 15 if len(items) <= 6 else 13
        if len(items) > 8:
            half = (len(items) + 1) // 2
            bullets(slide, items[:half], 2.0, MARGIN, 5.7, 4.4, size=size)
            bullets(slide, items[half:], 2.0, MARGIN + 6.0, 5.7, 4.4, size=size)
        else:
            bullets(slide, items, 2.0, MARGIN, SLIDE_W - 2 * MARGIN, 3.9, size=size)

        visual = str(s.get("visual_recommendation") or "").strip()
        if visual:
            vis_y = SLIDE_H - 1.25
            tag = solid_rect(slide, MARGIN, vis_y, 0.95, 0.34, ACCENT_SOFT, rounded=True)
            vtf = tag.text_frame
            vp = vtf.paragraphs[0]
            vp.alignment = PP_ALIGN.CENTER
            vr = vp.add_run()
            vr.text = "VISUAL"
            vr.font.size = Pt(9)
            vr.font.bold = True
            vr.font.color.rgb = ACCENT
            vr.font.name = FONT
            _, tf = textbox(slide, MARGIN + 1.1, vis_y + 0.03, SLIDE_W - 2 * MARGIN - 1.1, 0.4)
            put(tf, visual, 11, MUTED, italic=True, first=True)

        notes = str(s.get("speaker_notes") or "")
        if notes:
            slide.notes_slide.notes_text_frame.text = notes

    # ---- Closing slide ----
    slide = prs.slides.add_slide(blank)
    solid_rect(slide, 0, 0, SLIDE_W, SLIDE_H, WHITE)
    solid_rect(slide, 0, SLIDE_H - 0.14, SLIDE_W, 0.14, ACCENT)
    _, tf = textbox(slide, MARGIN, 3.0, SLIDE_W - 2 * MARGIN, 1.2)
    put(tf, "Thank you", 40, INK, bold=True, first=True)
    _, tf = textbox(slide, MARGIN, 4.2, SLIDE_W - 2 * MARGIN, 0.6)
    put(tf, deck_title, 14, MUTED, first=True)
    footer(slide, len(slides) + 2)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _pdf_story_blocks(content: dict) -> list:
    """Build a PDF story from structured output content using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    ACCENT = HexColor("#5B8DEF")
    INK = HexColor("#2E3440")
    MUTED = HexColor("#646B7A")

    title_style = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=20, textColor=INK, spaceAfter=2 * mm)
    h_style = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=13, textColor=ACCENT, spaceBefore=4 * mm, spaceAfter=1.5 * mm)
    body_style = ParagraphStyle("B", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK)
    muted_style = ParagraphStyle("M", fontName="Helvetica", fontSize=9, leading=13, textColor=MUTED)

    story: list = []
    title = content.get("title") or content.get("advisory_title") or content.get("deck_title") \
        or content.get("storyboard_title") or "Prism Output"
    story.append(Paragraph(str(title), title_style))

    def emit(key: str, value, depth: int = 0):
        if key in ("_quality", "language_note", "srt_ready"):
            return
        label = key.replace("_", " ").title()
        if isinstance(value, dict):
            story.append(Paragraph(label, h_style))
            for k, v in value.items():
                emit(k, v, depth + 1)
        elif isinstance(value, list):
            story.append(Paragraph(label, h_style))
            if value and all(isinstance(v, str) for v in value):
                for v in value:
                    story.append(Paragraph(f"• {v}", body_style))
            else:
                for item in value:
                    if isinstance(item, dict):
                        rows = [[Paragraph(str(kk).replace('_', ' ').title(), muted_style),
                                 Paragraph(str(vv), body_style)]
                                for kk, vv in item.items() if vv and kk not in ("source_id", "chunk_index")
                                and not isinstance(vv, (dict, list)) and str(vv).strip()]
                        if rows:
                            t = Table(rows, colWidths=[38 * mm, 120 * mm])
                            t.setStyle(TableStyle([
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                                ("TOPPADDING", (0, 0), (-1, -1), 3),
                                ("LINEBELOW", (0, 0), (-1, -2), 0.25, HexColor("#DFE4EB")),
                            ]))
                            story.append(t)
                            story.append(Spacer(1, 2 * mm))
                    else:
                        story.append(Paragraph(str(item), body_style))
        elif isinstance(value, str) and value.strip():
            story.append(Paragraph(label, h_style))
            for para in value.split("\n"):
                if para.strip():
                    story.append(Paragraph(para.strip(), body_style))

    for k, v in content.items():
        emit(k, v)

    return story


def _to_html(content: dict, output_type: str) -> bytes:
    """Self-contained styled HTML (print-to-PDF friendly, email-friendly)."""
    import html as _html

    title = content.get("title") or content.get("advisory_title") or content.get("deck_title") \
        or content.get("storyboard_title") or output_type.replace("_", " ").title()
    body: list[str] = []

    def emit(key, value, depth=0):
        esc = lambda s: _html.escape(str(s))
        label = esc(key.replace("_", " ").title())
        if key in ("_quality", "language_note", "srt_ready"):
            return
        if isinstance(value, dict):
            if value:
                body.append(f"<h3>{label}</h3>")
                for k, v in value.items():
                    emit(k, v, depth + 1)
        elif isinstance(value, list):
            if not value:
                return
            body.append(f"<h3>{label}</h3>")
            if all(isinstance(v, str) for v in value):
                body.append("<ul>" + "".join(f"<li>{esc(v)}</li>" for v in value) + "</ul>")
            else:
                for item in value:
                    if isinstance(item, dict):
                        head = item.get("heading") or item.get("title") or item.get("name") or ""
                        rows = "".join(
                            f"<tr><td>{esc(kk.replace('_',' ').title())}</td><td>{esc(vv)}</td></tr>"
                            for kk, vv in item.items()
                            if vv and kk not in ("source_id", "chunk_index")
                            and not isinstance(vv, (dict, list)) and str(vv).strip())
                        if head:
                            body.append(f"<h4>{esc(head)}</h4>")
                        if rows:
                            body.append(f"<table>{rows}</table>")
                    else:
                        body.append(f"<p>{esc(item)}</p>")
        elif isinstance(value, str) and value.strip():
            body.append(f"<h3>{label}</h3>")
            for para in value.split("\n"):
                if para.strip():
                    body.append(f"<p>{esc(para.strip())}</p>")

    for k, v in content.items():
        emit(k, v)

    doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{_html.escape(str(title))}</title>
<style>
  body {{ font-family: 'DM Sans', 'Segoe UI', sans-serif; color: #111827; max-width: 800px;
         margin: 40px auto; padding: 0 24px; line-height: 1.65; }}
  h1 {{ font-size: 26px; border-bottom: 3px solid #5B8DEF; padding-bottom: 10px; }}
  h3 {{ color: #5B8DEF; font-size: 15px; text-transform: uppercase; letter-spacing: 0.04em;
       margin: 22px 0 6px; }}
  h4 {{ margin: 14px 0 4px; }}
  p {{ margin: 6px 0; }}
  ul {{ padding-left: 20px; }}
  li {{ margin: 4px 0; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
  td {{ border-bottom: 1px solid #E5E7EB; padding: 6px 8px; vertical-align: top; font-size: 13.5px; }}
  td:first-child {{ color: #6B7280; width: 200px; }}
  .footer {{ margin-top: 36px; color: #9CA3AF; font-size: 11px; border-top: 1px solid #E5E7EB;
             padding-top: 10px; }}
</style></head><body>
<h1>{_html.escape(str(title))}</h1>
{chr(10).join(body)}
<div class="footer">Generated by Prism — grounded in your source material</div>
</body></html>"""
    return doc.encode("utf-8")


def _to_csv(content: dict) -> bytes:
    """Flat CSV of scalar fields + list items (for spreadsheets/BI tools)."""
    import csv as _csv
    import io as _io

    buf = _io.StringIO()
    writer = _csv.writer(buf)

    def scalar_rows(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("_quality", "language_note"):
                    continue
                scalar_rows(v, f"{prefix}{k}." if prefix else f"{k}.")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                scalar_rows(v, f"{prefix}{i + 1}.")
        elif isinstance(obj, str):
            label = prefix.rstrip(".")
            if len(obj) < 5000:
                writer.writerow([label, obj])

    scalar_rows(content)
    data = buf.getvalue()
    return data.encode("utf-8-sig")  # BOM so Excel opens UTF-8 correctly


def export_output(output_type: str, content: dict, fmt: str, title: str) -> tuple[str, bytes, str]:
    safe_title = re.sub(r"[^A-Za-z0-9_\- ]", "", title).strip().replace(" ", "_")[:60] or "output"
    if fmt == "md":
        return f"{safe_title}.md", _to_markdown(output_type, content).encode("utf-8"), "text/markdown"
    if fmt == "txt":
        return f"{safe_title}.txt", _flatten(content).encode("utf-8"), "text/plain"
    if fmt == "srt":
        name, data, _ = f"{safe_title}.srt", _to_srt(content), "application/x-subrip"
        return name, data, _
    if fmt == "docx":
        return f"{safe_title}.docx", _to_docx(content, output_type), \
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if fmt == "pptx":
        if output_type != "presentation":
            raise AppError("PPTX export is only available for presentations.")
        return f"{safe_title}.pptx", _to_pptx(content), \
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    if fmt == "pdf":
        from io import BytesIO
        from reportlab.platypus import SimpleDocTemplate
        from reportlab.lib.pagesizes import A4
        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, title=safe_title)
        doc.build(_pdf_story_blocks(content))
        return f"{safe_title}.pdf", buf.getvalue(), "application/pdf"
    if fmt == "html":
        return f"{safe_title}.html", _to_html(content, output_type), "text/html"
    if fmt == "json":
        import json as _json
        return f"{safe_title}.json", _json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8"), "application/json"
    if fmt == "csv":
        return f"{safe_title}.csv", _to_csv(content), "text/csv"
    raise AppError(f"Unsupported export format '{fmt}'.")
