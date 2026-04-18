import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

PURPLE = colors.HexColor('#5B3FD9')
TEAL = colors.HexColor('#0D6E56')
CORAL = colors.HexColor('#C14828')
AMBER = colors.HexColor('#835010')
INK = colors.HexColor('#1a1a1a')
MUTED = colors.HexColor('#555555')
CODEBG = colors.HexColor('#F4F2FF')

def generate_pdf(result: dict) -> bytes:
    """
    Accepts the analysis result dict and returns a PDF as bytes.
    The bytes can be returned from FastAPI or downloaded via Streamlit.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.85*inch, rightMargin=0.85*inch,
        topMargin=0.85*inch, bottomMargin=0.85*inch
    )
    styles = getSampleStyleSheet()

    def S(name, **kw):
        base = styles.get(name, styles['Normal'])
        return ParagraphStyle(name+'_g'+str(abs(hash(str(kw)))), parent=base, **kw)

    h1 = S('Normal', fontSize=22, textColor=PURPLE, fontName='Helvetica-Bold',
           spaceAfter=6, alignment=TA_CENTER)
    h2 = S('Normal', fontSize=14, textColor=PURPLE, fontName='Helvetica-Bold',
           spaceBefore=14, spaceAfter=4)
    sub = S('Normal', fontSize=11, textColor=MUTED, fontName='Helvetica',
            spaceAfter=4, alignment=TA_CENTER)
    body = S('Normal', fontSize=10.5, leading=16.5, textColor=INK,
             fontName='Helvetica', spaceAfter=6, alignment=TA_JUSTIFY)

    story = []

    # ■■ Cover section
    story.append(Spacer(1, 1.2*inch))
    story.append(Paragraph('MeetingMind AI', h1))
    story.append(Paragraph('Meeting Intelligence Report', sub))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}", sub))
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width='100%', thickness=1, color=PURPLE))
    story.append(Spacer(1, 0.3*inch))

    # ■■ Summary
    story.append(Paragraph('Executive Summary', h2))
    story.append(Paragraph(
        result.get('summary', 'No summary available.').replace('\n', ' '), body))

    # ■■ Action items table
    story.append(Paragraph('Action Items', h2))
    items = result.get('action_items', [])
    if items:
        header = [['Priority', 'Task', 'Owner', 'Deadline']]
        rows = [[
            item.get('priority', '-'),
            item.get('task', '-'),
            item.get('owner', '-'),
            item.get('deadline', '-')
        ] for item in items]
        tdata = header + rows
        tbl = Table(tdata, colWidths=[0.75*inch, 3.2*inch, 1.3*inch, 1.05*inch])
        
        pri_colors = {'High': CORAL, 'Medium': AMBER, 'Low': TEAL}
        table_style = [
            ('BACKGROUND', (0,0), (-1,0), PURPLE),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('LEADING', (0,0), (-1,-1), 13),
            ('LEFTPADDING',(0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING',(0,0),(-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#DDDDDD')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#F7F6FF')]),
        ]
        
        for i, item in enumerate(items, 1):
            pri = item.get('priority', '')
            c = pri_colors.get(pri, INK)
            table_style.append(('TEXTCOLOR', (0, i), (0, i), c))
            table_style.append(('FONTNAME', (0, i), (0, i), 'Helvetica-Bold'))
        
        tbl.setStyle(TableStyle(table_style))
        story.append(tbl)
    else:
        story.append(Paragraph('No action items identified.', body))

    # ■■ Sentiment
    story.append(Paragraph('Sentiment Analysis', h2))
    sent = result.get('sentiment', {})
    sent_rows = [
        ['Overall tone', sent.get('overall_tone', 'N/A')],
        ['Energy level', sent.get('energy_level', 'N/A')],
        ['Risk flags', ', '.join(sent.get('risk_flags', [])) or 'None'],
        ['Facilitator note', sent.get('recommendation', 'N/A')],
    ]
    st_tbl = Table(sent_rows, colWidths=[1.5*inch, 4.8*inch])
    st_tbl.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9.5),
        ('LEADING', (0,0), (-1,-1), 14),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('ROWBACKGROUNDS',(0,0),(-1,-1), [colors.HexColor('#F0FDF8'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#DDDDDD')),
    ]))
    story.append(st_tbl)
    story.append(Spacer(1, 0.2*inch))

    # ■■ Transcript
    story.append(PageBreak())
    story.append(Paragraph('Full Transcript', h2))
    transcript = result.get('transcript', 'No transcript.')
    for line in transcript.split('\n'):
        if line.strip():
            story.append(Paragraph(line, body))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(
            letter[0]/2, 0.5*inch,
            f'MeetingMind AI Report · Page {doc.page} · Confidential'
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()