import requests

def show_records():
    # Get data from API
    response = requests.get('http://127.0.0.1:8000/api/get-active-tickets/')
    
    if response.status_code == 200:
        data = response.json()
        tickets = data.get('tickets', [])
        
        # Print headers
        print("ID | Plate No | Vehicle Type | Entry Time | Status")
        print("-" * 50)
        
        # Print each ticket
        for ticket in tickets:
            print(f"{ticket.get('id')} | {ticket.get('plat_no')} | {ticket.get('vehicle_type')} | {ticket.get('date_masuk')} | {ticket.get('status')}")
    else:
        print(f"Error: {response.status_code}")

if __name__ == "__main__":
    show_records()
