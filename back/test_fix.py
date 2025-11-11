#!/usr/bin/env python3
"""
Simple test script to verify the NFC scan fix works correctly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import process_nfc_scan
from sqlmodel import Session, select
from main import engine, Student

def test_process_nfc_scan_with_invalid_tag():
    """Test process_nfc_scan with an invalid tag ID"""
    print("Testing process_nfc_scan with invalid tag ID...")
    
    # This should not crash and should print a message about no student found
    try:
        process_nfc_scan("invalid_tag_id")
        print("✓ Test passed: No crash with invalid tag ID")
        return True
    except Exception as e:
        print(f"✗ Test failed: {repr(e)}")
        return False

def test_process_nfc_scan_with_valid_tag():
    """Test process_nfc_scan with a valid tag ID"""
    print("Testing process_nfc_scan with valid tag ID...")
    
    # Create a test student first
    with Session(engine) as session:
        test_student = Student(
            name="Test Student",
            tid="test_tag_id",
            lastscan=0,
            in_school=False,
            schoolclass="Test Class"
        )
        session.add(test_student)
        session.commit()
        session.refresh(test_student)
        
        # Test with valid tag
        try:
            process_nfc_scan("test_tag_id")
            print("✓ Test passed: No crash with valid tag ID")
            
            # Verify the student's status was flipped
            updated_student = session.exec(select(Student).where(Student.id == test_student.id)).first()
            if updated_student.in_school == True:
                print("✓ Test passed: Student status was correctly flipped")
                return True
            else:
                print("✗ Test failed: Student status was not flipped")
                return False
                
        except Exception as e:
            print(f"✗ Test failed: {repr(e)}")
            return False
        finally:
            # Clean up
            session.delete(test_student)
            session.commit()

if __name__ == "__main__":
    print("Running NFC scan fix tests...")
    print("=" * 50)
    
    test1_result = test_process_nfc_scan_with_invalid_tag()
    print()
    test2_result = test_process_nfc_scan_with_valid_tag()
    
    print()
    print("=" * 50)
    if test1_result and test2_result:
        print("✓ All tests passed! The fix is working correctly.")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Please check the implementation.")
        sys.exit(1)