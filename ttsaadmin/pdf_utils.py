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
from reportlab.pdfgen import canvas

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
    elements.append(Paragraph("Creating Champions On And Off The Board", small_style))
    elements.append(Spacer(1, 1 * mm))
    elements.append(Paragraph("0799786754 / 0182858956 | ttsaacademy@gmail.com | ttsa.co.ke", small_style))
    elements.append(Spacer(1, 3 * mm))
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


def generate_player_statistics_pdf(player_data):
    """Generate a professional single-page A4 portrait PDF chess player profile for TTSA."""
    from reportlab.pdfgen import canvas as pdf_canvas_module
    
    buffer = io.BytesIO()
    page_width, page_height = A4
    
    # Create PDF canvas
    pdf_canvas = pdf_canvas_module.Canvas(buffer, pagesize=A4)
    
    # Colors
    black_color = colors.black
    blue_color = colors.HexColor('#2c5aa0')
    gray_color = colors.HexColor('#666666')
    
    # Margins
    left_margin = 15 * mm
    right_margin = 15 * mm
    top_margin = 15 * mm
    bottom_margin = 12 * mm
    
    y_pos = page_height - top_margin
    
    # Header section with logo and academy name
    logo_path = '/home/Django/apps/TTSA/static/images/logo.png'
    logo_width = 25 * mm
    logo_height = 25 * mm
    logo_x = left_margin
    logo_y = y_pos - 25 * mm
    
    try:
        pdf_canvas.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, mask='auto')
    except:
        # Fallback to placeholder if logo not found
        logo_radius = 12.5 * mm
        pdf_canvas.setFillColor(colors.HexColor('#f5f5f5'))
        pdf_canvas.circle(logo_x + logo_radius, logo_y + logo_radius, logo_radius, fill=1, stroke=0)
        pdf_canvas.setStrokeColor(black_color)
        pdf_canvas.setLineWidth(1)
        pdf_canvas.circle(logo_x + logo_radius, logo_y + logo_radius, logo_radius, fill=0, stroke=1)
        
        pdf_canvas.setFillColor(black_color)
        pdf_canvas.setFont("Helvetica-Bold", 10)
        text_width = pdf_canvas.stringWidth("TTSA", "Helvetica-Bold", 10)
        pdf_canvas.drawString(logo_x + logo_radius - text_width/2, logo_y + logo_radius - 4, "TTSA")
    
    # Academy name and tagline centered
    pdf_canvas.setFillColor(black_color)
    pdf_canvas.setFont("Helvetica-Bold", 14)
    header_text = "TAITA TAVETA SPORTS ACADEMY"
    text_width = pdf_canvas.stringWidth(header_text, "Helvetica-Bold", 14)
    pdf_canvas.drawString((page_width - text_width) / 2, y_pos - 10 * mm, header_text)

    y_pos -= 5 * mm
    pdf_canvas.setFont("Helvetica-Oblique", 9)
    tagline_text = "Creating Champions On And Off The Board"
    text_width = pdf_canvas.stringWidth(tagline_text, "Helvetica-Oblique", 9)
    pdf_canvas.drawString((page_width - text_width) / 2, y_pos - 10 * mm, tagline_text)

    # Contact information
    y_pos -= 5 * mm
    pdf_canvas.setFont("Helvetica", 8)
    pdf_canvas.setFillColor(gray_color)
    contact_text = "0799786754 / 0182858956 | ttsaacademy@gmail.com | ttsa.co.ke"
    text_width = pdf_canvas.stringWidth(contact_text, "Helvetica", 8)
    pdf_canvas.drawString((page_width - text_width) / 2, y_pos - 10 * mm, contact_text)

    y_pos -= 20 * mm
    pdf_canvas.setStrokeColor(black_color)
    pdf_canvas.setLineWidth(1)
    pdf_canvas.line(left_margin, y_pos, page_width - right_margin, y_pos)
    
    # Player name in header
    y_pos -= 15 * mm
    pdf_canvas.setFillColor(black_color)
    pdf_canvas.setFont("Helvetica-Bold", 16)
    player_name = player_data.get('player_name', 'N/A').upper()
    text_width = pdf_canvas.stringWidth(player_name, "Helvetica-Bold", 16)
    pdf_canvas.drawString((page_width - text_width) / 2, y_pos, player_name)
    
    # Player details in two columns
    y_pos -= 8 * mm
    pdf_canvas.setFont("Helvetica", 9)
    pdf_canvas.setFillColor(gray_color)
    
    col1_x = left_margin
    col2_x = page_width / 2 + 20 * mm
    
    pdf_canvas.drawString(col1_x, y_pos, f"Location: {player_data.get('location', 'N/A')}")
    pdf_canvas.drawString(col2_x, y_pos, f"Phone: {player_data.get('phone', 'N/A')}")
    
    y_pos -= 6 * mm
    pdf_canvas.drawString(col1_x, y_pos, f"Tournament: {player_data.get('tournament_name', 'N/A')}")
    
    # Key stats in two columns
    y_pos -= 12 * mm
    pdf_canvas.setFillColor(black_color)
    pdf_canvas.setFont("Helvetica-Bold", 10)
    pdf_canvas.drawString(left_margin, y_pos, "Key Statistics")
    
    y_pos -= 6 * mm
    pdf_canvas.setFont("Helvetica", 9)
    current_rating = player_data.get('current_rating', 'N/A')
    rating_change = player_data.get('rating_change', 0)
    total_tournaments = player_data.get('total_tournaments', 0)
    
    # Column 1 - Left side
    col1_x = left_margin
    stats_line1 = f"Current Rating: {current_rating}"
    pdf_canvas.drawString(col1_x, y_pos, stats_line1)
    
    y_pos -= 6 * mm
    stats_line2 = f"Rating Change: {rating_change:+}"
    pdf_canvas.drawString(col1_x, y_pos, stats_line2)
    
    y_pos -= 6 * mm
    stats_line3 = f"Total Tournaments: {total_tournaments}"
    pdf_canvas.drawString(col1_x, y_pos, stats_line3)
    
    # Win/Draw/Loss stats
    y_pos -= 8 * mm
    wins = player_data.get('wins', 0)
    draws = player_data.get('draws', 0)
    losses = player_data.get('losses', 0)
    total_games = wins + draws + losses
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    stats_line4 = f"Wins: {wins}"
    pdf_canvas.drawString(col1_x, y_pos, stats_line4)
    
    y_pos -= 6 * mm
    stats_line5 = f"Draws: {draws}"
    pdf_canvas.drawString(col1_x, y_pos, stats_line5)
    
    y_pos -= 6 * mm
    stats_line6 = f"Losses: {losses}"
    pdf_canvas.drawString(col1_x, y_pos, stats_line6)
    
    y_pos -= 6 * mm
    stats_line7 = f"Win Rate: {win_rate:.1f}%"
    pdf_canvas.drawString(col1_x, y_pos, stats_line7)
    
    # Column 2 - Opponents from current tournament
    y_pos_start_opponents = page_height - top_margin - 65 * mm
    col2_x = left_margin + 80 * mm
    
    pdf_canvas.setFillColor(black_color)
    pdf_canvas.setFont("Helvetica-Bold", 10)
    pdf_canvas.drawString(col2_x, y_pos_start_opponents, "Current Tournament Opponents")
    
    y_pos_start_opponents -= 5 * mm
    current_opponents = player_data.get('current_opponents', [])
    
    # Table header
    header_y = y_pos_start_opponents
    pdf_canvas.setFont("Helvetica-Bold", 8)
    col_widths_opp = [15 * mm, 45 * mm, 15 * mm]
    col_x_opp = col2_x
    headers_opp = ['Board', 'Opponent', 'Score']
    for i, header in enumerate(headers_opp):
        pdf_canvas.drawString(col_x_opp + 2 * mm, header_y, header)
        col_x_opp += col_widths_opp[i]
    
    y_pos_start_opponents -= 2 * mm
    pdf_canvas.setStrokeColor(black_color)
    pdf_canvas.setLineWidth(0.5)
    pdf_canvas.line(col2_x, y_pos_start_opponents, page_width - right_margin, y_pos_start_opponents)
    
    # Table rows
    y_pos_start_opponents -= 5 * mm
    row_height_opp = 5 * mm
    pdf_canvas.setFont("Helvetica", 8)
    
    for opponent in current_opponents:
        if y_pos_start_opponents - row_height_opp < bottom_margin + 50 * mm:
            break
        
        col_x_opp = col2_x
        
        # Board
        pdf_canvas.drawString(col_x_opp + 2 * mm, y_pos_start_opponents, str(opponent.get('board_number', 'N/A')))
        col_x_opp += col_widths_opp[0]
        
        # Opponent
        opponent_name = opponent.get('opponent_name', 'N/A').upper()[:20]
        pdf_canvas.drawString(col_x_opp + 2 * mm, y_pos_start_opponents, opponent_name)
        col_x_opp += col_widths_opp[1]
        
        # Score
        score = opponent.get('score', 'N/A')
        pdf_canvas.drawString(col_x_opp + 2 * mm, y_pos_start_opponents, str(score))
        
        y_pos_start_opponents -= row_height_opp
    
    # Current Tournament Information
    y_pos -= 15 * mm
    pdf_canvas.setFillColor(black_color)
    pdf_canvas.setFont("Helvetica-Bold", 10)
    pdf_canvas.drawString(left_margin, y_pos, "Current Tournament")
    
    y_pos -= 8 * mm
    pdf_canvas.setFont("Helvetica", 9)
    pdf_canvas.setFillColor(gray_color)
    
    current_tournament_name = player_data.get('tournament_name', 'N/A')
    current_rating = player_data.get('current_rating', 'N/A')
    current_round = player_data.get('current_round', 'N/A')
    current_position = player_data.get('current_position', 'N/A')
    total_players = player_data.get('total_players', 'N/A')
    
    tournament_info = f"Tournament: {current_tournament_name}   |   Rating: {current_rating}   |   Round: {current_round}   |   Position: {current_position}   |   Players: {total_players}"
    pdf_canvas.drawString(left_margin, y_pos, tournament_info)
    
    # Current Tournament Standings Table (Top 10)
    y_pos -= 12 * mm
    pdf_canvas.setFillColor(black_color)
    pdf_canvas.setFont("Helvetica-Bold", 10)
    pdf_canvas.drawString(left_margin, y_pos, "Tournament Standings (Top 10)")
    
    y_pos -= 5 * mm
    current_standings = player_data.get('current_standings', [])
    
    # Table header
    header_y = y_pos
    pdf_canvas.setFont("Helvetica-Bold", 8)
    col_widths = [12 * mm, 55 * mm, 20 * mm, 20 * mm, 20 * mm, 20 * mm]
    col_x = left_margin
    headers = ['Rank', 'Player', 'Rating', 'Points', 'Played', 'W-D-L']
    for i, header in enumerate(headers):
        pdf_canvas.drawString(col_x + 2 * mm, header_y, header)
        col_x += col_widths[i]
    
    y_pos -= 2 * mm
    pdf_canvas.setStrokeColor(black_color)
    pdf_canvas.setLineWidth(0.5)
    pdf_canvas.line(left_margin, y_pos, page_width - right_margin, y_pos)
    
    # Table rows
    y_pos -= 5 * mm
    row_height = 6 * mm
    pdf_canvas.setFont("Helvetica", 8)
    
    for standing in current_standings[:10]:
        if y_pos - row_height < bottom_margin + 50 * mm:
            break
        
        col_x = left_margin
        
        # Rank
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, str(standing.get('rank', 'N/A')))
        col_x += col_widths[0]
        
        # Player
        player_name_text = standing.get('player_name', 'N/A').upper()[:22]
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, player_name_text)
        col_x += col_widths[1]
        
        # Rating
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, str(standing.get('rating', 'N/A')))
        col_x += col_widths[2]
        
        # Points
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, str(standing.get('points', 'N/A')))
        col_x += col_widths[3]
        
        # Played
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, str(standing.get('played', 'N/A')))
        col_x += col_widths[4]
        
        # W-D-L
        wins = standing.get('wins', 0)
        draws = standing.get('draws', 0)
        losses = standing.get('losses', 0)
        wdl_text = f"{wins}-{draws}-{losses}"
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, wdl_text)
        
        y_pos -= row_height
    
    # Recent Tournaments table
    y_pos -= 12 * mm
    pdf_canvas.setFillColor(black_color)
    pdf_canvas.setFont("Helvetica-Bold", 10)
    pdf_canvas.drawString(left_margin, y_pos, "Recent Tournaments")
    
    y_pos -= 5 * mm
    all_tournaments = player_data.get('all_tournaments', [])
    
    # Table header
    header_y = y_pos
    pdf_canvas.setFont("Helvetica-Bold", 9)
    col_widths = [30 * mm, 60 * mm, 40 * mm, 25 * mm, 25 * mm]
    col_x = left_margin
    headers = ['Date', 'Tournament', 'Location', 'Position', 'Rating']
    for i, header in enumerate(headers):
        pdf_canvas.drawString(col_x + 2 * mm, header_y, header)
        col_x += col_widths[i]
    
    y_pos -= 2 * mm
    pdf_canvas.setStrokeColor(black_color)
    pdf_canvas.setLineWidth(0.5)
    pdf_canvas.line(left_margin, y_pos, page_width - right_margin, y_pos)
    
    # Table rows
    y_pos -= 5 * mm
    row_height = 7 * mm
    pdf_canvas.setFont("Helvetica", 9)
    
    for idx, tournament in enumerate(all_tournaments[:8]):
        if y_pos - row_height < bottom_margin + 10 * mm:
            break
        
        col_x = left_margin
        
        # Date
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, tournament.get('date', 'N/A')[:10])
        col_x += col_widths[0]
        
        # Tournament
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, tournament.get('name', 'N/A')[:35])
        col_x += col_widths[1]
        
        # Location
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, tournament.get('location', 'N/A')[:20])
        col_x += col_widths[2]
        
        # Position
        position = tournament.get('position', 'N/A')
        if position and position <= 3:
            pdf_canvas.setFillColor(blue_color)
            position_text = f"{position}{'st' if position == 1 else 'nd' if position == 2 else 'rd'}"
        else:
            pdf_canvas.setFillColor(black_color)
            position_text = str(position) if position else 'N/A'
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, position_text)
        col_x += col_widths[3]
        
        # Rating
        pdf_canvas.setFillColor(black_color)
        pdf_canvas.drawString(col_x + 2 * mm, y_pos, str(tournament.get('rating_after', 'N/A')))
        
        y_pos -= row_height
    
    # Footer
    footer_y = bottom_margin + 5 * mm
    pdf_canvas.setFillColor(gray_color)
    pdf_canvas.setFont("Helvetica", 7)
    footer_text = "Creating Champions On And Off The Board"
    text_width = pdf_canvas.stringWidth(footer_text, "Helvetica", 7)
    pdf_canvas.drawString((page_width - text_width) / 2, footer_y, footer_text)
    
    pdf_canvas.save()
    buffer.seek(0)
    return buffer


def generate_bulk_player_statistics_pdf(players_data):
    """Generate a multi-page PDF with player statistics for multiple players."""
    from PyPDF2 import PdfReader, PdfWriter
    
    writer = PdfWriter()
    
    for player_data in players_data:
        player_buffer = generate_player_statistics_pdf(player_data)
        player_buffer.seek(0)
        reader = PdfReader(player_buffer)
        for page in reader.pages:
            writer.add_page(page)
    
    output_buffer = io.BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer
