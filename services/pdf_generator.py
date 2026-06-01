import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.colors import HexColor
from models import ResumeObject


# One-page enforcement strategy:
# 1. Reduce font sizes and spacing
# 2. Limit bullets per role (max 4)
# 3. Truncate summary to 2 sentences
# 4. If still overflows, scale down font sizes further via a second pass

PAGE_HEIGHT = letter[1]
PAGE_WIDTH = letter[0]

TOP_MARGIN = 0.4 * inch
BOTTOM_MARGIN = 0.4 * inch
LEFT_MARGIN = 0.55 * inch
RIGHT_MARGIN = 0.55 * inch

MAX_BULLETS_PER_ROLE = 4
MAX_ROLES = 4  # show max 4 most recent roles


def _build_story(resume: ResumeObject, scale: float = 1.0) -> list:
    """Build the story elements with optional font scale factor for fitting."""

    def s(size):
        return max(6.5, size * scale)

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        "Name",
        parent=styles["Normal"],
        fontSize=s(16),
        leading=s(20),
        alignment=TA_CENTER,
        spaceAfter=s(2),
        textColor=HexColor("#1a1a1a"),
        fontName="Helvetica-Bold",
    )
    contact_style = ParagraphStyle(
        "Contact",
        parent=styles["Normal"],
        fontSize=s(8.5),
        leading=s(11),
        alignment=TA_CENTER,
        spaceAfter=s(4),
        textColor=HexColor("#555555"),
    )
    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontSize=s(9.5),
        leading=s(12),
        spaceBefore=s(7),
        spaceAfter=s(3),
        textColor=HexColor("#2c3e50"),
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=s(8.5),
        leading=s(11),
        spaceAfter=s(1),
        textColor=HexColor("#333333"),
    )
    role_style = ParagraphStyle(
        "Role",
        parent=styles["Normal"],
        fontSize=s(9),
        leading=s(11),
        spaceBefore=s(4),
        spaceAfter=s(1),
        textColor=HexColor("#1a1a1a"),
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        fontSize=s(8.5),
        leading=s(10.5),
        leftIndent=10,
        spaceAfter=s(1),
        textColor=HexColor("#333333"),
    )

    story = []

    # Header
    info = resume.personal_info
    if info.name:
        story.append(Paragraph(info.name, name_style))
    contact_parts = [p for p in [info.email, info.phone, info.location, info.linkedin] if p]
    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), contact_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#cccccc"), spaceAfter=2))

    # Summary — truncate to 2 sentences max
    if resume.summary:
        sentences = resume.summary.replace("! ", ". ").replace("? ", ". ").split(". ")
        short_summary = ". ".join(sentences[:2])
        if not short_summary.endswith("."):
            short_summary += "."
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_header_style))
        story.append(HRFlowable(width="100%", thickness=0.3, color=HexColor("#dddddd"), spaceAfter=2))
        story.append(Paragraph(short_summary, body_style))

    # Experience — cap at MAX_ROLES most recent, MAX_BULLETS_PER_ROLE bullets each
    if resume.experience:
        story.append(Paragraph("EXPERIENCE", section_header_style))
        story.append(HRFlowable(width="100%", thickness=0.3, color=HexColor("#dddddd"), spaceAfter=2))
        for exp in resume.experience[:MAX_ROLES]:
            dates = f"{exp.start_date} – {exp.end_date}" if exp.start_date else ""
            role_line = f"<b>{exp.title}</b> | {exp.company}"
            if dates:
                role_line += f" <font color='#777777'>| {dates}</font>"
            story.append(Paragraph(role_line, role_style))
            bullets = exp.bullets[:MAX_BULLETS_PER_ROLE]
            for bullet in bullets:
                # Truncate long bullets at 120 chars
                text = bullet if len(bullet) <= 120 else bullet[:117].rsplit(" ", 1)[0] + "…"
                story.append(Paragraph(f"• {text}", bullet_style))

    # Education
    if resume.education:
        story.append(Paragraph("EDUCATION", section_header_style))
        story.append(HRFlowable(width="100%", thickness=0.3, color=HexColor("#dddddd"), spaceAfter=2))
        for edu in resume.education:
            dates = f"{edu.start_date} – {edu.end_date}" if edu.start_date else ""
            edu_line = f"<b>{edu.degree}</b> | {edu.institution}"
            if dates:
                edu_line += f" | {dates}"
            if edu.gpa:
                edu_line += f" | GPA: {edu.gpa}"
            story.append(Paragraph(edu_line, body_style))

    # Skills — single line, truncate if too many
    if resume.skills:
        story.append(Paragraph("SKILLS", section_header_style))
        story.append(HRFlowable(width="100%", thickness=0.3, color=HexColor("#dddddd"), spaceAfter=2))
        skills_text = ", ".join(resume.skills[:20])  # cap at 20 skills
        story.append(Paragraph(skills_text, body_style))

    return story


def _measure_story_height(story: list) -> float:
    """Render to a dummy buffer and measure actual page count."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
    )
    # Use a page counter to detect overflow
    page_count = [0]

    def on_page(canvas, doc):
        page_count[0] += 1

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return page_count[0]


def generate_resume_pdf(resume: ResumeObject) -> bytes:
    """
    Generate a one-page resume PDF.
    Attempts at scale=1.0, then reduces font scale until it fits one page.
    """
    scales = [1.0, 0.93, 0.86, 0.80]

    for scale in scales:
        story = _build_story(resume, scale=scale)
        pages = _measure_story_height(story)
        if pages <= 1:
            break

    # Final render with the working scale
    story = _build_story(resume, scale=scale)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
    )
    doc.build(story)
    return buffer.getvalue()
