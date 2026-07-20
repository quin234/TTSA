#!/usr/bin/env python3
"""
Test script to verify tournament creation works correctly
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.append('/home/Django/apps/TTSA')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ttsa_project.settings')

# Setup Django
django.setup()

from django.test import RequestFactory
from ttsa_app.models import User
from ttsaadmin.forms import TournamentForm
from ttsaadmin.models import Tournament
from datetime import datetime, timedelta
from django.utils import timezone

def test_tournament_creation():
    """Test tournament creation with valid data"""
    print("Testing tournament creation...")
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='testadmin',
        defaults={'email': 'test@example.com', 'is_staff': True}
    )
    
    # Create test data
    utc_now = timezone.now()
    start_date = utc_now + timedelta(days=7)
    end_date = start_date + timedelta(days=2)
    registration_deadline = start_date - timedelta(days=1)
    
    # Valid tournament data
    tournament_data = {
        'name': 'Test Tournament 2024',
        'description': 'A test tournament for validation',
        'venue': 'Test Chess Club',
        'category': 'open',
        'format': 'swiss',
        'rounds': 7,
        'time_control': '90+30',
        'start_date': start_date.strftime('%Y-%m-%dT%H:%M'),
        'end_date': end_date.strftime('%Y-%m-%dT%H:%M'),
        'registration_deadline': registration_deadline.strftime('%Y-%m-%dT%H:%M'),
        'entry_fee': '50.00',
        'max_players': 32,
        'status': 'draft',
        'is_active': True,
        'is_featured': False
    }
    
    # Test form validation
    form = TournamentForm(data=tournament_data)
    print(f"Form is valid: {form.is_valid()}")
    
    if not form.is_valid():
        print("Form validation errors:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
        return False
    
    # Test saving to database
    try:
        tournament = form.save(commit=False)
        tournament.created_by = user
        tournament.save()
        
        print(f"✓ Tournament created successfully with ID: {tournament.id}")
        print(f"  Name: {tournament.name}")
        print(f"  Start Date: {tournament.start_date}")
        print(f"  End Date: {tournament.end_date}")
        print(f"  Registration Deadline: {tournament.registration_deadline}")
        
        # Clean up
        tournament.delete()
        print("✓ Test tournament deleted")
        
        return True
        
    except Exception as e:
        print(f"✗ Error saving tournament: {e}")
        return False

def test_tournament_form_edge_cases():
    """Test edge cases for tournament form"""
    print("\nTesting edge cases...")
    
    # Test with empty entry_fee
    data_without_entry_fee = {
        'name': 'Test Tournament No Fee',
        'description': 'Test tournament without entry fee',
        'venue': 'Test Chess Club',
        'category': 'open',
        'format': 'swiss',
        'rounds': 7,
        'time_control': '90+30',
        'start_date': '2024-12-01T10:00',
        'end_date': '2024-12-03T18:00',
        'registration_deadline': '2024-11-30T23:59',
        'max_players': 32,
        'status': 'draft',
        'is_active': True,
        'is_featured': False
    }
    
    form = TournamentForm(data=data_without_entry_fee)
    if form.is_valid():
        print("✓ Form validates without entry_fee")
        return True
    else:
        print("✗ Form failed validation without entry_fee:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
        return False

if __name__ == '__main__':
    print("Running tournament creation tests...\n")
    
    # Test basic creation
    basic_test_passed = test_tournament_creation()
    
    # Test edge cases
    edge_test_passed = test_tournament_form_edge_cases()
    
    if basic_test_passed and edge_test_passed:
        print("\n🎉 All tests passed! Tournament creation is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the issues above.")
