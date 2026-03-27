import streamlit as st
import requests
import smtplib
import os
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, Image as RLImage
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════

GMAIL_ADDRESS   = "Wijdan.psyc@gmail.com"
GMAIL_PASSWORD  = "rias eeul lyuu stce"
THERAPIST_EMAIL = "Wijdan.psyc@gmail.com"
LOGO_FILE       = "logo.png"

# ══════════════════════════════════════════════════════════════
#  BAI — 21 items, scale 0–3
# ══════════════════════════════════════════════════════════════

BAI_QUESTIONS = [
    {"id": 1,  "text": "Numbness or tingling"},
    {"id": 2,  "text": "Feeling hot"},
    {"id": 3,  "text": "Wobbliness in legs"},
    {"id": 4,  "text": "Unable to relax"},
    {"id": 5,  "text": "Fear of worst happening"},
    {"id": 6,  "text": "Dizzy or lightheaded"},
    {"id": 7,  "text": "Heart pounding / racing"},
    {"id": 8,  "text": "Unsteady"},
    {"id": 9,  "text": "Terrified or afraid"},
    {"id": 10, "text": "Nervous"},
    {"id": 11, "text": "Feeling of choking"},
    {"id": 12, "text": "Hands trembling"},
    {"id": 13, "text": "Shaky / unsteady"},
    {"id": 14, "text": "Fear of losing control"},
    {"id": 15, "text": "Difficulty in breathing"},
    {"id": 16, "text": "Fear of dying"},
    {"id": 17, "text": "Scared"},
    {"id": 18, "text": "Indigestion"},
    {"id": 19, "text": "Faint / lightheaded"},
    {"id": 20, "text": "Face flushed"},
    {"id": 21, "text": "Hot / cold sweats"},
]

BAI_SCALE = {
    0: "0 — Not at all",
    1: "1 — Mildly, but it didn't bother me much",
    2: "2 — Moderately – it wasn't pleasant at times",
    3: "3 — Severely – it bothered me a lot",
}

# ══════════════════════════════════════════════════════════════
#  PSWQ — 16 items, scale 1–5
#  Reverse-scored items: 1, 3, 8, 10, 11
# ══════════════════════════════════════════════════════════════

PSWQ_QUESTIONS = [
    {"id": 1,  "text": "If I do not have enough time to do everything, I do not worry about it.",       "reverse": True},
    {"id": 2,  "text": "My worries overwhelm me.",                                                       "reverse": False},
    {"id": 3,  "text": "I do not tend to worry about things.",                                           "reverse": True},
    {"id": 4,  "text": "Many situations make me worry.",                                                 "reverse": False},
    {"id": 5,  "text": "I know I should not worry about things, but I just cannot help it.",             "reverse": False},
    {"id": 6,  "text": "When I am under pressure I worry a lot.",                                        "reverse": False},
    {"id": 7,  "text": "I am always worrying about something.",                                          "reverse": False},
    {"id": 8,  "text": "I find it easy to dismiss worrisome thoughts.",                                  "reverse": True},
    {"id": 9,  "text": "As soon as I finish one task, I start to worry about everything else I have to do.", "reverse": False},
    {"id": 10, "text": "I never worry about anything.",                                                  "reverse": True},
    {"id": 11, "text": "When there is nothing more I can do about a concern, I do not worry about it any more.", "reverse": True},
    {"id": 12, "text": "I have been a worrier all my life.",                                             "reverse": False},
    {"id": 13, "text": "I notice that I have been worrying about things.",                               "reverse": False},
    {"id": 14, "text": "Once I start worrying, I cannot stop.",                                          "reverse": False},
    {"id": 15, "text": "I worry all the time.",                                                          "reverse": False},
    {"id": 16, "text": "I worry about projects until they are all done.",                                "reverse": False},
]

PSWQ_SCALE = {
    1: "1 — Not at all typical of me",
    2: "2",
    3: "3",
    4: "4",
    5: "5 — Very typical of me",
}

# ══════════════════════════════════════════════════════════════
#  SCORING
# ══════════════════════════════════════════════════════════════

def calculate_bai_total(responses: dict) -> int:
    return sum(responses.values())

def get_bai_level(total: int) -> str:
    if total <= 21:   return "Low Anxiety"
    elif total <= 35: return "Moderate Anxiety"
    else:             return "Potentially Concerning Levels of Anxiety"

def get_bai_color(total: int) -> str:
    if total <= 21:   return "#5CB85C"
    elif total <= 35: return "#F0AD4E"
    else:             return "#D9534F"

