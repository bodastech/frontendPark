import os
import django
import random
import time
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_management.settings')
django.setup()

from parking.models import Captureticket

def generate_plate():
    areas = ['B', 'D', 'F', 'T', 'AB', 'AD', 'AE', 'AG']
    numbers = str(random.randint(1000, 9999))
    letters = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ', k=3))
    return f"{random.choice(areas)} {numbers} {letters}"

def main():
    total_entries = 1000  # We'll create 1000 entries
    entries_created = 0
    
    print(f"Starting to create {total_entries} vehicle entries...")
    
    while entries_created < total_entries:
        try:
            # Generate random entry time within the last 24 hours
            entry_time = datetime.now() - timedelta(hours=random.randint(0, 24))
            
            # Create the entry directly in the database
            ticket = Captureticket.objects.create(
                plat_no=generate_plate(),
                date_masuk=entry_time,
                status="MASUK"
            )
            
            entries_created += 1
            print(f"Created entry {entries_created}/{total_entries}: {ticket.plat_no}")
            
            # Every 50 entries, check current count
            if entries_created % 50 == 0:
                current_count = Captureticket.objects.count()
                print(f"\nCurrent total vehicles in database: {current_count}\n")
        
        except Exception as e:
            print(f"Error: {str(e)}")
            time.sleep(1)  # Wait longer if there's an error
            
    print("Finished creating entries!")
    final_count = Captureticket.objects.count()
    print(f"Final total vehicles in database: {final_count}")
    
if __name__ == "__main__":
    main() 