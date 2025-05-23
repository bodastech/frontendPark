# Sistem Parkir RSI BNA

Sistem manajemen parkir untuk Rumah Sakit Islam BNA dengan fitur masuk dan keluar kendaraan.

## Struktur Folder

```
dj15april-main/
├── parking_management/          # Django Project Root
│   ├── parking_management/     # Project Configuration
│   │   ├── __init__.py
│   │   ├── settings.py        # Pengaturan utama Django
│   │   ├── urls.py           # URL utama project
│   │   ├── asgi.py          # ASGI config
│   │   └── wsgi.py          # WSGI config
│   │
│   └── parking/              # Aplikasi Parkir
│       ├── migrations/       # Database migrations
│       ├── templates/
│       │   └── parking/
│       │       ├── base.html          # Template dasar
│       │       ├── check_in.html      # Form parkir masuk
│       │       ├── check_out.html     # Form parkir keluar
│       │       ├── dashboard.html     # Halaman utama
│       │       ├── login.html         # Halaman login
│       │       └── ... (template lainnya)
│       ├── __init__.py
│       ├── admin.py         # Konfigurasi admin Django
│       ├── api.py          # API endpoints
│       ├── apps.py         # Konfigurasi aplikasi
│       ├── models.py       # Model database
│       ├── urls.py         # URL routing aplikasi
│       └── views.py        # Logic tampilan
├── manage.py               # Command-line utility Django
├── api-doc.md             # Dokumentasi API
└── README.md              # Dokumentasi project
```

## Komponen Sistem

### 1. Parkir Masuk
- Input plat nomor kendaraan
- Cetak tiket masuk
- Simpan data ke database
- Integrasi dengan kamera

### 2. Parkir Keluar
- Scan/input nomor tiket
- Verifikasi plat nomor
- Hitung durasi dan biaya
- Cetak struk keluar

## Endpoint API

### Parkir Masuk
- `POST /api/gate/capture-tickets/` - Menyimpan data kendaraan masuk
- `GET /api/test-connection/` - Test koneksi server

### Parkir Keluar
- `GET /api/cek-tiket` - Cek status tiket
- `POST /api/keluar` - Proses kendaraan keluar

## Database

### Tabel Utama
1. `captureticket` - Data tiket masuk
2. `ParkingSession` - Sesi parkir aktif
3. `Vehicle` - Data kendaraan
4. `ParkingSpot` - Data slot parkir
5. `Shift` - Data shift petugas

## Konfigurasi

### Database
```ini
host = 192.168.2.6
port = 5432
name = parkir2
user = postgres
password = [sesuaikan]
```

### Server
```ini
host = 192.168.2.6
port = 5051
api_base = /api
```

## Alur Kerja

### Parkir Masuk
1. Kamera menangkap plat nomor
2. Data dikirim ke server
3. Tiket dicetak
4. Data disimpan di database

### Parkir Keluar
1. Petugas input/scan nomor tiket
2. Sistem verifikasi data tiket
3. Menampilkan informasi parkir
4. Hitung biaya
5. Proses pembayaran
6. Cetak struk
7. Update status di database

## Perangkat yang Dibutuhkan

1. Kamera (IP Camera)
   - Dahua IP Camera
   - Resolution: 1280x720
   - Protocol: RTSP/HTTP

2. Printer Thermal
   - EPSON TM-series
   - Paper: 80mm
   - Connection: USB

3. Server
   - CPU: 2 cores minimum
   - RAM: 4GB minimum
   - OS: Windows 10
   - Network: LAN

## Development Checklist & Roadmap

### ✅ Completed Features (Version 1.0)
1. Core System
   - [x] User authentication and authorization
   - [x] Database integration with PostgreSQL
   - [x] Basic UI template and navigation
   - [x] Server connection management

2. Parking Management
   - [x] Vehicle check-in/check-out
   - [x] License plate recording
   - [x] Fee calculation
   - [x] Ticket generation

3. Reporting
   - [x] Shift reports
   - [x] Revenue tracking
   - [x] Occupancy monitoring
   - [x] Excel export functionality

4. Staff Management
   - [x] Shift management
   - [x] Operator activity tracking
   - [x] Session management

### 🚀 Current Development (Version 1.1)
1. Enhanced Reporting
   - [x] Spot utilization visualization
   - [x] Daily/monthly reports
   - [x] Revenue distribution charts
   - [x] Real-time dashboard updates

2. System Integration
   - [x] External database synchronization
   - [x] Camera integration API
   - [x] Printer service integration
   - [x] Network redundancy

### 📋 Upcoming Features (Version 1.2)
1. Advanced Analytics
   - [ ] Predictive parking patterns
   - [ ] Peak hour analysis
   - [ ] Revenue forecasting
   - [ ] Occupancy trends

2. User Experience
   - [ ] Mobile-responsive design
   - [ ] Dark mode support
   - [ ] Quick action shortcuts
   - [ ] Notification system

3. Hardware Integration
   - [ ] Multiple camera support
   - [ ] Barrier gate automation
   - [ ] LED display integration
   - [ ] RFID card support

4. Security Enhancements
   - [ ] Role-based access control
   - [ ] Audit logging
   - [ ] Backup automation
   - [ ] Data encryption

### 🎯 Future Roadmap (Version 2.0)
1. Smart Parking Features
   - [ ] Mobile app for users
   - [ ] Online payment integration
   - [ ] Parking space reservation
   - [ ] License plate recognition AI

2. System Expansion
   - [ ] Multi-location support
   - [ ] Cloud backup integration
   - [ ] API gateway implementation
   - [ ] Load balancing

3. Business Intelligence
   - [ ] Custom report builder
   - [ ] Business analytics dashboard
   - [ ] Performance metrics
   - [ ] Revenue optimization tools

## Troubleshooting

### Koneksi Database
1. Cek status PostgreSQL service
2. Verifikasi kredensial database
3. Cek firewall settings
4. Test menggunakan endpoint `/test-connection/`

### Printer
1. Cek koneksi USB
2. Verifikasi driver printer
3. Cek status kertas
4. Test print melalui Windows

### Kamera
1. Cek koneksi jaringan
2. Verifikasi IP kamera
3. Test stream RTSP
4. Cek pencahayaan#   f r o n t e n d P a r k  
 