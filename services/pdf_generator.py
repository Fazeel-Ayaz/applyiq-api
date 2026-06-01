import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.colors import HexColor
from models import ResumeObject


def generate_resume_pdf(resume: ResumeObject) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        "Name",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=2,
        textColor=HexColor("#1a1a1a"),
    )
    contact_style = ParagraphStyle(
        "Contact",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=6,
        textColor=HexColor("#555555"),
    )
    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=4,
        textColor=HexColor("#2c3e50"),
        borderWidth=0,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=12,
        spaceAfter=2,
        textColor=HexColor("#333333"),
    )
    role_style = ParagraphStyle(
        "Role",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        spaceBefore=4,
        spaceAfter=1,
        textColor=HexColor("#1a1a1a"),
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        fontSize=9,
        leading=11.5,
        leftIndent=12,
        spaceAfter=1,
        textColor=HexColor("#333333"),
        bulletIndent=0,
    )

    story = []

    info = resume.personal_info
    if info.name:
        story.append(Paragraph(info.name, name_style))
    contact_parts = [p for p in [info.email, info.phone, info.location, info.linkedin] if p]
    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), contact_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#cccccc")))

    if resume.summary:
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_header_style))
        story.append(Paragraph(resume.summary, body_style))

    if resume.experience:
        story.append(Paragraph("EXPERIENCE", section_header_style))
        story.append(HRFlowable(width="100%", thickness=0.3, color=HexColor("#dddddd")))
        for exp in resume.experience:
            dates = f"{exp.start_date} – {exp.end_date}" if exp.start_date else ""
            role_line = f"<b>{exp.title}</b> | {exp.company}"
            if dates:
                role_line += f" | {dates}"
            story.append(Paragraph(role_line, role_style))
            for bullet in exp.bullets:
                story.append(Paragraph(f"• {bullet}", bullet_style))

    if resume.education:
        story.append(Paragraph("EDUCATION", section_header_style))
        story.append(HRFlowable(width="100%", thickness=0.3, color=HexColor("#dddddd")))
        for edu in resume.education:
            dates = f"{edu.start_date} – {edu.end_date}" if edu.start_date else ""
            edu_line = f"<b>{edu.degree}</b> | {edu.institution}"
            if dates:
                edu_line += f" | {dates}"
            if edu.gpa:
                edu_line += f" | GPA: {edu.gpa}"
            story.append(Paragraph(edu_line, body_style))

    if resume.skills:
        story.append(Paragraph("SKILLS", section_header_style))
        story.append(HRFlowable(width="100%", thickness=0.3, color=HexColor("#dddddd")))
        story.append(Paragraph(", ".join(resume.skills), body_style))

    doc.build(story)
    return buffer.getvalue()
