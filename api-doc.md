# API Documentation - Sistem Parkir RSI BNA

## Base URL
- Production: `https://your-domain.com/api/`
- Development: `http://localhost:8000/api/`

## Authentication
All endpoints require authentication. Use JWT token in Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

## Error Responses
All endpoints return standardized error responses:
```json
{
    "success": false,
    "message": "Error description",
    "errors": {
        "field_name": ["error message"]
    }
}
```

## Endpoints

### 1. Vehicle Management

#### Get Vehicle List
```
GET /api/vehicles/
```
- Returns list of all registered vehicles
- Response:
```json
{
    "success": true,
    "vehicles": [
        {
            "id": 1,
            "license_plate": "B 1234 CD",
            "vehicle_type": "CAR",
            "owner_name": "John Doe",
            "owner_contact": "08123456789"
        }
    ]
}
```

#### Create Vehicle
```
POST /api/vehicles/
```
- Required fields: license_plate, vehicle_type, owner_name, owner_contact
- Response:
```json
{
    "success": true,
    "message": "Vehicle created successfully",
    "vehicle": {
        "id": 1,
        "license_plate": "B 1234 CD"
    }
}
```

### 2. Parking Entry

#### Process Entry (Enhanced)
```
POST /api/process-entry/
```
- Required fields: plate_number, vehicle_type
- Optional fields: image_path, confidence_score, entry_gate, operator, weather_condition, entry_method, device_info
- Response:
```json
{
    "success": true,
    "message": "Entry processed successfully",
    "ticket": {
        "id": 1,
        "plate_number": "B 1234 CD",
        "entry_time": "2025-04-16T16:49:42+07:00",
        "vehicle_type": "CAR",
        "status": "MASUK",
        "image_path": "/media/captures/2025-04-16/B1234CD_20250416164942.jpg",
        "confidence_score": 0.95,
        "entry_gate": "MAIN",
        "operator": "operator1",
        "weather_condition": "SUNNY",
        "is_regular": true,
        "visit_count": 5,
        "entry_method": "AUTOMATIC",
        "device_info": {
            "camera_id": "CAM-001",
            "location": "Main Entrance",
            "firmware": "v2.1.3",
            "resolution": "1280x720"
        }
    }
}
```

### 3. Parking Exit

#### Process Exit
```
POST /api/process-exit/
```
- Required fields: ticket_number
- Response:
```json
{
    "success": true,
    "message": "Exit processed successfully",
    "data": {
        "fee": 6000,
        "duration": 1.5,
        "entry_time": "2025-04-16T16:49:42+07:00",
        "exit_time": "2025-04-16T18:19:42+07:00",
        "vehicle_type": "CAR"
    }
}
```

### 4. Reports

#### Daily Report
```
GET /api/daily-report/
```
- Returns statistics for current day
- Response:
```json
{
    "total_vehicles": 150,
    "total_revenue": 900000,
    "average_duration": 2.5,
    "vehicle_types": [
        {"vehicle_type": "CAR", "count": 100},
        {"vehicle_type": "MOTORCYCLE", "count": 50}
    ],
    "revenue_by_hour": [
        {"hour": "08:00", "amount": 150000},
        {"hour": "09:00", "amount": 200000}
    ]
}
```

#### Availability Report
```
GET /api/availability-report/
```
- Returns parking spot status
- Response:
```json
{
    "total_spots": 200,
    "available_spots": 50,
    "occupied_spots": 150,
    "occupancy_rate": 75.0,
    "spots": [
        {
            "floor": 1,
            "spot_number": "A1",
            "status": "OCCUPIED",
            "status_class": "danger",
            "vehicle": "B 1234 CD"
        }
    ]
}
```

### 5. Operator Management

#### List Operators
```
GET /api/operators/
```
- Returns list of all operators
- Response:
```json
{
    "operators": [
        {
            "id": 1,
            "username": "operator1",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com"
        }
    ]
}

#### Create Operator
```
POST /api/operators/
```
- Required fields: username, password, first_name, last_name, email
- Response:
```json
{
    "success": true,
    "message": "Operator created successfully",
    "operator": {
        "id": 1,
        "username": "operator1"
    }
}
```

### 6. Shift Management

#### Start Shift
```
POST /api/shifts/start/
```
- Optional fields: notes
- Response:
```json
{
    "success": true,
    "message": "Shift started successfully",
    "shift": {
        "id": 1,
        "start_time": "2025-04-16T16:49:42+07:00"
    }
}

