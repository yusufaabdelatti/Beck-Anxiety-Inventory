import streamlit as st
import requests
import smtplib
import os
import datetime
import base64
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
#  CONFIGURATION — edit this section only
# ══════════════════════════════════════════════════════════════

GMAIL_ADDRESS   = "Wijdan.psyc@gmail.com"
GMAIL_PASSWORD  = "rias eeul lyuu stce"
THERAPIST_EMAIL = "Wijdan.psyc@gmail.com"

LOGO_FILE = "logo.png"   # ← name your logo file exactly this in GitHub

# ══════════════════════════════════════════════════════════════
#  BAI QUESTIONS  (21 items, scale 0–3)
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

SCALE_OPTIONS = {
    0: "0 — Not at all",
    1: "1 — Mildly, but it didn't bother me much",
    2: "2 — Moderately – it wasn't pleasant at times",
    3: "3 — Severely – it bothered me a lot",
}

# ══════════════════════════════════════════════════════════════
#  SCORING
# ══════════════════════════════════════════════════════════════

def calculate_total(responses: dict) -> int:
    """Sum all 21 item scores (each 0–3). Max = 63."""
    return sum(responses.values())

def get_anxiety_level(total: int) -> str:
    if total <= 21:
        return "Low Anxiety"
    elif total <= 35:
        return "Moderate Anxiety"
    else:
        return "Potentially Concerning Levels of Anxiety"

def get_anxiety_color(total: int) -> str:
    if total <= 21:
        return "#5CB85C"
    elif total <= 35:
        return "#F0AD4E"
    else:
        return "#D9534F"

# ══════════════════════════════════════════════════════════════
#  GROQ REPORT GENERATION
# ══════════════════════════════════════════════════════════════

def generate_report(client_name: str, total: int, responses: dict) -> str:
    level = get_anxiety_level(total)

    # Build item-level detail for the prompt
    item_lines = "\n".join(
        f"  {q['text']}: {responses[q['id']]}/3"
        for q in BAI_QUESTIONS
    )

    prompt = f"""You are a licensed clinical psychologist writing a confidential professional anxiety assessment report.

CLIENT: {client_name}
ASSESSMENT: Beck Anxiety Inventory (BAI) — 21 items, scale 0–3 per item, total score 0–63

TOTAL SCORE: {total}/63 — {level}

SCORING GUIDE:
- 0–21: Low Anxiety
- 22–35: Moderate Anxiety
- 36–63: Potentially Concerning Levels of Anxiety

ITEM-LEVEL RESPONSES:
{item_lines}

PSYCHOMETRIC PROPERTIES:
- Internal consistency: Cronbach's α = 0.92
- Test-retest reliability (1 week): 0.75
- Moderately correlated with Hamilton Anxiety Rating Scale (.51)
- Mildly correlated with Hamilton Depression Rating Scale (.25)
- Reference: Beck, A.T., Epstein, N., Brown, G., & Steer, R.A. (1988). Journal of Consulting and Clinical Psychology, 56, 893–897.

---
Write a full professional anxiety assessment report with the following sections:

1. ASSESSMENT OVERVIEW
   - Instrument used, purpose, psychometric properties, and administration context.

2. PRESENTING SYMPTOM PROFILE
   - Narrative summary of the client's overall anxiety presentation based on the total score and item-level pattern.
   - Identify the most prominently endorsed symptom clusters (physiological, cognitive, affective).

3. SYMPTOM-BY-SYMPTOM ANALYSIS
   - Group symptoms into clusters (physiological arousal, cognitive anxiety, somatic symptoms) and discuss the pattern.
   - Highlight the most severely endorsed items and their clinical significance.
   - Note any discrepancies or clinically interesting patterns in the item-level data.

4. SEVERITY & CLINICAL INTERPRETATION
   - Interpret what the total score and level mean for this specific client.
   - Discuss implications for daily functioning, relationships, and wellbeing.
   - Note any items that may warrant immediate clinical attention.

5. DIFFERENTIAL CONSIDERATIONS
   - Based on the symptom profile, note any patterns consistent with specific anxiety presentations (GAD, panic, social anxiety, etc.).
   - Note this is a screening tool only and does not yield a diagnosis.

6. STRENGTHS & PROTECTIVE FACTORS
   - Identify any items with low or absent scores that may indicate relative areas of resilience.

7. THERAPEUTIC & PRACTICAL IMPLICATIONS
   - Evidence-based suggestions for treatment approach (e.g., CBT, relaxation training, exposure).
   - How this anxiety profile may affect the therapeutic relationship and treatment planning.
   - Practical self-management recommendations.

8. SUMMARY
   - One concise paragraph suitable for clinical records:
     "According to the Beck Anxiety Inventory (BAI), [client] self-reports a total score of [X]/63, indicating [level]. [Brief narrative of predominant symptoms]."

Use formal clinical language. Be specific to the scores and item pattern — avoid generic anxiety descriptions. Ready for placement in a clinical file."""

    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from Streamlit secrets.")

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2500,
            "temperature": 0.4,
        },
        timeout=60,
    )

    if not response.ok:
        try:
            error_detail = response.json()
        except Exception:
            error_detail = response.text
        raise Exception(f"Groq API error {response.status_code}: {error_detail}")

    return response.json()["choices"][0]["message"]["content"].strip()

