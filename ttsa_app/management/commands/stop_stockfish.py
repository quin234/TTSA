"""
Django management command to stop Stockfish engine
"""

from django.core.management.base import BaseCommand
from ttsa_app.stockfish_service import stockfish_service


class Command(BaseCommand):
    help = 'Stop the Stockfish chess engine'

    def handle(self, *args, **options):
        self.stdout.write('Stopping Stockfish engine...')
        
        stockfish_service.stop_engine()
        self.stdout.write(self.style.SUCCESS('Stockfish engine stopped'))