#### End Shift
```
PUT /api/shifts/end/
```
- Response:
```json
{
    "success": true,
    "message": "Shift ended successfully",
    "shift": {
        "id": 1,
        "end_time": "2025-04-16T23:59:59+07:00",
        "total_vehicles": 150,
        "total_revenue": 900000
    }
}

### 7. Search Features

#### Search Vehicle
```
GET /api/search-vehicle/?q=B1234
```
- Query parameters: q (search term)
- Response:
```json
{
    "vehicles": [
        {
            "id": 1,
            "license_plate": "B 1234 CD",
            "vehicle_type": "CAR",
            "owner_name": "John Doe"
        }
    ]
}

#### Search Parking Spot
```
GET /api/search-parking-spot/?q=A1
```
- Query parameters: q (search term)
- Response:
```json
{
    "spots": [
        {
            "id": 1,
            "spot_number": "A1",
            "spot_type": "CAR",
            "status": "OCCUPIED",
            "floor": 1
        }
    ]
}

## Webhooks

### 1. Vehicle Entry Notification
```
POST /api/webhooks/vehicle-entry/
```
- Payload:
```json
{
    "event": "vehicle_entry",
    "data": {
        "license_plate": "B 1234 CD",
        "entry_time": "2025-04-16T16:49:42+07:00",
        "spot_number": "A1"
    }
}
```

### 2. Vehicle Exit Notification
```
POST /api/webhooks/vehicle-exit/
```
- Payload:
```json
{
    "event": "vehicle_exit",
    "data": {
        "license_plate": "B 1234 CD",
        "exit_time": "2025-04-16T18:19:42+07:00",
        "duration": 1.5,
        "fee": 6000
    }
}

## Error Codes

### Common Error Codes
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

### Specific Error Codes
- 409: Conflict (e.g., duplicate entry)
- 422: Unprocessable Entity (validation errors)
- 429: Too Many Requests

## Best Practices

1. Always validate vehicle license plates before processing
2. Use proper error handling for all API calls
3. Implement rate limiting for search endpoints
4. Use HTTPS for all production environments
5. Implement proper logging for all operations
6. Use pagination for large result sets
7. Implement caching for frequently accessed data
8. Use proper error codes and messages
9. Implement proper authentication and authorization
10. Use proper input validation

## Security

1. Use HTTPS for all API calls
2. Implement JWT token authentication
3. Use proper input validation
4. Implement rate limiting
5. Use secure password hashing
6. Implement proper session management
7. Use secure database connections
8. Implement proper logging
9. Use proper error handling
10. Implement proper access control

## System Requirements

### Hardware Requirements
1. **Camera (IP Camera)**
   - Type: Dahua IP Camera (recommended)
   - Resolution: Minimum 1280x720
   - Protocol: RTSP/HTTP
   - Connection: Ethernet

2. **Arduino Device**
   - Board: Arduino Uno/Nano
   - Port: COM port (usually COM3-COM9)
   - Baud Rate: 9600
   - Connection: USB

3. **Thermal Printer**
   - Type: EPSON TM-series
   - Connection: USB
   - Driver: EPSON ESC/POS compatible
   - Paper: 80mm thermal paper

4. **Server Requirements**
   - CPU: Minimum 2 cores
   - RAM: Minimum 4GB
   - Storage: Minimum 500GB
   - OS: Windows 10 or newer
   - Network: Ethernet connection

### Software Requirements
```bash
# Python Version
Python 3.8 or newer

# Python Packages
opencv-python==4.5.3.56
numpy==1.21.2
requests==2.26.0
psycopg2-binary==2.9.1
pyserial==3.5
python-escpos==2.2.0
Pillow==8.3.2
python-barcode==0.13.1

# Database
PostgreSQL 12 or newer
```

## Device Configuration

### 1. Camera Configuration
```ini
[camera]
# Camera connection settings
ip = 192.168.2.100
username = admin
password = admin123
port = 554
protocol = rtsp

# Image settings
width = 1280
height = 720
fps = 15
format = MJPG
```

### 2. Arduino Configuration
```ini
[button]
# Arduino settings
type = serial
port = COM3
baudrate = 9600
timeout = 1.0
debounce_delay = 0.5

# Pin configuration
button_pin = 2
led_pin = 13
```

### 3. Printer Configuration
```ini
[printer]
# Printer settings
model = TM-T82
vendor_id = 0x04b8
product_id = 0x0202
paper_width = 80
dpi = 180

# Print settings
font_size = 1
text_align = center
cut_type = partial
```

## Server Connection Details

### Base URL
```
http://192.168.2.6:5051/api
```

### Server Configuration
```ini
[server]
host = 192.168.2.6
port = 5051
api_base = /api
```

### Database Configuration
```ini
[database]
host = 192.168.2.6
port = 5432
name = parkir2
user = postgres
password = [secure password required]
```

## API Endpoints

### 1. Test Connection
Test server availability and get vehicle count.

**Endpoint:** `/test`  
**Method:** GET  
**Response:**
```json
{
    "success": true,
    "total_kendaraan": 150
}
```

