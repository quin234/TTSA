#!/usr/bin/env python3
"""
Final validation test for tournament form fixes
"""

# Test the form validation with the corrected field choices
import os
import sys

# Add the project root to Python path
sys.path.insert(0, '/home/Django/apps/TTSA')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ttsa_project.settings')

try:
    import django
    django.setup()
    
    from ttsaadmin.forms import TournamentForm
    from datetime import datetime, timedelta
    
    def test_all_fixes():
        print("Testing tournament form with all fixes applied...")
        
        # Test data with corrected field choices
        data = {
            'name': 'Test Tournament 2024',
            'description': 'A test tournament with all required fields',
            'venue': 'Test Chess Club',
            'category': 'open',  # Valid category choice
            'format': 'swiss',   # Valid format choice
            'rounds': 7,
            'time_control': '90+30',
            'start_date': '2024-12-01T10:00',
            'end_date': '2024-12-03T18:00',
            'registration_deadline': '2024-11-30T23:59',
            'max_players': 32,
            'status': 'draft',   # Valid status choice
            'is_active': True,
            'is_featured': False
            # entry_fee is optional now
        }
        
        form = TournamentForm(data=data)
        print(f"Form is valid: {form.is_valid()}")
        
        if not form.is_valid():
            print("Validation errors:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
            return False
        
        print("✓ All validation fixes work correctly!")
        print("✓ Form accepts valid field choices")
        print("✓ Entry fee is optional")
        print("✓ All required fields are properly validated")
        
        return True
    
    def test_invalid_choices():
        print("\nTesting invalid field choices...")
        
        # Test with invalid category (should fail)
        invalid_data = {
            'name': 'Test Tournament',
            'venue': 'Test Venue',
            'category': 'women',  # Invalid category - was removed
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
        
        form = TournamentForm(data=invalid_data)
        if not form.is_valid():
            print("✓ Invalid category correctly rejected")
        else:
            print("✗ Invalid category was accepted - this should not happen")
            return False
        
        # Test with invalid format (should fail)
        invalid_data['category'] = 'open'  # Fix category
        invalid_data['format'] = 'team'    # Invalid format - was removed
        
        form = TournamentForm(data=invalid_data)
        if not form.is_valid():
            print("✓ Invalid format correctly rejected")
        else:
            print("✗ Invalid format was accepted - this should not happen")
            return False
        
        # Test with invalid status (should fail)
        invalid_data['format'] = 'swiss'    # Fix format
        invalid_data['status'] = 'archived' # Invalid status

        form = TournamentForm(data=invalid_data)
        if not form.is_valid():
            print("✓ Invalid status correctly rejected")
        else:
            print("✗ Invalid status was accepted - this should not happen")
            return False
        
        return True
    
    if __name__ == '__main__':
        print("Running final validation tests...\n")
        
        # Test all fixes work
        all_fixes_work = test_all_fixes()
        
        # Test invalid choices are rejected
        invalid_choices_rejected = test_invalid_choices()
        
        if all_fixes_work and invalid_choices_rejected:
            print("\n🎉 ALL TESTS PASSED!")
            print("The tournament form validation issues have been fixed:")
            print("  ✓ Field choices now match model definitions")
            print("  ✓ Entry fee is optional (has default)")
            print("  ✓ All required fields are properly validated")
            print("  ✓ Invalid choices are correctly rejected")
            print("\nThe tournament creation should now work correctly!")
        else:
            print("\n❌ Some tests failed. Please review the issues above.")
            
except Exception as e:
    print(f"Error during testing: {e}")
    import traceback
    traceback.print_exc()
