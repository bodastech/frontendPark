import os
import sys
import django
import json

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_management.parking.settings')
django.setup()

from django.db import connection

def show_real_records():
    print("\n=== REAL DATABASE RECORDS ===")
    
    with connection.cursor() as cursor:
        # Get all fields from captureticket table
        cursor.execute("""
            SELECT * 
            FROM captureticket
            WHERE date_masuk IS NOT NULL
            ORDER BY date_masuk DESC
            LIMIT 10
        """)
        
        # Get column names
        columns = [col[0] for col in cursor.description]
        
        # Get rows
        rows = cursor.fetchall()
        
        print(f"\nFound {len(rows)} records")
        
        # Print column headers
        print("\nColumn Names:")
        print("-" * 50)
        for col in columns:
            print(f"{col}")
        
        print("\n\nSample Records:")
        print("-" * 50)
        
        # Print each record with all fields
        for i, row in enumerate(rows, 1):
            print(f"\nRecord {i}")
            print("-" * 50)
            record = dict(zip(columns, row))
            for key, value in record.items():
                if value is not None:
                    print(f"{key}: {value}")
            print("" * 2)

if __name__ == "__main__":
    show_real_records()