def calculate_pswq_total(responses: dict) -> int:
    """Apply reverse scoring then sum. Range 16–80."""
    total = 0
    for q in PSWQ_QUESTIONS:
        raw = responses[q["id"]]
        scored = (6 - raw) if q["reverse"] else raw
        total += scored
    return total

def get_pswq_level(total: int) -> str:
    if total <= 44:   return "Low Worry"
    elif total <= 59: return "Moderate Worry"
    elif total <= 69: return "High Worry"
    else:             return "Very High Worry"

def get_pswq_color(total: int) -> str:
    if total <= 44:   return "#5CB85C"
    elif total <= 59: return "#F0AD4E"
    elif total <= 69: return "#E07B39"
    else:             return "#D9534F"

# ══════════════════════════════════════════════════════════════
#  GROQ REPORT GENERATION
# ══════════════════════════════════════════════════════════════

def generate_report(client_name: str, bai_total: int, bai_responses: dict,
                    pswq_total: int, pswq_responses: dict) -> str:

    bai_level  = get_bai_level(bai_total)
    pswq_level = get_pswq_level(pswq_total)

    bai_items = "\n".join(
        f"  {q['text']}: {bai_responses[q['id']]}/3"
        for q in BAI_QUESTIONS
    )

    pswq_items = "\n".join(
        f"  {'[R] ' if q['reverse'] else '      '}{q['text']}: raw={pswq_responses[q['id']]}, scored={(6 - pswq_responses[q['id']]) if q['reverse'] else pswq_responses[q['id']]}"
        for q in PSWQ_QUESTIONS
    )

    prompt = f"""You are a licensed clinical psychologist writing a confidential dual-instrument anxiety assessment report.

CLIENT: {client_name}
DATE: {datetime.datetime.now().strftime("%B %d, %Y")}

════════════════════════════════
INSTRUMENT 1: Beck Anxiety Inventory (BAI)
21 items · scale 0–3 · range 0–63
Total: {bai_total}/63 — {bai_level}
Scoring: 0–21 Low · 22–35 Moderate · 36–63 Concerning
Reliability: α=0.92 · test-retest r=0.75
Reference: Beck et al. (1988), J. Consulting and Clinical Psychology, 56, 893–897.

Item responses:
{bai_items}

════════════════════════════════
INSTRUMENT 2: Penn State Worry Questionnaire (PSWQ)
16 items · scale 1–5 · range 16–80 · [R] = reverse scored
Total: {pswq_total}/80 — {pswq_level}
Scoring: ≤44 Low · 45–59 Moderate · 60–69 High · 70–80 Very High
Reliability: α=0.93 · test-retest r=0.92
Reference: Meyer et al. (1990), Behaviour Research and Therapy, 28, 487–495.

Item responses ([R] = reverse scored):
{pswq_items}

════════════════════════════════
REPORT INSTRUCTIONS:

Write a professional clinical report with these clearly labelled sections. Each section should be concise, specific to the data, and non-repetitive across sections.

SECTION A — BECK ANXIETY INVENTORY (BAI)

A1. PRESENTING SYMPTOM PROFILE
Summarize the overall anxiety presentation from the BAI. Identify dominant symptom clusters (physiological, cognitive, affective) based on the item pattern.

A2. SYMPTOM ANALYSIS
Group items by cluster. Highlight the most severely endorsed items and their clinical significance. Note any interesting patterns or low-severity items suggesting resilience.

A3. SEVERITY & CLINICAL INTERPRETATION
Interpret the total score level. Note implications for daily functioning and any items warranting clinical attention.

────────────────────────────────
SECTION B — PENN STATE WORRY QUESTIONNAIRE (PSWQ)

B1. WORRY PROFILE
Summarize the worry presentation from the PSWQ. Note the total score, level, and key endorsed items (especially those scoring 4–5 after transformation).

B2. WORRY PATTERN ANALYSIS
Identify the nature of worry (pervasive, uncontrollable, situation-specific). Highlight the highest-scoring items. Note any low-scored items indicating protective factors.

B3. SEVERITY & CLINICAL INTERPRETATION
Interpret the PSWQ score in the context of GAD screening thresholds (scores ≥45 suggest clinically significant worry). Note differential implications.

────────────────────────────────
SECTION C — INTEGRATED ANXIETY PROFILE

C1. CROSS-INSTRUMENT SYNTHESIS
In 2–3 focused paragraphs, synthesize findings from both instruments. Describe how the BAI somatic/physiological picture and the PSWQ cognitive worry pattern interact to form a coherent anxiety profile. Note convergence or divergence between the two measures.

C2. CLINICAL FORMULATION
Based on both scores, outline a brief formulation: what type of anxiety presentation this pattern suggests (e.g., GAD features, panic-related anxiety, mixed presentation), and what maintains the anxiety.

C3. THERAPEUTIC IMPLICATIONS
Evidence-based treatment recommendations arising from the combined profile. Include modality suggestions (e.g., CBT, worry postponement, somatic techniques, mindfulness). Keep this section focused — 1 paragraph.

────────────────────────────────
SECTION D — SUMMARY

One concise paragraph for clinical records:
"According to the Beck Anxiety Inventory (BAI), {client_name} self-reports [BAI score]/63, indicating [BAI level], with predominant [symptom clusters]. The Penn State Worry Questionnaire (PSWQ) yields a score of [PSWQ score]/80, indicating [PSWQ level], characterized by [worry pattern]. Taken together, these findings suggest [integrated interpretation]."

────────────────────────────────
FORMATTING RULES:
- Use the section labels exactly as above (A1, A2, etc.)
- No preamble or closing remarks outside the sections
- No repetition of the same point across sections
- Clinical, precise language throughout
- Do not reproduce the scoring guides verbatim"""

    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from Streamlit secrets.")

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 3000,
            "temperature": 0.4,
        },
        timeout=90,
    )

    if not response.ok:
        try:    error_detail = response.json()
        except: error_detail = response.text
        raise Exception(f"Groq API error {response.status_code}: {error_detail}")

    return response.json()["choices"][0]["message"]["content"].strip()

