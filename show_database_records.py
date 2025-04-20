import requests

def get_jwt_token():
    # Replace with your actual credentials
    auth_data = {
        'username': 'admin',  # Replace with your username
        'password': 'admin123'  # Replace with your password
    }
    response = requests.post('http://127.0.0.1:8000/api/token/', data=auth_data)
    if response.status_code == 200:
        return response.json().get('access')
    return None

def show_records():
    # Get JWT token
    token = get_jwt_token()
    if not token:
        print("Error: Could not get authentication token")
        return

    # Get data from API with authentication
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get('http://127.0.0.1:8000/api/get-active-tickets/', headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        tickets = data.get('tickets', [])
        stats = data.get('stats', {})
        
        # Print statistics
        print("\n=== PARKING STATISTICS ===")
        print(f"Total Active Tickets: {stats.get('total_active', 0)}")
        print(f"Today's Entries: {stats.get('today_entries', 0)}")
        print(f"Long Duration (>4h): {stats.get('long_duration', 0)}")
        print("-" * 50)
        
        # Print headers
        print("\n=== ACTIVE TICKETS ===")
        print("\nID | Plate No | Entry Time | Status | Vehicle Type | Gate | Operator | Weather | Method")
        print("-" * 120)
        
        # Print each ticket
        for ticket in tickets:
            print(f"{ticket.get('id')} | {ticket.get('plat_no')} | {ticket.get('date_masuk')} | {ticket.get('status')} | {ticket.get('vehicle_type')} | {ticket.get('entry_gate')} | {ticket.get('operator')} | {ticket.get('weather_condition')} | {ticket.get('entry_method')}")
    else:
        print(f"Error: {response.status_code}")

if __name__ == "__main__":
    show_records()
