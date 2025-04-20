# Parking Entry Client

This client application captures enhanced parking entry data and sends it to the parking management system API.

## Features

- License plate recognition from camera feed
- Weather data integration
- Automatic/manual entry processing
- Regular visitor detection
- Enhanced data transmission to API

## Installation

1. Install Python 3.7 or higher
2. Install required packages:

```bash
pip install -r requirements.txt
```

3. Configure the client by editing `config.json`

## Configuration

Edit `config.json` to set the following:

- `api_url`: URL of the parking management API
- `api_username` and `api_password`: Credentials for API authentication
- `camera_id`: Identifier for the camera
- `entry_gate`: Identifier for the entry gate (e.g., "MAIN", "SIDE", "VIP")
- `image_save_path`: Directory to save captured images
- `weather_api_key`: OpenWeatherMap API key (optional)
- `default_vehicle_type`: Default vehicle type if not specified

## Usage

### Automatic Mode

Run the client in automatic mode to capture license plates using the camera:

```bash
python entry_client.py
```

### Manual Mode

Run the client in manual mode to enter license plates manually:

```bash
python entry_client.py --manual
```

### Custom Configuration

Specify a custom configuration file:

```bash
python entry_client.py --config custom_config.json
```

## Data Sent to API

The client sends the following enhanced data to the API:

```json
{
  "plate_number": "B1234CD",
  "vehicle_type": "CAR",
  "confidence_score": 0.95,
  "image_path": "/path/to/image.jpg",
  "entry_gate": "MAIN",
  "operator": "operator_name",
  "weather_condition": "SUNNY",
  "entry_method": "AUTOMATIC",
  "device_info": {
    "camera_id": "CAM-001",
    "location": "Main Entrance",
    "hostname": "entry-gate-pc",
    "ip_address": "192.168.1.100",
    "os": "Windows",
    "os_version": "10.0.19044",
    "python_version": "3.9.7",
    "user": "operator",
    "timestamp": "2025-04-16T20:15:30.123456"
  }
}
```

## Troubleshooting

- Check `entry_client.log` for detailed error messages
- Ensure the API server is running and accessible
- Verify camera connection and permissions
- Check API credentials in the configuration
