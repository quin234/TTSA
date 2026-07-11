"""
Django management command to start Stockfish engine
"""

from django.core.management.base import BaseCommand
from ttsa_app.stockfish_service import stockfish_service


class Command(BaseCommand):
    help = 'Start the Stockfish chess engine'

    def handle(self, *args, **options):
        self.stdout.write('Starting Stockfish engine...')
        
        if stockfish_service.is_engine_available():
            if stockfish_service.start_engine():
                self.stdout.write(self.style.SUCCESS('Stockfish engine started successfully'))
            else:
                self.stdout.write(self.style.ERROR('Failed to start Stockfish engine'))
        else:
            self.stdout.write(self.style.WARNING('Stockfish engine not available - executable not found'))