# ══════════════════════════════════════════════════════════════
#  PDF CREATION
# ══════════════════════════════════════════════════════════════

def create_pdf_report(path, client_name, bai_total, bai_responses,
                      pswq_total, pswq_responses, report_text, timestamp):

    DARK   = colors.HexColor("#1C1917")
    WARM   = colors.HexColor("#6B5B45")
    LIGHT  = colors.HexColor("#F7F4F0")
    BORDER = colors.HexColor("#DDD5C8")

    bai_lvl_color  = colors.HexColor(get_bai_color(bai_total))
    pswq_lvl_color = colors.HexColor(get_pswq_color(pswq_total))

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    title_s   = ParagraphStyle("T",  fontName="Times-Roman",      fontSize=20, textColor=DARK,  alignment=TA_CENTER, spaceAfter=3)
    sub_s     = ParagraphStyle("S",  fontName="Times-Italic",      fontSize=10, textColor=WARM,  alignment=TA_CENTER, spaceAfter=2)
    meta_s    = ParagraphStyle("M",  fontName="Helvetica",         fontSize=8,  textColor=WARM,  alignment=TA_CENTER, spaceAfter=12)
    section_s = ParagraphStyle("Se", fontName="Helvetica-Bold",    fontSize=10, textColor=WARM,  spaceBefore=12, spaceAfter=4)
    body_s    = ParagraphStyle("B",  fontName="Helvetica",         fontSize=9.5,textColor=DARK,  leading=15, spaceAfter=5)
    small_s   = ParagraphStyle("Sm", fontName="Helvetica",         fontSize=8.5,textColor=WARM,  leading=13)
    footer_s  = ParagraphStyle("Ft", fontName="Helvetica-Oblique", fontSize=7.5,textColor=WARM,  leading=11, alignment=TA_CENTER)

    story = []
    date_str = datetime.datetime.now().strftime("%B %d, %Y  |  %H:%M")

    # ── Logo ──────────────────────────────────────────────────
    if os.path.exists(LOGO_FILE):
        try:
            logo = RLImage(LOGO_FILE, width=4*cm, height=2*cm)
            logo.hAlign = "CENTER"
            story.append(logo)
            story.append(Spacer(1, 0.3*cm))
        except Exception:
            pass

    story.append(Paragraph("Anxiety Assessment Report", title_s))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Beck Anxiety Inventory  ·  Penn State Worry Questionnaire", sub_s))
    story.append(Paragraph(f"CONFIDENTIAL  ·  {date_str}", meta_s))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 0.3*cm))

    # ── Client info ───────────────────────────────────────────
    info_data = [
        [Paragraph("<b>Client</b>", small_s), Paragraph(client_name, body_s),
         Paragraph("<b>Assessments</b>", small_s), Paragraph("BAI (21 items) · PSWQ (16 items)", body_s)],
        [Paragraph("<b>Date</b>", small_s), Paragraph(date_str, body_s),
         Paragraph("<b>Score Ranges</b>", small_s), Paragraph("BAI: 0–63  |  PSWQ: 16–80", body_s)],
    ]
    it = Table(info_data, colWidths=[3*cm, 6*cm, 3.5*cm, 4.5*cm])
    it.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT),
        ("BOX",           (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))
    story.append(it)
    story.append(Spacer(1, 0.4*cm))

    # ── Score summary (both instruments side by side) ─────────
    story.append(Paragraph("SCORE SUMMARY", section_s))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))

    def bar(score, max_score, width=30):
        filled = int((score / max_score) * width)
        return "█" * filled + "░" * (width - filled)

    summary_header = [
        Paragraph("<b>Instrument</b>", small_s),
        Paragraph("<b>Score</b>",      small_s),
        Paragraph("<b>Level</b>",      small_s),
        Paragraph("<b>Range Bar</b>",  small_s),
    ]
    summary_rows = [summary_header, [
        Paragraph("<b>Beck Anxiety Inventory (BAI)</b>",
                  ParagraphStyle("bi", fontName="Helvetica-Bold", fontSize=9, textColor=bai_lvl_color)),
        Paragraph(f"<b>{bai_total}/63</b>",
                  ParagraphStyle("bs", fontName="Helvetica-Bold", fontSize=9, textColor=bai_lvl_color, alignment=TA_CENTER)),
        Paragraph(get_bai_level(bai_total),
                  ParagraphStyle("bl", fontName="Helvetica", fontSize=8.5, textColor=bai_lvl_color)),
        Paragraph(f'<font color="{get_bai_color(bai_total)}">{bar(bai_total, 63)}</font>',
                  ParagraphStyle("bb", fontName="Courier", fontSize=7)),
    ], [
        Paragraph("<b>Penn State Worry Questionnaire (PSWQ)</b>",
                  ParagraphStyle("pi", fontName="Helvetica-Bold", fontSize=9, textColor=pswq_lvl_color)),
        Paragraph(f"<b>{pswq_total}/80</b>",
                  ParagraphStyle("ps", fontName="Helvetica-Bold", fontSize=9, textColor=pswq_lvl_color, alignment=TA_CENTER)),
        Paragraph(get_pswq_level(pswq_total),
                  ParagraphStyle("pl", fontName="Helvetica", fontSize=8.5, textColor=pswq_lvl_color)),
        Paragraph(f'<font color="{get_pswq_color(pswq_total)}">{bar(pswq_total, 80)}</font>',
                  ParagraphStyle("pb", fontName="Courier", fontSize=7)),
    ]]

    sum_table = Table(summary_rows, colWidths=[5.5*cm, 2*cm, 4.5*cm, 5*cm])
    sum_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#EDE9E3")),
        ("BACKGROUND",    (0,2),(-1,2),  LIGHT),
        ("BOX",           (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ALIGN",         (1,0),(1,-1),  "CENTER"),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 0.4*cm))

    # ── BAI item table ────────────────────────────────────────
    story.append(Paragraph("BECK ANXIETY INVENTORY — ITEM RESPONSES", section_s))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))

    SCORE_LABELS = {0: "Not at all", 1: "Mildly", 2: "Moderately", 3: "Severely"}
    SCORE_COLORS = {
        0: colors.HexColor("#5CB85C"), 1: colors.HexColor("#F0AD4E"),
        2: colors.HexColor("#E07B39"), 3: colors.HexColor("#D9534F"),
    }

    bai_header = [
        Paragraph("<b>#</b>",        small_s),
        Paragraph("<b>Symptom</b>",  small_s),
        Paragraph("<b>Score</b>",    small_s),
        Paragraph("<b>Severity</b>", small_s),
    ]
    bai_rows = [bai_header]
    for q in BAI_QUESTIONS:
        sc = bai_responses[q["id"]]
        sc_col = SCORE_COLORS[sc]
        bai_rows.append([
            Paragraph(str(q["id"]),
                      ParagraphStyle("in", fontName="Helvetica", fontSize=8.5, textColor=WARM, alignment=TA_CENTER)),
            Paragraph(q["text"], body_s),
            Paragraph(f"<b>{sc}</b>",
                      ParagraphStyle("is", fontName="Helvetica-Bold", fontSize=9, textColor=sc_col, alignment=TA_CENTER)),
            Paragraph(SCORE_LABELS[sc],
                      ParagraphStyle("il", fontName="Helvetica", fontSize=8.5, textColor=sc_col)),
        ])

    bai_table = Table(bai_rows, colWidths=[1.2*cm, 8.5*cm, 1.8*cm, 5.5*cm])
    bai_styles = [
        ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#EDE9E3")),
        ("BOX",           (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("ALIGN",         (0,0),(0,-1),  "CENTER"),
        ("ALIGN",         (2,0),(2,-1),  "CENTER"),
    ]
    for i in range(1, len(bai_rows)):
        if i % 2 == 0:
            bai_styles.append(("BACKGROUND", (0,i),(-1,i), LIGHT))
    bai_table.setStyle(TableStyle(bai_styles))
    story.append(bai_table)
    story.append(Spacer(1, 0.5*cm))

    # ── PSWQ item table ───────────────────────────────────────
    story.append(Paragraph("PENN STATE WORRY QUESTIONNAIRE — ITEM RESPONSES", section_s))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))

    pswq_header = [
        Paragraph("<b>#</b>",           small_s),
        Paragraph("<b>Statement</b>",   small_s),
        Paragraph("<b>Raw</b>",         small_s),
        Paragraph("<b>Scored</b>",      small_s),
    ]
    pswq_rows = [pswq_header]

    def pswq_score_color(scored):
        if scored <= 2: return colors.HexColor("#5CB85C")
        elif scored == 3: return colors.HexColor("#F0AD4E")
        elif scored == 4: return colors.HexColor("#E07B39")
        else: return colors.HexColor("#D9534F")

    for q in PSWQ_QUESTIONS:
        raw    = pswq_responses[q["id"]]
        scored = (6 - raw) if q["reverse"] else raw
        sc_col = pswq_score_color(scored)
        rev_tag = " <i>[R]</i>" if q["reverse"] else ""
        pswq_rows.append([
            Paragraph(str(q["id"]),
                      ParagraphStyle("pn", fontName="Helvetica", fontSize=8.5, textColor=WARM, alignment=TA_CENTER)),
            Paragraph(q["text"] + rev_tag,
                      ParagraphStyle("pt", fontName="Helvetica", fontSize=9, textColor=DARK, leading=13)),
            Paragraph(str(raw),
                      ParagraphStyle("pr", fontName="Helvetica", fontSize=9, textColor=WARM, alignment=TA_CENTER)),
            Paragraph(f"<b>{scored}</b>",
                      ParagraphStyle("ps2", fontName="Helvetica-Bold", fontSize=9, textColor=sc_col, alignment=TA_CENTER)),
        ])

    pswq_table = Table(pswq_rows, colWidths=[1.2*cm, 10*cm, 1.5*cm, 2.3*cm])
    pswq_styles = [
        ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#EDE9E3")),
        ("BOX",           (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("ALIGN",         (0,0),(0,-1),  "CENTER"),
        ("ALIGN",         (2,0),(3,-1),  "CENTER"),
    ]
    for i in range(1, len(pswq_rows)):
        if i % 2 == 0:
            pswq_styles.append(("BACKGROUND", (0,i),(-1,i), LIGHT))
    pswq_table.setStyle(TableStyle(pswq_styles))
    story.append(pswq_table)

    # ── PSWQ scoring note ─────────────────────────────────────
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "<i>[R] = reverse scored item. Scored value reflects the transformed score used in the total.</i>",
        ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=7.5, textColor=WARM)
    ))
    story.append(Spacer(1, 0.5*cm))

    # ── AI clinical report ────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("CLINICAL REPORT", section_s))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))

    for line in report_text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.18*cm))
        elif line.isupper() or (line.endswith(":") and len(line) < 70) or (
            line[:3] in ("A1.", "A2.", "A3.", "B1.", "B2.", "B3.", "C1.", "C2.", "C3.", "D. ", "D —")
            or line.startswith("SECTION")
        ):
            story.append(Paragraph(line, section_s))
        else:
            story.append(Paragraph(line, body_s))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "This report is strictly confidential and intended solely for the treating clinician. "
        "Not to be shared without explicit written consent. "
        "AI-assisted analysis should be reviewed alongside clinical judgment.",
        footer_s
    ))
    doc.build(story)

