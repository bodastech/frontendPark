import os
import sys
import django
from django.db import connection

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_management.parking_management.settings')
django.setup()

def check_table_structure():
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'captureticket'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            
            print("\nTable structure for 'captureticket':")
            print("Column Name | Data Type | Max Length")
            print("-" * 40)
            for col in columns:
                print(f"{col[0]:<11} | {col[1]:<9} | {col[2] if col[2] else 'N/A'}")
            
            # Get a sample row
            cursor.execute("SELECT * FROM captureticket LIMIT 1;")
            sample = cursor.fetchone()
            if sample:
                print("\nSample row:")
                print(sample)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_table_structure()
