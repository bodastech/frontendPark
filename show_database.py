import os
import sys
import requests
import json
from datetime import datetime

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_management.parking.settings')

def show_database_data():
    print("\n=== PARKING SYSTEM DATA ===")
    print(f"\nCurrent Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get data from API
    response = requests.get('http://127.0.0.1:8000/api/get-active-tickets/')
    
    if response.status_code == 200:
        data = response.json()
        
        # Print statistics
        print("\n=== Statistics ===")
        stats = data.get('stats', {})
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # Print tickets
        print("\n=== Active Tickets ===")
        tickets = data.get('tickets', [])
        print(f"Total Active Tickets: {len(tickets)}")
        
        for i, ticket in enumerate(tickets, 1):
            print(f"\nTicket {i}")
            print("-" * 50)
            for key, value in ticket.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    print(f"{key}: {value}")
            print("" * 2)
    else:
        print(f"Error fetching data: {response.status_code}")

if __name__ == "__main__":
    show_database_data()