# ══════════════════════════════════════════════════════════════
#  EMAIL
# ══════════════════════════════════════════════════════════════

def send_report_email(pdf_path, client_name, bai_total, pswq_total, filename):
    date_str   = datetime.datetime.now().strftime("%B %d, %Y at %H:%M")
    bai_color  = get_bai_color(bai_total)
    pswq_color = get_pswq_color(pswq_total)

    msg = MIMEMultipart("mixed")
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = THERAPIST_EMAIL
    msg["Subject"] = f"[Anxiety Report] {client_name} — {date_str}"

    body_html = f"""
    <html><body style="font-family:Georgia,serif;color:#1C1917;background:#F7F4F0;padding:24px;">
      <div style="max-width:580px;margin:0 auto;background:white;border:1px solid #DDD5C8;border-radius:4px;padding:32px;">
        <h2 style="font-weight:300;font-size:22px;margin-bottom:2px;">Anxiety Assessment Report</h2>
        <p style="color:#6B5B45;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;margin-top:0;">
          BAI · PSWQ — New Submission
        </p>
        <hr style="border:none;border-top:1px solid #DDD5C8;margin:18px 0;">
        <table style="width:100%;font-size:14px;border-collapse:collapse;">
          <tr><td style="padding:6px 0;color:#6B5B45;width:40%;">Client</td><td><strong>{client_name}</strong></td></tr>
          <tr><td style="padding:6px 0;color:#6B5B45;">Date &amp; Time</td><td>{date_str}</td></tr>
        </table>
        <hr style="border:none;border-top:1px solid #DDD5C8;margin:18px 0;">
        <p style="font-size:13px;color:#6B5B45;margin-bottom:8px;font-weight:bold;">Assessment Results</p>
        <table style="width:100%;font-size:13px;border-collapse:collapse;">
          <tr>
            <td style="padding:6px 0;color:#6B5B45;width:50%;">BAI Total Score</td>
            <td><strong style="color:{bai_color};">{bai_total}/63 — {get_bai_level(bai_total)}</strong></td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#6B5B45;">PSWQ Total Score</td>
            <td><strong style="color:{pswq_color};">{pswq_total}/80 — {get_pswq_level(pswq_total)}</strong></td>
          </tr>
        </table>
        <hr style="border:none;border-top:1px solid #DDD5C8;margin:18px 0;">
        <p style="font-size:13px;line-height:1.6;">The full clinical report is attached as a PDF.</p>
        <p style="font-size:11px;color:#6B5B45;margin-top:20px;font-style:italic;">
          Confidential — intended only for the treating clinician.</p>
      </div>
    </body></html>"""

    msg.attach(MIMEText(body_html, "html"))
    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, THERAPIST_EMAIL, msg.as_string())

