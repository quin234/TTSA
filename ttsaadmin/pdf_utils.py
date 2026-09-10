import io
from decimal import Decimal
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def _format_decimal(value, places=2):
    """Format a Decimal/float to a fixed number of decimal places."""
    if value is None:
        return ""
    try:
        d = Decimal(str(value))
        return f"{d:.{places}f}"
    except Exception:
        return str(value)


def generate_pairings_pdf(tournament, round_number, games, bye_players=None):
    """Generate a professional PDF for round pairings."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    
    def add_watermark(canvas, doc):
        """Add TTSA watermark to the page"""
        canvas.saveState()
        
        # Set watermark properties for professional appearance
        canvas.setFont("Helvetica-Bold", 60)
        
        # Professional watermark color with proper transparency
        # Using light gray with 15% opacity for subtle but visible watermark
        canvas.setFillColorRGB(0.7, 0.7, 0.7)
        canvas.setFillAlpha(0.15)  # 15% opacity for professional watermark
        
        # Page dimensions
        page_width, page_height = A4
        
        # Watermark text
        watermark_text = "TTSA"
        
        # Calculate text width for centering
        text_width = canvas.stringWidth(watermark_text, "Helvetica-Bold", 60)
        
        # Center position
        center_x = page_width / 2
        center_y = page_height / 2
        
        # Draw professional diagonal watermark
        canvas.saveState()
        canvas.translate(center_x, center_y)
        canvas.rotate(-45)  # Professional -45 degree diagonal rotation
        canvas.drawString(-text_width / 2, 0, watermark_text)
        canvas.restoreState()
        
        canvas.restoreState()

    styles = getSampleStyleSheet()
    academy_style = ParagraphStyle(
        'AcademyName',
        parent=styles['Title'],
        fontSize=14,
        alignment=0,
        spaceAfter=6,
        textColor=colors.black,
    )
    title_style = ParagraphStyle(
        'PairingTitle',
        parent=styles['Title'],
        fontSize=18,
        alignment=0,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        'PairingSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=0,
        spaceAfter=12,
        textColor=colors.black,
    )
    small_style = ParagraphStyle(
        'SmallLeft',
        parent=styles['Normal'],
        fontSize=9,
        alignment=0,
        textColor=colors.black,
    )
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,
        textColor=colors.black,
    )

    elements = []

    elements.append(Paragraph("TAITA TAVETA SPORTS ACADEMY", academy_style))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(tournament.name, title_style))
    elements.append(Paragraph(f"Round {round_number}", subtitle_style))
    elements.append(Paragraph(
        f"Date: {tournament.start_date.strftime('%B %d, %Y') if tournament.start_date else ''}",
        small_style
    ))
    elements.append(Spacer(1, 10 * mm))

    data = [['Table', 'White Player', 'Black Player']]
    for game in games:
        data.append([
            str(game.board_number),
            game.white_player.player_name.upper(),
            game.black_player.player_name.upper(),
        ])

    table = Table(
        data,
        colWidths=[20 * mm, 80 * mm, 80 * mm],
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)

    if bye_players:
        bye_names = ', '.join(p.player_name.upper() for p in bye_players)
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph(f"Bye: {bye_names}", small_style))

    # Add footer with contact information and social media
    elements.append(Spacer(1, 20 * mm))
    elements.append(Paragraph(
        "Email: ttsaacademy@gmail.com",
        footer_style
    ))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(
        "TikTok: @ttsaacademy | Facebook: @ttsaacademy | Instagram: @ttsaacademy",
        footer_style
    ))

    doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
    buffer.seek(0)
    return buffer


def generate_standings_pdf(tournament, round_number: Optional[int], standings):
    """Generate a professional PDF for tournament standings."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'StandingsTitle',
        parent=styles['Title'],
        fontSize=18,
        alignment=1,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        'StandingsSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=1,
        spaceAfter=12,
        textColor=colors.HexColor('#333333'),
    )
    small_style = ParagraphStyle(
        'SmallCenter',
        parent=styles['Normal'],
        fontSize=9,
        alignment=1,
        textColor=colors.HexColor('#666666'),
    )

    elements = []

    elements.append(Paragraph(tournament.name, title_style))
    elements.append(Paragraph(
        f"Standings - Round {round_number if round_number else 'Latest'}",
        subtitle_style
    ))
    elements.append(Paragraph(
        f"Date: {tournament.start_date.strftime('%B %d, %Y') if tournament.start_date else ''} | "
        f"Time Control: {tournament.time_control}",
        small_style
    ))
    elements.append(Spacer(1, 8 * mm))

    data = [
        ['Rank', 'Player', 'Rating', 'Points', 'Played', 'W', 'D', 'L', 'Buchholz', 'S-B']
    ]
    for standing in standings:
        data.append([
            str(standing.rank),
            standing.player.player_name,
            str(standing.player.rating) if standing.player.rating is not None else '',
            _format_decimal(standing.points, 1),
            str(standing.games_played),
            str(standing.wins),
            str(standing.draws),
            str(standing.losses),
            _format_decimal(standing.buchholz, 2),
            _format_decimal(standing.sonneborn_berger, 2),
        ])

    table = Table(
        data,
        colWidths=[14 * mm, 75 * mm, 20 * mm, 24 * mm, 18 * mm, 14 * mm, 14 * mm, 14 * mm, 28 * mm, 28 * mm],
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f8fc')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer
