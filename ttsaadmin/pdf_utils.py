import io
from decimal import Decimal
from typing import List, Optional
from django.conf import settings
import os
from functools import lru_cache

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

# Cache for template images to avoid repeated file I/O
_template_merit_cache = None
_template_merit_path = None
_template_participation_cache = None
_template_participation_path = None

def get_merit_template():
    """Load and cache the certificate of merit template image."""
    global _template_merit_cache, _template_merit_path
    
    template_path = os.path.join(settings.BASE_DIR, 'certificateofmerit.jpg')
    
    # Return cached image if path hasn't changed
    if _template_merit_path == template_path and _template_merit_cache is not None:
        return _template_merit_cache, template_path
    
    # Load new image
    if os.path.exists(template_path):
        try:
            from reportlab.lib.utils import ImageReader
            _template_merit_cache = ImageReader(template_path)
            _template_merit_path = template_path
            return _template_merit_cache, template_path
        except:
            pass
    
    return None, template_path

def get_participation_template():
    """Load and cache the certificate of participation template image."""
    global _template_participation_cache, _template_participation_path
    
    template_path = os.path.join(settings.BASE_DIR, 'certificateofperticipation.jpg')
    
    # Return cached image if path hasn't changed
    if _template_participation_path == template_path and _template_participation_cache is not None:
        return _template_participation_cache, template_path
    
    # Load new image
    if os.path.exists(template_path):
        try:
            from reportlab.lib.utils import ImageReader
            _template_participation_cache = ImageReader(template_path)
            _template_participation_path = template_path
            return _template_participation_cache, template_path
        except:
            pass
    
    return None, template_path


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


def _generate_single_certificate(tournament, player, position=None):
    """Generate certificate using appropriate template based on position (top 3 get merit, rest get participation)."""
    from reportlab.pdfgen import canvas as pdf_canvas_module
    
    buffer = io.BytesIO()
    page_width, page_height = landscape(A4)
    
    # Create PDF canvas
    pdf_canvas = pdf_canvas_module.Canvas(buffer, pagesize=landscape(A4))
    
    # Determine if this is a top 3 player
    is_top_3 = position is not None and position <= 3
    
    # Get appropriate template
    if is_top_3:
        template, template_path = get_merit_template()
    else:
        template, template_path = get_participation_template()
    
    # Draw template as background
    if template:
        try:
            pdf_canvas.drawImage(template_path, 0, 0, width=page_width, height=page_height, mask='auto')
        except:
            pdf_canvas.setFillColorRGB(1, 1, 1)
            pdf_canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
    else:
        pdf_canvas.setFillColorRGB(1, 1, 1)
        pdf_canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
    
    # Player name in uppercase
    player_name_upper = player.player_name.upper()
    pdf_canvas.setFont("Times-Bold", 28)
    pdf_canvas.setFillColor(colors.black)
    name_width = pdf_canvas.stringWidth(player_name_upper, "Times-Bold", 28)
    
    if is_top_3:
        # Top 3 players: merit certificate with name and position
        # Draw player name first at 120mm from top, centered
        pdf_canvas.setFont("Times-Bold", 28)
        name_width = pdf_canvas.stringWidth(player_name_upper, "Times-Bold", 28)
        name_x = (page_width - name_width) / 2
        name_y = page_height - 120 * mm
        pdf_canvas.drawString(name_x, name_y, player_name_upper)
        
        # Draw position text below player name (20mm below name), centered
        position_text = f"{position}{('st' if position == 1 else 'nd' if position == 2 else 'rd')} Position"
        pdf_canvas.setFont("Times-Bold", 24)
        pdf_canvas.setFillColor(colors.black)
        position_width = pdf_canvas.stringWidth(position_text, "Times-Bold", 24)
        position_x = (page_width - position_width) / 2 + 35* mm
        position_y = name_y - 15 * mm
        pdf_canvas.drawString(position_x, position_y, position_text)
        
        # Draw venue at original position (38mm below original name position = 158mm from top)
        venue_text = tournament.venue.upper()
        pdf_canvas.setFont("Times-Bold", 20)
        pdf_canvas.setFillColor(colors.black)
        venue_width = pdf_canvas.stringWidth(venue_text, "Times-Bold", 20)
        venue_x = (page_width - venue_width) / 2 + 10 * mm
        venue_y = page_height - 158 * mm
        pdf_canvas.drawString(venue_x, venue_y, venue_text)
    else:
        # Rest of players: participation certificate with name and tournament venue
        # Draw player name - same Y position as merit certificate (120mm from top), centered
        name_x = (page_width - name_width) / 2
        name_y = page_height - 120 * mm
        pdf_canvas.drawString(name_x, name_y, player_name_upper)
        
        # Draw tournament venue/location - 38mm below name, 10mm to the right
        venue_text = tournament.venue.upper()
        pdf_canvas.setFont("Times-Bold", 20)
        pdf_canvas.setFillColor(colors.black)
        venue_width = pdf_canvas.stringWidth(venue_text, "Times-Bold", 20)
        venue_x = (page_width - venue_width) / 2 + 10 * mm
        venue_y = name_y - 38 * mm
        pdf_canvas.drawString(venue_x, venue_y, venue_text)
    
    pdf_canvas.save()
    buffer.seek(0)
    return buffer