# ══════════════════════════════════════════════════════════════
#  STREAMLIT UI  — identical structure/CSS, no changes
# ══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Anxiety Assessment",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --bg: #F7F4F0;
    --white: #FFFFFF;
    --deep: #1C1917;
    --warm: #6B5B45;
    --accent: #8B6F47;
    --border: #DDD5C8;
    --selected: #2D2926;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg);
    color: var(--deep);
}
.stApp { background-color: var(--bg); }

.page-header {
    text-align: center;
    padding: 2.5rem 0 2rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.page-header h1 {
    font-family: 'Playfair Display', serif;
    font-size: 2.4rem;
    font-weight: 400;
    letter-spacing: 0.02em;
    margin-bottom: 0.3rem;
    color: var(--deep);
}
.page-header p {
    color: var(--warm);
    font-size: 0.82rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 400;
}

.section-divider {
    text-align: center;
    padding: 1.5rem 0 1rem 0;
    border-bottom: 1px solid var(--border);
    margin: 2rem 0 1.5rem 0;
}
.section-divider h2 {
    font-family: 'Playfair Display', serif;
    font-size: 1.6rem;
    font-weight: 400;
    color: var(--deep);
    margin-bottom: 0.2rem;
}
.section-divider p {
    color: var(--warm);
    font-size: 0.78rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.question-card {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1.5rem 1.8rem 0.5rem 1.8rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
}
.question-card:hover { border-color: var(--accent); }

.q-number {
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 0.3rem;
    font-weight: 500;
}
.q-text {
    font-family: 'Playfair Display', serif;
    font-size: 1.08rem;
    color: var(--deep);
    margin-bottom: 1rem;
    line-height: 1.5;
}

div[data-testid="stRadio"] > label { display: none; }
div[data-testid="stRadio"] > div { gap: 0.4rem !important; flex-direction: row !important; flex-wrap: wrap !important; }
div[data-testid="stRadio"] > div > label {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 3px !important;
    padding: 0.5rem 0.9rem !important;
    cursor: pointer !important;
    font-size: 0.82rem !important;
    color: var(--deep) !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: all 0.15s ease !important;
    min-width: 180px !important;
}
div[data-testid="stRadio"] > div > label:hover {
    border-color: var(--accent) !important;
    background: #F0EBE3 !important;
}

.progress-wrap { background: var(--border); border-radius: 2px; height: 3px; margin: 1.5rem 0 0.5rem 0; }
.progress-fill { height: 3px; border-radius: 2px; background: linear-gradient(90deg, var(--warm), var(--accent)); }

.stButton > button {
    background: var(--selected) !important;
    color: var(--bg) !important;
    border: none !important;
    padding: 0.8rem 2.8rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-radius: 2px !important;
    transition: background 0.2s ease !important;
}
.stButton > button:hover { background: var(--warm) !important; }

.thank-you {
    text-align: center;
    padding: 5rem 2rem;
}
.thank-you h2 {
    font-family: 'Playfair Display', serif;
    font-size: 2.2rem;
    font-weight: 400;
    margin-bottom: 1rem;
}
.thank-you p {
    color: var(--warm);
    font-size: 0.95rem;
    max-width: 380px;
    margin: 0 auto;
    line-height: 1.8;
}

div[data-testid="stTextInput"] input {
    background: white !important;
    border: 1px solid var(--border) !important;
    border-radius: 3px !important;
    font-family: 'DM Sans', sans-serif !important;
    color: var(--deep) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Routing ────────────────────────────────────────────────────────────────────
page = st.query_params.get("page", "client")

if page == "admin":
    st.markdown("""
    <div class="page-header">
        <p>Therapist Portal</p>
        <h1>Assessment Reports</h1>
    </div>""", unsafe_allow_html=True)

    if "admin_auth" not in st.session_state:
        st.session_state.admin_auth = False

    if not st.session_state.admin_auth:
        pwd = st.text_input("Enter admin password", type="password", placeholder="Password")
        if st.button("Access Portal"):
            if pwd == st.secrets.get("ADMIN_PASSWORD", ""):
                st.session_state.admin_auth = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    else:
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        files = sorted([f for f in os.listdir(reports_dir) if f.endswith(".pdf")], reverse=True)
        if not files:
            st.info("No reports submitted yet.")
        else:
            st.markdown(f"**{len(files)} report(s) on file**")
            for fname in files:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"📄 `{fname}`")
                with col2:
                    with open(os.path.join(reports_dir, fname), "rb") as f:
                        st.download_button("Download", data=f, file_name=fname,
                                           mime="application/pdf", key=fname)
        if st.button("Log out"):
            st.session_state.admin_auth = False
            st.rerun()

else:
    if "submitted"      not in st.session_state: st.session_state.submitted = False
    if "access_granted" not in st.session_state: st.session_state.access_granted = False

    if not st.session_state.access_granted:
        if os.path.exists(LOGO_FILE):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2: st.image(LOGO_FILE, use_container_width=True)
        st.markdown("""<div class="page-header">
            <p>Confidential Personality Assessment</p>
            <h1>Big Five Personality Test</h1>
        </div>""", unsafe_allow_html=True)
        st.markdown("""<div style="max-width:360px;margin:0 auto;padding:2rem 0;text-align:center;">
            <p style="color:#6B5B45;font-size:.9rem;margin-bottom:1.5rem;line-height:1.8;">
                This assessment is available to referred patients only.<br>
                Please enter the access code provided by your clinician.
            </p>
        </div>""", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            code = st.text_input("Access code", type="password",
                                 placeholder="Enter access code",
                                 label_visibility="collapsed")
            if st.button("Enter", use_container_width=True):
                valid_codes = [c.strip() for c in st.secrets.get("ACCESS_CODE", "").split(",")]
if code.strip() in valid_codes:
                    st.session_state.access_granted = True
                    st.rerun()
                else:
                    st.markdown("""<div style="background:#FFF0F0;border-left:3px solid #D9534F;
                        padding:.8rem 1rem;border-radius:0 4px 4px 0;
                        font-size:.88rem;color:#7A1A1A;margin:.5rem 0;">
                        &#9888; Incorrect access code. Please check and try again.
                    </div>""", unsafe_allow_html=True)
        st.stop()

    # ── CLIENT VIEW ────────────────────────────────────────────────────────────
    if st.session_state.submitted:
        st.markdown("""
        <div class="thank-you">
            <h2>Thank You</h2>
            <p>Your responses have been submitted successfully.<br>
            Your clinician will be in touch with you shortly.</p>
        </div>""", unsafe_allow_html=True)

    else:
        if os.path.exists(LOGO_FILE):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(LOGO_FILE, use_container_width=True)

        st.markdown("""
        <div class="page-header">
            <p>Confidential Anxiety Assessment</p>
            <h1>Anxiety Questionnaires</h1>
        </div>""", unsafe_allow_html=True)

        client_name = st.text_input("Your name (optional)", placeholder="First name or initials")

        # ── PART 1: BAI ───────────────────────────────────────────────────────
        st.markdown("""
        <div class="section-divider">
            <h2>Part 1 — Beck Anxiety Inventory</h2>
            <p>21 items · Past month · Scale 0–3</p>
        </div>
        <p style="font-size:0.88rem;color:#6B5B45;text-align:center;margin-bottom:1.5rem;line-height:1.8;">
        Indicate how much you have been <strong>bothered by each symptom during the past month</strong>, including today.
        </p>""", unsafe_allow_html=True)

        bai_responses  = {}
        bai_all_answered = True

        for q in BAI_QUESTIONS:
            qid = q["id"]
            st.markdown(f"""
            <div class="question-card">
                <div class="q-number">Symptom {qid} of 21</div>
                <div class="q-text">{q['text']}</div>
            </div>""", unsafe_allow_html=True)

            choice = st.radio(
                label=f"bai_{qid}",
                options=list(BAI_SCALE.values()),
                index=None,
                key=f"bai_{qid}",
                label_visibility="collapsed",
                horizontal=True,
            )
            if choice is None:
                bai_all_answered = False
            else:
                bai_responses[qid] = next(k for k, v in BAI_SCALE.items() if v == choice)

        # ── PART 2: PSWQ ─────────────────────────────────────────────────────
        st.markdown("""
        <div class="section-divider">
            <h2>Part 2 — Penn State Worry Questionnaire</h2>
            <p>16 items · General · Scale 1–5</p>
        </div>
        <p style="font-size:0.88rem;color:#6B5B45;text-align:center;margin-bottom:1.5rem;line-height:1.8;">
        Rate each statement on how <strong>typical it is of you</strong>.<br>
        Begin each statement with <strong>"I…"</strong> and answer based on how you generally are.
        </p>""", unsafe_allow_html=True)

        pswq_responses   = {}
        pswq_all_answered = True

        for q in PSWQ_QUESTIONS:
            qid = q["id"]
            st.markdown(f"""
            <div class="question-card">
                <div class="q-number">Statement {qid} of 16</div>
                <div class="q-text">{q['text']}</div>
            </div>""", unsafe_allow_html=True)

            choice = st.radio(
                label=f"pswq_{qid}",
                options=list(PSWQ_SCALE.values()),
                index=None,
                key=f"pswq_{qid}",
                label_visibility="collapsed",
                horizontal=True,
            )
            if choice is None:
                pswq_all_answered = False
            else:
                pswq_responses[qid] = next(k for k, v in PSWQ_SCALE.items() if v == choice)

        # ── Progress bar ──────────────────────────────────────────────────────
        total_q     = 21 + 16
        answered    = len(bai_responses) + len(pswq_responses)
        pct         = int((answered / total_q) * 100)
        all_answered = bai_all_answered and pswq_all_answered

        st.markdown(f"""
        <div style="text-align:center;font-size:0.78rem;color:#6B5B45;
                    letter-spacing:0.08em;margin-top:1.5rem;">
            {answered} of {total_q} answered
        </div>
        <div class="progress-wrap">
            <div class="progress-fill" style="width:{pct}%"></div>
        </div>""", unsafe_allow_html=True)

        if not all_answered and answered > 0:
            st.markdown("""
            <div style="background:#FFF8F0;border-left:3px solid #E07B39;
                        padding:1rem 1.2rem;border-radius:0 4px 4px 0;
                        font-size:0.88rem;color:#7A3D1A;margin:1rem 0;">
                ⚠ Please answer all 37 questions before submitting.
            </div>""", unsafe_allow_html=True)

        st.markdown('<div style="text-align:center;padding:2rem 0 3rem 0;">', unsafe_allow_html=True)
        submit = st.button("Submit Assessment", disabled=not all_answered)
        st.markdown('</div>', unsafe_allow_html=True)

        if submit and all_answered:
            with st.spinner("Submitting your responses..."):
                bai_total  = calculate_bai_total(bai_responses)
                pswq_total = calculate_pswq_total(pswq_responses)
                report_text = generate_report(
                    client_name or "Anonymous",
                    bai_total, bai_responses,
                    pswq_total, pswq_responses,
                )

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = (client_name or "anonymous").replace(" ", "_").lower()
                filename  = f"Anxiety_{safe_name}_{timestamp}.pdf"
                os.makedirs("reports", exist_ok=True)
                pdf_path  = os.path.join("reports", filename)

                create_pdf_report(
                    pdf_path, client_name or "Anonymous",
                    bai_total, bai_responses,
                    pswq_total, pswq_responses,
                    report_text, timestamp,
                )

                try:
                    send_report_email(pdf_path, client_name or "Anonymous",
                                      bai_total, pswq_total, filename)
                except Exception as e:
                    st.warning(f"Report saved but email failed: {e}")

                st.session_state.submitted = True
                st.rerun()
