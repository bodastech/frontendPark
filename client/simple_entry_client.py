#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple Parking Entry Client
--------------------------
A simplified client for sending enhanced parking entry data
to the parking management system API without authentication.
"""

import os
import sys
import json
import time
import requests
import datetime
import uuid
import platform
import socket
import getpass

# Configuration
CONFIG = {
    "api_url": "http://127.0.0.1:8000/api/process-entry/",
    "camera_id": "CAM-001",
    "entry_gate": "MAIN",
    "default_vehicle_type": "CAR"
}

def get_device_info():
    """Collect information about the device running this client"""
    try:
        return {
            "camera_id": CONFIG["camera_id"],
            "location": CONFIG["entry_gate"],
            "hostname": socket.gethostname(),
            "ip_address": socket.gethostbyname(socket.gethostname()),
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "user": getpass.getuser(),
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error getting device info: {e}")
        return {
            "camera_id": CONFIG["camera_id"],
            "location": CONFIG["entry_gate"],
            "error": str(e)
        }

def manual_entry():
    """Interactive function for manual entry"""
    try:
        print("\n=== Manual Entry ===")
        plate_number = input("Enter license plate number: ")
        vehicle_types = ["CAR", "MOTORCYCLE", "TRUCK"]
        
        print("Vehicle types:")
        for i, vtype in enumerate(vehicle_types):
            print(f"{i+1}. {vtype}")
        
        vehicle_choice = int(input("Select vehicle type (1-3): "))
        vehicle_type = vehicle_types[vehicle_choice-1]
        
        operator = input("Operator name: ")
        weather = input("Weather condition (e.g., SUNNY, RAINY, CLOUDY): ")
        
        # Prepare entry data
        entry_data = {
            "plate_number": plate_number,
            "vehicle_type": vehicle_type,
            "confidence_score": 1.0,  # Manual entry has perfect confidence
            "image_path": None,  # No image for manual entry
            "entry_gate": CONFIG["entry_gate"],
            "operator": operator,
            "weather_condition": weather.upper(),
            "entry_method": "MANUAL",
            "device_info": get_device_info()
        }
        
        # Send data to API
        print(f"\nSending data to API: {CONFIG['api_url']}")
        print(json.dumps(entry_data, indent=2))
        
        response = requests.post(
            CONFIG["api_url"],
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
            
            print("\nEntry recorded successfully!")
        else:
            print(f"\nError: {response.status_code}")
            print(response.text)
                
    except Exception as e:
        print(f"Error in manual entry: {e}")

def main():
    """Main function to run the client"""
    print("Simple Parking Entry Client")
    print("---------------------------")
    print(f"API URL: {CONFIG['api_url']}")
    print(f"Entry Gate: {CONFIG['entry_gate']}")
    print("---------------------------")
    
    manual_entry()

if __name__ == "__main__":
    main()