# ══════════════════════════════════════════════════════════════
#  PDF CREATION
# ══════════════════════════════════════════════════════════════

def create_pdf_report(path, client_name, total, responses, report_text, timestamp):
    DARK   = colors.HexColor("#1C1917")
    WARM   = colors.HexColor("#6B5B45")
    LIGHT  = colors.HexColor("#F7F4F0")
    BORDER = colors.HexColor("#DDD5C8")
    WHITE  = colors.white

    level     = get_anxiety_level(total)
    lvl_color = colors.HexColor(get_anxiety_color(total))

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

    # Logo
    if os.path.exists(LOGO_FILE):
        try:
            logo = RLImage(LOGO_FILE, width=4*cm, height=2*cm)
            logo.hAlign = "CENTER"
            story.append(logo)
            story.append(Spacer(1, 0.3*cm))
        except Exception:
            pass

    story.append(Paragraph("Beck Anxiety Inventory", title_s))
    story.append(Paragraph("Clinical Anxiety Assessment Report", sub_s))
    story.append(Paragraph(f"CONFIDENTIAL  ·  {date_str}", meta_s))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 0.3*cm))

    # Client info
    info_data = [
        [Paragraph("<b>Client</b>", small_s), Paragraph(client_name, body_s),
         Paragraph("<b>Assessment</b>", small_s), Paragraph("BAI (21 items)", body_s)],
        [Paragraph("<b>Date</b>", small_s), Paragraph(date_str, body_s),
         Paragraph("<b>Score Range</b>", small_s), Paragraph("0 – 63 total", body_s)],
    ]
    it = Table(info_data, colWidths=[3*cm, 6*cm, 3*cm, 5*cm])
    it.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), LIGHT),
        ("BOX",        (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",  (0,0),(-1,-1), 0.3, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))
    story.append(it)
    story.append(Spacer(1, 0.4*cm))

    # Total score summary
    story.append(Paragraph("TOTAL SCORE SUMMARY", section_s))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))

    bar_filled = int((total / 63) * 36)
    bar = "█" * bar_filled + "░" * (36 - bar_filled)

    score_header = [
        Paragraph("<b>Score</b>", small_s),
        Paragraph("<b>Level</b>", small_s),
        Paragraph("<b>Range Bar (0 ──────────────────── 63)</b>", small_s),
    ]
    score_rows = [score_header, [
        Paragraph(f"<b>{total}/63</b>",
                  ParagraphStyle("SC", fontName="Helvetica-Bold", fontSize=11, textColor=lvl_color, alignment=TA_CENTER)),
        Paragraph(level,
                  ParagraphStyle("LV", fontName="Helvetica-Bold", fontSize=9, textColor=lvl_color, alignment=TA_CENTER)),
        Paragraph(f'<font color="{get_anxiety_color(total)}">{bar}</font>',
                  ParagraphStyle("BR", fontName="Courier", fontSize=7, textColor=lvl_color)),
    ]]

    st_table = Table(score_rows, colWidths=[2.5*cm, 7*cm, 7.5*cm])
    st_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), colors.HexColor("#EDE9E3")),
        ("BACKGROUND", (0,1),(-1,1), LIGHT),
        ("BOX",        (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",  (0,0),(-1,-1), 0.3, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ALIGN", (0,0),(1,-1), "CENTER"),
    ]))
    story.append(st_table)
    story.append(Spacer(1, 0.3*cm))

    # Item-level table
    story.append(Paragraph("ITEM-LEVEL RESPONSES", section_s))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))

    SCORE_LABELS = {0: "Not at all", 1: "Mildly", 2: "Moderately", 3: "Severely"}
    SCORE_COLORS = {
        0: colors.HexColor("#5CB85C"),
        1: colors.HexColor("#F0AD4E"),
        2: colors.HexColor("#E07B39"),
        3: colors.HexColor("#D9534F"),
    }

    item_header = [
        Paragraph("<b>#</b>", small_s),
        Paragraph("<b>Symptom</b>", small_s),
        Paragraph("<b>Score</b>", small_s),
        Paragraph("<b>Severity</b>", small_s),
    ]
    item_rows = [item_header]
    for q in BAI_QUESTIONS:
        sc = responses[q["id"]]
        sc_color = SCORE_COLORS[sc]
        item_rows.append([
            Paragraph(str(q["id"]),
                      ParagraphStyle("IN", fontName="Helvetica", fontSize=8.5, textColor=WARM, alignment=TA_CENTER)),
            Paragraph(q["text"], body_s),
            Paragraph(f"<b>{sc}</b>",
                      ParagraphStyle("IS", fontName="Helvetica-Bold", fontSize=9, textColor=sc_color, alignment=TA_CENTER)),
            Paragraph(SCORE_LABELS[sc],
                      ParagraphStyle("IL", fontName="Helvetica", fontSize=8.5, textColor=sc_color)),
        ])

    item_table = Table(item_rows, colWidths=[1.2*cm, 8.5*cm, 1.8*cm, 5.5*cm])
    item_styles = [
        ("BACKGROUND", (0,0),(-1,0), colors.HexColor("#EDE9E3")),
        ("BOX",        (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",  (0,0),(-1,-1), 0.3, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("ALIGN", (0,0),(0,-1), "CENTER"),
        ("ALIGN", (2,0),(2,-1), "CENTER"),
    ]
    for row_i in range(1, len(item_rows)):
        if row_i % 2 == 0:
            item_styles.append(("BACKGROUND", (0,row_i),(-1,row_i), LIGHT))
    item_table.setStyle(TableStyle(item_styles))
    story.append(item_table)
    story.append(Spacer(1, 0.5*cm))

    # AI report
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("CLINICAL REPORT", section_s))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))

    for line in report_text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.18*cm))
        elif line.isupper() or (line.endswith(":") and len(line) < 60):
            story.append(Paragraph(line, section_s))
        else:
            story.append(Paragraph(line, body_s))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "This report is strictly confidential and intended solely for the treating clinician. "
        "It is not to be shared with the client or any third party without explicit written consent. "
        "AI-assisted analysis should be reviewed in conjunction with clinical judgment.",
        footer_s
    ))
    doc.build(story)

