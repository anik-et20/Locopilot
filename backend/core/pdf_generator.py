"""
PDF Generation Engine for LocalGPT
Converts Markdown / Structured Text into professional, beautifully styled binary PDF documents using ReportLab.
100% on-device, zero external network calls.
"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether

def generate_pdf_from_markdown(markdown_content: str, output_path: Path, title: Optional[str] = None) -> Path:
    """Compile markdown string into a valid, publication-ready PDF document."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Setup Document with comfortable margins
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    # Color Palette
    PRIMARY = colors.HexColor("#1e293b")      # Slate 800
    ACCENT = colors.HexColor("#4f46e5")       # Indigo 600
    MUTED = colors.HexColor("#64748b")        # Slate 500
    LINE_COLOR = colors.HexColor("#e2e8f0")   # Slate 200
    BG_TABLE_HEADER = colors.HexColor("#f1f5f9")
    BG_TABLE_ALT = colors.HexColor("#f8fafc")

    # Typography Styles
    base_styles = getSampleStyleSheet()

    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=base_styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=ACCENT,
        spaceAfter=8
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=base_styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=base_styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=ACCENT,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        'Heading3_Custom',
        parent=base_styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=PRIMARY,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=PRIMARY,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=PRIMARY,
        leftIndent=15,
        spaceAfter=3
    )

    meta_style = ParagraphStyle(
        'Meta_Custom',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=MUTED,
        spaceAfter=8
    )

    table_cell_style = ParagraphStyle(
        'TableCell_Custom',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=PRIMARY
    )

    table_header_style = ParagraphStyle(
        'TableHeader_Custom',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=PRIMARY
    )

    flowables = []
    lines = markdown_content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # Horizontal Rule
        if re.match(r'^(?:---|\*\*\*|___)$', line):
            flowables.append(HRFlowable(width="100%", thickness=0.8, color=LINE_COLOR, spaceBefore=6, spaceAfter=8))
            i += 1
            continue

        # Headings
        if line.startswith('# '):
            clean_text = _format_inline_markdown(line[2:].strip())
            flowables.append(Paragraph(clean_text, doc_title_style))
            i += 1
            continue
        elif line.startswith('## '):
            clean_text = _format_inline_markdown(line[3:].strip())
            flowables.append(Paragraph(clean_text, h1_style))
            i += 1
            continue
        elif line.startswith('### '):
            clean_text = _format_inline_markdown(line[4:].strip())
            flowables.append(Paragraph(clean_text, h2_style))
            i += 1
            continue
        elif line.startswith('#### '):
            clean_text = _format_inline_markdown(line[5:].strip())
            flowables.append(Paragraph(clean_text, h3_style))
            i += 1
            continue

        # Markdown Table Detection
        if line.startswith('|') and line.endswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                table_lines.append(lines[i].strip())
                i += 1

            table_flowable = _parse_markdown_table(table_lines, table_header_style, table_cell_style, BG_TABLE_HEADER, BG_TABLE_ALT, LINE_COLOR)
            if table_flowable:
                flowables.append(table_flowable)
                flowables.append(Spacer(1, 6))
            continue

        # Bullet List Items
        if re.match(r'^[\*\-]\s+', line):
            content = line[2:].strip()
            clean_text = _format_inline_markdown(content)
            flowables.append(Paragraph(f"&bull; {clean_text}", bullet_style))
            i += 1
            continue

        # Numbered List Items
        match_num = re.match(r'^(\d+)\.\s+(.*)$', line)
        if match_num:
            num = match_num.group(1)
            content = match_num.group(2).strip()
            clean_text = _format_inline_markdown(content)
            flowables.append(Paragraph(f"<b>{num}.</b> {clean_text}", bullet_style))
            i += 1
            continue

        # Metadata line (e.g. **Applicant:** ... | **Date:** ...)
        if line.startswith('**Applicant:**') or line.startswith('**Email:**') or line.startswith('**To:**'):
            clean_text = _format_inline_markdown(line)
            flowables.append(Paragraph(clean_text, meta_style))
            i += 1
            continue

        # Regular Paragraph
        clean_text = _format_inline_markdown(line)
        flowables.append(Paragraph(clean_text, body_style))
        i += 1

    # Build Document
    doc.build(flowables)
    return output_path

def _format_inline_markdown(text: str) -> str:
    """Convert inline markdown (*bold*, _italic_, links, code) into ReportLab XML format."""
    if not text:
        return ""

    # Escape XML specials first
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

    # Italic: *text* or _text_
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)(.*?)(?<!_)_(?!_)', r'<i>\1</i>', text)

    # Inline code: `code`
    text = re.sub(r'`([^`]+)`', r'<font name="Courier" color="#334155" size="8.5">\1</font>', text)

    # Markdown links: [text](url) -> text
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<font color="#4f46e5"><u>\1</u></font>', text)

    return text

def _parse_markdown_table(table_lines: List[str], header_style, cell_style, bg_header, bg_alt, border_color) -> Optional[Table]:
    """Parse raw markdown table lines into a styled ReportLab Table object."""
    if len(table_lines) < 2:
        return None

    raw_rows = []
    for line in table_lines:
        # Skip markdown separator row |---|---|
        if re.match(r'^\|[\s\-:|]+\|$', line):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        raw_rows.append(cells)

    if not raw_rows:
        return None

    # Max columns
    max_cols = max(len(r) for r in raw_rows)
    # Pad rows
    for r in raw_rows:
        while len(r) < max_cols:
            r.append("")

    # Convert cells to Paragraphs
    table_data = []
    for row_idx, row in enumerate(raw_rows):
        row_paragraphs = []
        is_header = (row_idx == 0)
        style = header_style if is_header else cell_style
        for cell in row:
            clean_cell = _format_inline_markdown(cell)
            row_paragraphs.append(Paragraph(clean_cell, style))
        table_data.append(row_paragraphs)

    # Width distribution across 520pt total width
    if max_cols == 2:
        col_widths = [150, 370]
    elif max_cols == 3:
        col_widths = [120, 250, 150]
    elif max_cols == 4:
        col_widths = [110, 150, 170, 90]
    else:
        col_widths = [520 / max_cols] * max_cols

    t = Table(table_data, colWidths=col_widths)
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), bg_header),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
    ]

    for row_idx in range(1, len(table_data)):
        if row_idx % 2 == 1:
            t_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg_alt))

    t.setStyle(TableStyle(t_style))
    return t