### 2. Vehicle Entry
Register a new vehicle entering the parking lot.

**Endpoint:** `/masuk`  
**Method:** POST  
**Request Body:**
```json
{
    "plat": "B1234XY",
    "jenis": "Motor"  // Optional, defaults to "Motor"
}
```
**Response:**
```json
{
    "success": true,
    "data": {
        "tiket": "PKR202504150001",
        "plat": "B1234XY",
        "waktu": "2025-04-15 18:49:04",
        "jenis": "Motor",
        "is_parked": true,
        "is_lost": false,
        "is_paid": false,
        "is_valid": true
    }
}
```

### 3. Vehicle Exit
Process a vehicle leaving the parking lot.

**Endpoint:** `/keluar`  
**Method:** POST  
**Request Body:**
```json
{
    "tiket": "PKR202504150001",
    "plat": "B1234XY"  // Optional, for verification
}
```
**Response:**
```json
{
    "success": true,
    "data": {
        "tiket": "PKR202504150001",
        "plat": "B1234XY",
        "waktu_masuk": "2025-04-15 18:49:04",
        "waktu_keluar": "2025-04-15 20:30:15",
        "durasi": "1 jam 41 menit",
        "jenis": "Motor",
        "tarif": 5000,
        "status": {
            "is_parked": false,
            "is_paid": true,
            "is_valid": true
        }
    }
}
```

**Error Responses:**
```json
// Ticket not found
{
    "success": false,
    "error": "TICKET_NOT_FOUND",
    "message": "Tiket tidak ditemukan"
}

// Invalid plate number
{
    "success": false,
    "error": "INVALID_PLATE",
    "message": "Nomor plat tidak sesuai dengan tiket"
}

// Ticket already used
{
    "success": false,
    "error": "TICKET_USED",
    "message": "Tiket sudah digunakan"
}
```

### 4. Check Ticket Status
Check the status of a parking ticket.

**Endpoint:** `/cek-tiket`  
**Method:** GET  
**Parameters:** 
- `tiket`: Ticket number (required)
- `plat`: License plate number (optional)

**Response:**
```json
{
    "success": true,
    "data": {
        "tiket": "PKR202504150001",
        "plat": "B1234XY",
        "waktu_masuk": "2025-04-15 18:49:04",
        "jenis": "Motor",
        "durasi_current": "1 jam 30 menit",
        "estimasi_biaya": 5000,
        "status": {
            "is_parked": true,
            "is_paid": false,
            "is_valid": true
        }
    }
}
```

### 5. Offline Mode
The system supports offline operation when server connection is unavailable:

- Tickets are generated with "OFF" prefix
- Data is stored locally in `offline_data.json`
- Automatic sync when connection is restored

## Important Notes

### 1. Device Setup
- Camera must be on the same network as the server
- Arduino must be connected before starting the application
- Printer must be set as default Windows printer
- All devices should be tested individually before running the system

### 2. Network Configuration
- Use static IP for all devices
- Configure firewall to allow required ports
- Ensure stable network connection
- Recommended to use dedicated network switch

### 3. Maintenance
- Regular backup of database (daily)
- Clean camera lens weekly
- Check printer head monthly
- Test Arduino buttons daily
- Monitor disk space for images

### 4. Troubleshooting Common Issues

#### Camera Issues
- Check network connection
- Verify IP address and credentials
- Ensure proper lighting conditions
- Clean lens if image is blurry

#### Arduino Issues
- Check USB connection
- Verify COM port in Device Manager
- Reset Arduino if unresponsive
- Check button physical connection

#### Printer Issues
- Check paper supply
- Clear paper jams
- Clean printer head
- Verify printer is online and ready

### 5. Backup Procedures
1. Database Backup
   ```bash
   pg_dump -U postgres parkir2 > backup_$(date +%Y%m%d).sql
   ```

2. Image Backup
   ```bash
   # Backup capture directory
   xcopy /E /I /Y capture backup\capture_%date:~-4,4%%date:~-7,2%%date:~-10,2%
   ```

### 6. Emergency Procedures
1. If server is down:
   - System will operate in offline mode
   - Tickets will be generated with "OFF" prefix
   - Data will be synced when server is back online

2. If printer fails:
   - System will continue capturing
   - Save ticket numbers manually
   - Contact technical support for printer service

3. If camera fails:
   - System will use dummy image mode
   - Log the issue
   - Contact technical support

### 7. Security Considerations
1. Change default passwords
2. Use HTTPS in production
3. Implement API authentication
4. Regular security updates
5. Monitor access logs
6. Restrict physical access to devices

## Support Contact

For technical support:
- Email: support@rsi-bna.com
- Phone: [Contact Number]
- Hours: 24/7 