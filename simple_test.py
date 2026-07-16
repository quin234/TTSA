#!/usr/bin/env python3
"""
Simple test to check tournament form validation
"""

# Test the form validation directly
import os
import sys

# Add the project root to Python path
sys.path.insert(0, '/home/Django/apps/TTSA')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ttsa_project.settings')

import django
django.setup()

from ttsaadmin.forms import TournamentForm
from datetime import datetime, timedelta

def test_form():
    print("Testing TournamentForm validation...")
    
    # Test data that should work
    data = {
        'name': 'Test Tournament',
        'description': 'Test description',
        'venue': 'Test venue',
        'category': 'open',
        'format': 'swiss',
        'rounds': 7,
        'time_control': '90+30',
        'start_date': '2024-12-01T10:00',
        'end_date': '2024-12-03T18:00',
        'registration_deadline': '2024-11-30T23:59',
        'entry_fee': '50.00',
        'max_players': 32,
        'status': 'draft',
        'is_active': True,
        'is_featured': False
    }
    
    form = TournamentForm(data=data)
    print(f"Form is valid: {form.is_valid()}")
    
    if not form.is_valid():
        print("Validation errors:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
        return False
    
    print("✓ Form validation passed!")
    return True

if __name__ == '__main__':
    try:
        success = test_form()
        if success:
            print("Form validation is working correctly!")
        else:
            print("Form validation still has issues.")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
