#!/usr/bin/env python3
"""
Test script for the new results system
"""

import os
import pandas as pd
from datetime import datetime
import uuid

# Test the new results system
def test_results_system():
    print("🧪 Testing new results system...")
    
    # Create test data for recent_results.csv
    results_folder = r'Database\results'
    recent_csv = os.path.join(results_folder, 'recent_results.csv')
    
    # Sample test data
    test_data = [
        {
            'result_id': f"eval_{uuid.uuid4().hex[:8]}",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_marks_obtained': 85,
            'total_max_marks': 100,
            'percentage': 85.0,
            'grade': 'A',
            'questions_count': 3,
            'student_id': 'STU001',
            'email': 'student1@example.com',
            'subject': 'Mathematics',
            'ai_used': 'Gemini AI',
            'hash_id': f"0x{uuid.uuid4().hex[:12].upper()}",
            'status': 'Completed'
        },
        {
            'result_id': f"eval_{uuid.uuid4().hex[:8]}",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_marks_obtained': 72,
            'total_max_marks': 100,
            'percentage': 72.0,
            'grade': 'B+',
            'questions_count': 3,
            'student_id': 'STU002',
            'email': 'student2@example.com',
            'subject': 'Science',
            'ai_used': 'Grok AI',
            'hash_id': f"0x{uuid.uuid4().hex[:12].upper()}",
            'status': 'Completed'
        }
    ]
    
    # Create the CSV file
    df = pd.DataFrame(test_data)
    df.to_csv(recent_csv, index=False)
    
    print(f"✅ Created test data in {recent_csv}")
    print(f"📊 Test data contains {len(test_data)} sample results")
    
    # Verify the file was created
    if os.path.exists(recent_csv):
        df_check = pd.read_csv(recent_csv)
        print(f"✅ Verification: CSV contains {len(df_check)} records")
        print("📋 Sample record:")
        print(f"   Student ID: {df_check.iloc[0]['student_id']}")
        print(f"   Grade: {df_check.iloc[0]['grade']}")
        print(f"   Status: {df_check.iloc[0]['status']}")
    else:
        print("❌ Error: CSV file was not created")
    
    print("🎉 Test completed!")

if __name__ == "__main__":
    test_results_system()