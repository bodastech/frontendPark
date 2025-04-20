#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parking Entry Client
-------------------
This script handles the capture and transmission of enhanced parking entry data
to the parking management system API.

Features:
- License plate recognition from camera feed
- Weather data integration
- Automatic/manual entry processing
- Regular visitor detection
- Enhanced data transmission to API
"""

import os
import sys
import json
import time
import argparse
import requests
import logging
import datetime
import cv2
import numpy as np
from pathlib import Path
import uuid
import platform
import socket
import getpass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("entry_client.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ParkingEntryClient")

# Configuration
CONFIG = {
    "api_url": "http://127.0.0.1:8000/api/process-entry/",
    "api_username": "admin",
    "api_password": "admin",
    "camera_id": "CAM-001",
    "entry_gate": "MAIN",
    "image_save_path": "captures",
    "weather_api_key": "",  # Add your weather API key here
    "weather_api_url": "https://api.openweathermap.org/data/2.5/weather",
    "default_vehicle_type": "CAR",
    "confidence_threshold": 0.7,
    "token": None,  # Will be set after authentication
}

class ParkingEntryClient:
    """Client for handling parking entry operations"""
    
    def __init__(self, config=None):
        """Initialize the client with configuration"""
        self.config = config or CONFIG
        self.session = requests.Session()
        if self.config.get("token"):
            self.session.headers.update({
                "Authorization": f"Bearer {self.config['token']}"
            })
        self.device_info = self._get_device_info()
        
    def _get_device_info(self):
        """Collect information about the device running this client"""
        try:
            return {
                "camera_id": self.config["camera_id"],
                "location": self.config["entry_gate"],
                "hostname": socket.gethostname(),
                "ip_address": socket.gethostbyname(socket.gethostname()),
                "os": platform.system(),
                "os_version": platform.version(),
                "python_version": platform.python_version(),
                "user": getpass.getuser(),
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return {
                "camera_id": self.config["camera_id"],
                "location": self.config["entry_gate"],
                "error": str(e)
            }
    
    def authenticate(self):
        """Authenticate with the API using session-based authentication"""
        try:
            # Check if we should use session-based authentication
            if self.config.get("use_session_auth", False):
                # Get CSRF token first
                csrf_response = self.session.get(self.config.get("auth_url", "http://127.0.0.1:8000/parking/login/"))
                
                # Extract CSRF token from the response
                csrf_token = None
                if 'csrftoken' in self.session.cookies:
                    csrf_token = self.session.cookies['csrftoken']
                
                # If we couldn't get a CSRF token, try to extract it from the response content
                if not csrf_token and 'name="csrfmiddlewaretoken"' in csrf_response.text:
                    import re
                    csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', csrf_response.text)
                    if csrf_match:
                        csrf_token = csrf_match.group(1)
                
                if not csrf_token:
                    logger.warning("Could not extract CSRF token, proceeding without it")
                
                # Prepare headers and data for login
                headers = {}
                if csrf_token:
                    headers['X-CSRFToken'] = csrf_token
                
                # Login with username and password
                login_data = {
                    "username": self.config["api_username"],
                    "password": self.config["api_password"]
                }
                
                if csrf_token:
                    login_data["csrfmiddlewaretoken"] = csrf_token
                
                login_response = self.session.post(
                    self.config.get("auth_url", "http://127.0.0.1:8000/parking/login/"),
                    data=login_data,
                    headers=headers,
                    allow_redirects=True
                )
                
                # Check if login was successful (usually by checking for a redirect or specific content)
                if login_response.status_code == 200 or login_response.status_code == 302:
                    logger.info("Session authentication successful")
                    return True
                else:
                    logger.error(f"Session authentication failed: {login_response.status_code} - {login_response.text}")
                    return False
            else:
                # JWT authentication (original method)
                response = requests.post(
                    "http://127.0.0.1:8000/api/token/",
                    data={
                        "username": self.config["api_username"],
                        "password": self.config["api_password"]
                    }
                )
                if response.status_code == 200:
                    token = response.json().get("access")
                    self.config["token"] = token
                    self.session.headers.update({
                        "Authorization": f"Bearer {token}"
                    })
                    logger.info("JWT authentication successful")
                    return True
                else:
                    logger.error(f"JWT authentication failed: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def capture_license_plate(self, camera_source=0):
        """
        Capture an image from the camera and perform license plate recognition
        
        Args:
            camera_source: Camera index or path to video file
            
        Returns:
            dict: Recognition results with plate number, confidence, and image path
        """
        try:
            # This is a simplified mock implementation
            # In a real system, you would use a proper OCR/ALPR library
            
            # Initialize camera
            logger.info(f"Initializing camera from source: {camera_source}")
            cap = cv2.VideoCapture(camera_source)
            if not cap.isOpened():
                logger.error("Failed to open camera")
                return None
            
            # Capture frame
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to capture image")
                cap.release()
                return None
            
            # Save image
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"capture_{timestamp}_{uuid.uuid4().hex[:6]}.jpg"
            
            # Create directory if it doesn't exist
            os.makedirs(self.config["image_save_path"], exist_ok=True)
            
            image_path = os.path.join(self.config["image_save_path"], image_filename)
            cv2.imwrite(image_path, frame)
            logger.info(f"Image saved to {image_path}")
            
            # Release camera
            cap.release()
            
            # Mock license plate recognition
            # In a real implementation, you would use a proper ALPR library here
            # For example: OpenALPR, Plate Recognizer, or a custom CNN model
            
            # For demo purposes, we'll generate a random plate number
            # Replace this with actual OCR/ALPR implementation
            plate_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            plate_numbers = "0123456789"
            
            mock_plate = "".join([
                plate_letters[np.random.randint(0, len(plate_letters))],
                plate_numbers[np.random.randint(0, len(plate_numbers))],
                plate_numbers[np.random.randint(0, len(plate_numbers))],
                plate_numbers[np.random.randint(0, len(plate_numbers))],
                plate_letters[np.random.randint(0, len(plate_letters))],
                plate_letters[np.random.randint(0, len(plate_letters))]
            ])
            
            confidence = np.random.uniform(0.7, 0.99)
            
            return {
                "plate_number": mock_plate,
                "confidence_score": confidence,
                "image_path": image_path
            }
            
        except Exception as e:
            logger.error(f"Error in license plate capture: {e}")
            return None
    
    def get_weather_data(self, lat=None, lon=None, city=None):
        """
        Get current weather data from OpenWeatherMap API
        
        Args:
            lat: Latitude (optional)
            lon: Longitude (optional)
            city: City name (optional)
            
        Returns:
            str: Weather condition (e.g., "SUNNY", "RAINY")
        """
        if not self.config.get("weather_api_key"):
            logger.warning("Weather API key not configured")
            return None
        
        try:
            params = {
                "appid": self.config["weather_api_key"],
            }
            
            if lat and lon:
                params["lat"] = lat
                params["lon"] = lon
            elif city:
                params["q"] = city
            else:
                # Default to Jakarta if no location specified
                params["q"] = "Jakarta,id"
            
            response = requests.get(self.config["weather_api_url"], params=params)
            
            if response.status_code == 200:
                data = response.json()
                weather_id = data["weather"][0]["id"]
                weather_main = data["weather"][0]["main"].upper()
                
                # Map OpenWeatherMap condition codes to simplified categories
                if weather_id >= 200 and weather_id < 300:
                    return "THUNDERSTORM"
                elif weather_id >= 300 and weather_id < 400:
                    return "DRIZZLE"
                elif weather_id >= 500 and weather_id < 600:
                    return "RAINY"
                elif weather_id >= 600 and weather_id < 700:
                    return "SNOW"
                elif weather_id >= 700 and weather_id < 800:
                    return "FOG"
                elif weather_id == 800:
                    return "CLEAR"
                elif weather_id > 800:
                    return "CLOUDY"
                else:
                    return weather_main
            else:
                logger.error(f"Weather API error: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")
            return None
    
    def process_entry(self, plate_data=None, manual_input=False, operator=None, vehicle_type=None):
        """
        Process a vehicle entry
        
        Args:
            plate_data: License plate data from recognition (optional)
            manual_input: Whether this is a manual entry
            operator: Name of the operator (for manual entries)
            vehicle_type: Type of vehicle (CAR, MOTORCYCLE, TRUCK)
            
        Returns:
            dict: API response data
        """
        try:
            entry_data = {}
            
            # Get plate data from camera if not provided
            if not plate_data and not manual_input:
                plate_data = self.capture_license_plate()
                if not plate_data:
                    logger.error("Failed to capture license plate")
                    return None
            
            # For manual input
            if manual_input:
                if not plate_data:
                    logger.error("Plate data required for manual input")
                    return None
                entry_method = "MANUAL"
            else:
                entry_method = "AUTOMATIC"
            
            # Get weather data
            weather_condition = self.get_weather_data()
            
            # Prepare entry data
            entry_data = {
                "plate_number": plate_data["plate_number"],
                "vehicle_type": vehicle_type or self.config["default_vehicle_type"],
                "confidence_score": plate_data.get("confidence_score"),
                "image_path": plate_data.get("image_path"),
                "entry_gate": self.config["entry_gate"],
                "operator": operator,
                "weather_condition": weather_condition,
                "entry_method": entry_method,
                "device_info": self.device_info
            }
            
            # Send data to API
            logger.info(f"Sending entry data to API: {entry_data}")
            response = self.session.post(
                self.config["api_url"],
                json=entry_data
            )
            
            if response.status_code == 200 or response.status_code == 201:
                logger.info("Entry processed successfully")
                return response.json()
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing entry: {e}")
            return None
    
    def manual_entry(self):
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
            
            plate_data = {
                "plate_number": plate_number,
                "confidence_score": 1.0,  # Manual entry has perfect confidence
                "image_path": None  # No image for manual entry
            }
            
            result = self.process_entry(
                plate_data=plate_data,
                manual_input=True,
                operator=operator,
                vehicle_type=vehicle_type
            )
            
            if result:
                print("\n=== Entry Successful ===")
                print(f"Ticket ID: {result['ticket']['id']}")
                print(f"Plate: {result['ticket']['plate_number']}")
                print(f"Entry Time: {result['ticket']['entry_time']}")
                print(f"Vehicle Type: {result['ticket']['vehicle_type']}")
                if result['ticket']['is_regular']:
                    print(f"Regular Visitor: Yes (Visit #{result['ticket']['visit_count']})")
                print("\nEntry recorded successfully!")
            else:
                print("\nError processing entry. Check logs for details.")
                
        except Exception as e:
            logger.error(f"Error in manual entry: {e}")
            print(f"Error: {e}")
    
    def auto_entry(self):
        """Automatic entry using camera"""
        try:
            print("\n=== Automatic Entry ===")
            print("Capturing license plate...")
            
            result = self.process_entry()
            
            if result:
                print("\n=== Entry Successful ===")
                print(f"Ticket ID: {result['ticket']['id']}")
                print(f"Plate: {result['ticket']['plate_number']}")
                print(f"Confidence: {result['ticket']['confidence_score']:.2f}")
                print(f"Entry Time: {result['ticket']['entry_time']}")
                print(f"Vehicle Type: {result['ticket']['vehicle_type']}")
                if result['ticket']['is_regular']:
                    print(f"Regular Visitor: Yes (Visit #{result['ticket']['visit_count']})")
                print("\nEntry recorded successfully!")
            else:
                print("\nError processing entry. Check logs for details.")
                
        except Exception as e:
            logger.error(f"Error in auto entry: {e}")
            print(f"Error: {e}")

def main():
    """Main function to run the client"""
    parser = argparse.ArgumentParser(description="Parking Entry Client")
    parser.add_argument("--manual", action="store_true", help="Use manual entry mode")
    parser.add_argument("--config", help="Path to config file")
    args = parser.parse_args()
    
    # Load config from file if provided
    config = CONFIG
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config.update(json.load(f))
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    client = ParkingEntryClient(config)
    
    # Authenticate
    if not client.authenticate():
        logger.error("Authentication failed. Exiting.")
        return
    
    if args.manual:
        client.manual_entry()
    else:
        client.auto_entry()

if __name__ == "__main__":
    main()
