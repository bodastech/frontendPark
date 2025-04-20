#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Test Script
--------------
This script demonstrates how to:
1. Send enhanced parking entry data to the API
2. Retrieve and display active tickets
"""

import requests
import json
import datetime
import time
import platform
import socket

# Configuration
API_BASE_URL = "http://127.0.0.1:8000"
ENTRY_API_URL = f"{API_BASE_URL}/api/process-entry/"
ACTIVE_TICKETS_API_URL = f"{API_BASE_URL}/api/get-active-tickets/"

def get_real_data():
    """Get real data from the database"""
    try:
        # Get data from the active tickets endpoint
        response = requests.get(ACTIVE_TICKETS_API_URL)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success' and data.get('tickets'):
                tickets = data['tickets']
                if tickets:
                    # Use the most recent ticket as a template
                    recent_ticket = tickets[0]
                    return {
                        'vehicle': {
                            'license_plate': recent_ticket.get('plat_no'),
                            'vehicle_type': recent_ticket.get('vehicle_type', 'CAR')
                        },
                        'spot': {
                            'location': 'Main Entrance',
                            'gate': 'MAIN'
                        },
                        'operator': 'System'
                    }
        return None
    except Exception as e:
        print(f"Error getting real data: {e}")
        return None

def send_enhanced_entry_data():
    """Send enhanced parking entry data using real data from database"""
    real_data = get_real_data()
    if not real_data:
        print("Could not get real data from database")
        return False
    
    vehicle = real_data['vehicle']
    spot = real_data['spot']
    operator = real_data['operator']
    
    # Get current weather (using a mock value since we don't have a weather API)
    weather = "SUNNY"  # This would be replaced with actual weather API integration
    
    # Get device information
    device_info = {
        "camera_id": f"CAM-{spot.get('id', '001')}",
        "location": spot.get('location', 'Main Entrance'),
        "hostname": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "os": platform.system(),
        "os_version": platform.version(),
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Prepare entry data using real data
    entry_data = {
        "plate_number": vehicle.get('license_plate'),
        "vehicle_type": vehicle.get('vehicle_type', 'CAR'),
        "confidence_score": 0.95,  # This would come from actual OCR confidence
        "entry_gate": spot.get('gate', 'MAIN'),
        "operator": operator,  # Using the operator string directly
        "weather_condition": weather,
        "entry_method": "AUTOMATIC",
        "device_info": device_info
    }
    
    print("\n=== Sending Enhanced Entry Data ===")
    print(f"API URL: {ENTRY_API_URL}")
    print(f"Plate Number: {vehicle.get('license_plate')}")
    print(f"Vehicle Type: {vehicle.get('vehicle_type', 'CAR')}")
    print(f"Entry Gate: {entry_data['entry_gate']}")
    print(f"Operator: {entry_data['operator']}")
    print(f"Weather: {weather}")
    print(f"Parking Spot: {spot.get('location', 'Not assigned')}")
    
    try:
        # Send data to API
        response = requests.post(
            ENTRY_API_URL,
            json=entry_data
        )
        
        print(f"\nAPI Response Status: {response.status_code}")
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            print("\n=== Entry Successful ===")
            print(f"Success: {result.get('success', False)}")
            print(f"Message: {result.get('message', 'No message')}")
            
            ticket = result.get('ticket', {})
            if ticket:
                print(f"\nTicket ID: {ticket.get('id')}")
                print(f"Plate: {ticket.get('plate_number')}")
                print(f"Entry Time: {ticket.get('entry_time')}")
                print(f"Vehicle Type: {ticket.get('vehicle_type')}")
                print(f"Is Regular: {ticket.get('is_regular', False)}")
                print(f"Visit Count: {ticket.get('visit_count', 1)}")
            
            return True
        else:
            print(f"\nError: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"Error sending entry data: {e}")
        return False

def get_active_tickets():
    """Get and display active tickets from the API"""
    
    print("\n=== Getting Active Tickets ===")
    print(f"API URL: {ACTIVE_TICKETS_API_URL}")
    
    try:
        # Get active tickets from API
        response = requests.get(ACTIVE_TICKETS_API_URL)
        
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success' and data.get('tickets'):
                tickets = data['tickets']
                stats = data.get('stats', {})
                
                print(f"\nTotal Active Tickets: {stats.get('total_active', len(tickets))}")
                print(f"Today's Entries: {stats.get('today_entries', 0)}")
                print(f"Long Duration (>4h): {stats.get('long_duration', 0)}")
                
                print("\n=== Active Tickets ===")
                for ticket in tickets:
                    print(f"\nID: {ticket.get('id')}")
                    print(f"Plate: {ticket.get('plat_no')}")
                    print(f"Entry Time: {ticket.get('date_masuk')}")
                    print(f"Vehicle Type: {ticket.get('vehicle_type')}")
                    print(f"Status: {ticket.get('status')}")
                    
                    # Print enhanced data if available
                    if 'confidence_score' in ticket:
                        print(f"Confidence Score: {ticket.get('confidence_score')}")
                    if 'entry_gate' in ticket:
                        print(f"Entry Gate: {ticket.get('entry_gate')}")
                    if 'operator' in ticket:
                        print(f"Operator: {ticket.get('operator')}")
                    if 'weather_condition' in ticket:
                        print(f"Weather: {ticket.get('weather_condition')}")
                    if 'entry_method' in ticket:
                        print(f"Entry Method: {ticket.get('entry_method')}")
                    if 'is_regular' in ticket:
                        print(f"Regular Visitor: {ticket.get('is_regular')}")
                    if 'visit_count' in ticket:
                        print(f"Visit Count: {ticket.get('visit_count')}")
                    
                    print("-" * 30)
                
                return True
            else:
                print(f"\nNo active tickets found or API error: {data}")
                return False
        else:
            print(f"\nError: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"Error getting active tickets: {e}")
        return False

def main():
    """Main function"""
    print("=" * 50)
    print("PARKING SYSTEM API TEST - VIEWING ACTIVE TICKETS")
    print("=" * 50)
    
    # Only get current active tickets
    print("\n[STEP 1] Getting current active tickets...")
    get_active_tickets()
    
    print("\n" + "=" * 50)
    print("VIEWING COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main()
