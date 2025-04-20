import os
import sys
import django
import json
from django.db import connection

def show_real_tables():
    print("\n=== DATABASE TABLES ===")
    
    # Get all table names
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        print(f"\nFound {len(tables)} tables:")
        for table in tables:
            print(f"- {table[0]}")
        
        # Show data from captureticket table
        print("\n=== CAPTURETICKET TABLE DATA ===")
        cursor.execute("""
            SELECT * 
            FROM captureticket
            ORDER BY date_masuk DESC
            LIMIT 5
        """)
        
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        
        print("\nColumns:", columns)
        print("\nRecent Records:")
        for row in rows:
            record = dict(zip(columns, row))
            print("\nRecord:")
            for key, value in record.items():
                print(f"{key}: {value}")

if __name__ == "__main__":
    # Setup Django environment
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_management.parking.settings')
    django.setup()
    
    show_real_tables()