# ══════════════════════════════════════════════════════════════
#  EMAIL SENDER
# ══════════════════════════════════════════════════════════════

def send_report_email(pdf_path, client_name, total, filename):
    date_str  = datetime.datetime.now().strftime("%B %d, %Y at %H:%M")
    level     = get_anxiety_level(total)
    lvl_color = get_anxiety_color(total)

    msg = MIMEMultipart("mixed")
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = THERAPIST_EMAIL
    msg["Subject"] = f"[BAI Report] {client_name} — {date_str}"

    body_html = f"""
    <html><body style="font-family:Georgia,serif;color:#1C1917;background:#F7F4F0;padding:24px;">
      <div style="max-width:580px;margin:0 auto;background:white;border:1px solid #DDD5C8;border-radius:4px;padding:32px;">
        <h2 style="font-weight:300;font-size:22px;margin-bottom:2px;">Beck Anxiety Inventory</h2>
        <p style="color:#6B5B45;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;margin-top:0;">
          New Assessment Submitted
        </p>
        <hr style="border:none;border-top:1px solid #DDD5C8;margin:18px 0;">
        <table style="width:100%;font-size:14px;border-collapse:collapse;">
          <tr>
            <td style="padding:6px 0;color:#6B5B45;width:40%;">Client</td>
            <td><strong>{client_name}</strong></td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#6B5B45;">Date &amp; Time</td>
            <td>{date_str}</td>
          </tr>
        </table>
        <hr style="border:none;border-top:1px solid #DDD5C8;margin:18px 0;">
        <p style="font-size:13px;color:#6B5B45;margin-bottom:8px;font-weight:bold;">Assessment Result</p>
        <table style="width:100%;font-size:13px;border-collapse:collapse;">
          <tr>
            <td style="padding:6px 0;color:#6B5B45;width:40%;">Total Score</td>
            <td><strong style="color:{lvl_color};">{total}/63</strong></td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#6B5B45;">Anxiety Level</td>
            <td><strong style="color:{lvl_color};">{level}</strong></td>
          </tr>
        </table>
        <hr style="border:none;border-top:1px solid #DDD5C8;margin:18px 0;">
        <p style="font-size:13px;line-height:1.6;">The full clinical report is attached as a PDF.</p>
        <p style="font-size:11px;color:#6B5B45;margin-top:20px;font-style:italic;">
          This message is confidential and intended only for the treating clinician.</p>
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
#  STREAMLIT APP
# ══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Beck Anxiety Inventory",
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
.q-stem {
    font-size: 0.8rem;
    color: var(--warm);
    font-style: italic;
    margin-bottom: 0.8rem;
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
    min-width: 200px !important;
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

.section-label {
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--warm);
    font-weight: 500;
    margin: 2rem 0 1rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--border);
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
    # ── CLIENT VIEW ────────────────────────────────────────────────────────────
    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    if st.session_state.submitted:
        st.markdown("""
        <div class="thank-you">
            <h2>Thank You</h2>
            <p>Your responses have been submitted successfully.<br>
            Your clinician will be in touch with you shortly.</p>
        </div>""", unsafe_allow_html=True)
    else:
        # Logo
        if os.path.exists(LOGO_FILE):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(LOGO_FILE, use_container_width=True)

        st.markdown("""
        <div class="page-header">
            <p>Confidential Anxiety Assessment</p>
            <h1>Beck Anxiety Inventory</h1>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <p style="font-size:0.88rem;color:#6B5B45;text-align:center;margin-bottom:0.5rem;line-height:1.8;">
        Below is a list of common symptoms of anxiety. Please carefully read each item.<br>
        Indicate how much you have been <strong>bothered by that symptom during the past month</strong>, including today.
        </p>""", unsafe_allow_html=True)

        client_name = st.text_input("Your name (optional)", placeholder="First name or initials")
        st.markdown("<br>", unsafe_allow_html=True)

        responses = {}
        all_answered = True

        for q in BAI_QUESTIONS:
            qid = q["id"]
            st.markdown(f"""
            <div class="question-card">
                <div class="q-number">Symptom {qid} of 21</div>
                <div class="q-text">{q['text']}</div>
            </div>""", unsafe_allow_html=True)

            choice = st.radio(
                label=f"q_{qid}",
                options=list(SCALE_OPTIONS.values()),
                index=None,
                key=f"q_{qid}",
                label_visibility="collapsed",
                horizontal=True,
            )

            if choice is None:
                all_answered = False
            else:
                score_val = next(k for k, v in SCALE_OPTIONS.items() if v == choice)
                responses[qid] = score_val

        answered_count = len(responses)
        pct = int((answered_count / 21) * 100)
        st.markdown(f"""
        <div style="text-align:center;font-size:0.78rem;color:#6B5B45;
                    letter-spacing:0.08em;margin-top:1.5rem;">
            {answered_count} of 21 answered
        </div>
        <div class="progress-wrap">
            <div class="progress-fill" style="width:{pct}%"></div>
        </div>""", unsafe_allow_html=True)

        if not all_answered and answered_count > 0:
            st.markdown("""
            <div style="background:#FFF8F0;border-left:3px solid #E07B39;
                        padding:1rem 1.2rem;border-radius:0 4px 4px 0;
                        font-size:0.88rem;color:#7A3D1A;margin:1rem 0;">
                ⚠ Please answer all 21 questions before submitting.
            </div>""", unsafe_allow_html=True)

        st.markdown('<div style="text-align:center;padding:2rem 0 3rem 0;">', unsafe_allow_html=True)
        submit = st.button("Submit Assessment", disabled=not all_answered)
        st.markdown('</div>', unsafe_allow_html=True)

        if submit and all_answered:
            with st.spinner("Submitting your responses..."):
                total       = calculate_total(responses)
                report_text = generate_report(client_name or "Anonymous", total, responses)

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = (client_name or "anonymous").replace(" ", "_").lower()
                filename  = f"BAI_{safe_name}_{timestamp}.pdf"
                os.makedirs("reports", exist_ok=True)
                pdf_path  = os.path.join("reports", filename)

                create_pdf_report(pdf_path, client_name or "Anonymous", total, responses, report_text, timestamp)

                try:
                    send_report_email(pdf_path, client_name or "Anonymous", total, filename)
                except Exception as e:
                    st.warning(f"Report saved but email failed: {e}")

                st.session_state.submitted = True
                st.rerun()