def generate_bulk_certificates_pdf(tournament, players):
    """Generate a multi-page PDF with all participant certificates using different templates for top 3 and rest."""
    from reportlab.pdfgen import canvas as pdf_canvas_module
    
    # Sort players by rank (top 3 get merit certificates)
    sorted_players = sorted(players, key=lambda p: (p.rank or float('inf'), -p.points, -p.buchholz, p.player_name))
    
    buffer = io.BytesIO()
    page_width, page_height = landscape(A4)
    
    # Create PDF canvas
    pdf_canvas = pdf_canvas_module.Canvas(buffer, pagesize=landscape(A4))
    
    # Get cached template images
    merit_template, merit_path = get_merit_template()
    participation_template, participation_path = get_participation_template()
    
    # Generate certificate for each player (skip first 3 - they get merit certificates separately)
    for idx, player in enumerate(sorted_players[3:]):
        # Add page break if not first page
        if idx > 0:
            pdf_canvas.showPage()
        
        # Use participation template for all remaining players
        template = participation_template
        template_path = participation_path
        
        # Draw template as background
        if template:
            try:
                pdf_canvas.drawImage(template_path, 0, 0, width=page_width, height=page_height, mask='auto')
            except:
                pdf_canvas.setFillColorRGB(1, 1, 1)
                pdf_canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        else:
            pdf_canvas.setFillColorRGB(1, 1, 1)
            pdf_canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        
        # Player name in uppercase - centered
        player_name_upper = player.player_name.upper()
        pdf_canvas.setFont("Times-Bold", 28)
        pdf_canvas.setFillColor(colors.black)
        name_width = pdf_canvas.stringWidth(player_name_upper, "Times-Bold", 28)
        
        # Draw player name - same Y position as merit certificate (120mm from top), centered
        name_x = (page_width - name_width) / 2
        name_y = page_height - 120 * mm
        pdf_canvas.drawString(name_x, name_y, player_name_upper)
        
        # Draw tournament venue/location - 38mm below name, 10mm to the right
        venue_text = tournament.venue.upper()
        pdf_canvas.setFont("Times-Bold", 20)
        pdf_canvas.setFillColor(colors.black)
        venue_width = pdf_canvas.stringWidth(venue_text, "Times-Bold", 20)
        venue_x = (page_width - venue_width) / 2 + 10 * mm
        venue_y = name_y - 38 * mm
        pdf_canvas.drawString(venue_x, venue_y, venue_text)
    
    pdf_canvas.save()
    buffer.seek(0)
    return buffer
