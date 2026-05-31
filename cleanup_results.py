#!/usr/bin/env python3
"""
Results Cleanup Script
Clean up old result files and keep only recent data
"""

import os
import pandas as pd
from datetime import datetime

# Directory paths
RESULTS_FOLDER = r'Database\results'

def cleanup_old_results():
    """Clean up old result files and keep only recent data"""
    try:
        print("🧹 Starting cleanup of old results...")
        
        # Remove old result text files (keep only last 5)
        result_files = []
        for filename in os.listdir(RESULTS_FOLDER):
            if filename.startswith('result_') and filename.endswith('.txt'):
                filepath = os.path.join(RESULTS_FOLDER, filename)
                result_files.append((filepath, os.path.getctime(filepath)))
        
        print(f"Found {len(result_files)} result files")
        
        # Sort by creation time (newest first)
        result_files.sort(key=lambda x: x[1], reverse=True)
        
        # Remove old files (keep only last 5)
        removed_count = 0
        for filepath, _ in result_files[5:]:
            try:
                os.remove(filepath)
                print(f"✅ Removed old result file: {os.path.basename(filepath)}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Error removing file {filepath}: {e}")
        
        print(f"Removed {removed_count} old result files")
        
        # Clean up old CSV data - keep only recent results
        old_csv = os.path.join(RESULTS_FOLDER, 'evaluation_results.csv')
        new_csv = os.path.join(RESULTS_FOLDER, 'recent_results.csv')
        
        if os.path.exists(old_csv):
            try:
                df = pd.read_csv(old_csv)
                print(f"Found {len(df)} records in old CSV")
                
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp', ascending=False)
                    # Keep only last 10 records
                    df = df.head(10)
                    df.to_csv(new_csv, index=False)
                    print(f"✅ Saved {len(df)} recent records to new CSV")
                
                # Remove old CSV file
                os.remove(old_csv)
                print("✅ Removed old evaluation_results.csv")
            except Exception as e:
                print(f"❌ Error cleaning up CSV: {e}")
        else:
            print("No old CSV file found")
        
        print("🎉 Cleanup completed successfully!")
                
    except Exception as e:
        print(f"❌ Error in cleanup_old_results: {e}")

if __name__ == "__main__":
    cleanup_old_results()