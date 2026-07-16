#!/usr/bin/env python3
"""
Simple test script to verify tournament form validation works correctly
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
from django.contrib.auth.models import User
from ttsaadmin.forms import TournamentForm
from ttsaadmin.views import tournament_create
from datetime import datetime, timedelta
import pytz

def test_tournament_form_validation():
    """Test the tournament form validation"""
    print("Testing tournament form validation...")
    
    # Create test data
    utc_now = datetime.now(pytz.UTC)
    start_date = utc_now + timedelta(days=7)
    end_date = start_date + timedelta(days=2)
    registration_deadline = start_date - timedelta(days=1)
    
    # Valid tournament data
    valid_data = {
        'name': 'Test Tournament 2024',
        'description': 'A test tournament for validation',
        'venue': 'Test Chess Club',
        'category': 'open',
        'format': 'swiss',
        'rounds': 7,
        'time_control': '90+30',
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'registration_deadline': registration_deadline.isoformat(),
        'entry_fee': 50.00,
        'max_players': 32,
        'status': 'draft',
        'is_active': True,
        'is_featured': False
    }
    
    # Test valid form
    form = TournamentForm(data=valid_data)
    if form.is_valid():
        print("✓ Valid tournament form passed validation")
    else:
        print("✗ Valid tournament form failed validation:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
        return False
    
    # Test invalid data - end date before start date
    invalid_data = valid_data.copy()
    invalid_data['end_date'] = (start_date - timedelta(days=1)).isoformat()
    
    form = TournamentForm(data=invalid_data)
    if not form.is_valid():
        print("✓ Invalid form (end date before start date) correctly failed validation")
    else:
        print("✗ Invalid form should have failed validation")
        return False
    
    # Test invalid data - registration deadline after start date
    invalid_data2 = valid_data.copy()
    invalid_data2['registration_deadline'] = (start_date + timedelta(days=1)).isoformat()
    
    form = TournamentForm(data=invalid_data2)
    if not form.is_valid():
        print("✓ Invalid form (registration deadline after start date) correctly failed validation")
    else:
        print("✗ Invalid form should have failed validation")
        return False
    
    print("All form validation tests passed!")
    return True

def test_tournament_create_view():
    """Test the tournament create view"""
    print("\nTesting tournament create view...")
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='testadmin',
        defaults={'email': 'test@example.com', 'is_staff': True}
    )
    
    # Create request factory
    factory = RequestFactory()
    
    # Create test data
    utc_now = datetime.now(pytz.UTC)
    start_date = utc_now + timedelta(days=7)
    end_date = start_date + timedelta(days=2)
    registration_deadline = start_date - timedelta(days=1)
    
    # Test POST request with valid data
    request_data = {
        'name': 'Test Tournament View',
        'description': 'A test tournament for view validation',
        'venue': 'Test Chess Club',
        'category': 'open',
        'format': 'swiss',
        'rounds': 7,
        'time_control': '90+30',
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'registration_deadline': registration_deadline.isoformat(),
        'entry_fee': 50.00,
        'max_players': 32,
        'status': 'draft',
        'is_active': True,
        'is_featured': False
    }
    
    request = factory.post('/ttsa-admin/tournaments/create/', request_data)
    request.user = user
    request.headers = {'X-Requested-With': 'XMLHttpRequest'}
    
    try:
        response = tournament_create(request)
        if response.status_code == 200:
            print("✓ Tournament create view returned valid response")
            return True
        else:
            print(f"✗ Tournament create view returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Tournament create view failed with error: {e}")
        return False

if __name__ == '__main__':
    print("Running tournament validation tests...\n")
    
    # Test form validation
    form_test_passed = test_tournament_form_validation()
    
    # Test view
    view_test_passed = test_tournament_create_view()
    
    if form_test_passed and view_test_passed:
        print("\n🎉 All tests passed! Tournament validation is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the issues above.")
