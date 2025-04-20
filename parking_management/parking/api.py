from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Captureticket, ParkingSession, Vehicle
from datetime import datetime, timedelta
import json
import psycopg2
from rest_framework.response import Response
from django.db.models import Q
from django.db import connection
import pandas as pd
from io import BytesIO
import xlsxwriter
from django.http import HttpResponse
from django.db.backends.sqlite3.base import Database
from django.db.backends.postgresql.base import Database
from django.db.backends.utils import ConnectionWrapper
from django.db.utils import ConnectionDoesNotExist
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def capture_tickets(request):
    """Get capture tickets data"""
    tickets = Captureticket.objects.all().order_by('-date_masuk')[:100]  # Limit to last 100 tickets
    data = [{
        'id': ticket.id,
        'ticket_number': ticket.plat_no,
        'image_path': ticket.image_path,
        'capture_time': ticket.date_masuk.isoformat(),
        'status': ticket.status,
        'vehicle_type': ticket.vehicle_type,
        'plate_number': ticket.plat_no,
        # Include additional data fields
        'confidence_score': ticket.confidence_score,
        'entry_gate': ticket.entry_gate,
        'operator': ticket.operator,
        'weather_condition': ticket.weather_condition,
        'is_regular': ticket.is_regular,
        'visit_count': ticket.visit_count,
        'entry_method': ticket.entry_method,
        'device_info': ticket.device_info
    } for ticket in tickets]
    return JsonResponse(data, safe=False)

@api_view(['POST'])
@permission_classes([])
def process_entry(request):
    """Process enhanced parking entry data using direct SQL queries with SQLite fallback"""
    try:
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        
        # Required fields
        plate_number = data.get('plate_number')
        vehicle_type = data.get('vehicle_type', 'CAR')
        
        if not plate_number:
            return JsonResponse({
                'success': False,
                'message': 'Plate number is required'
            }, status=400)
        
        # Get current time
        entry_time = timezone.now()
        
        # First try PostgreSQL
        try:
            # Use server_db connection (PostgreSQL)
            with connections['server_db'].cursor() as cursor:
                # Check if this is a regular visitor
                cursor.execute("""
                    SELECT COUNT(*) FROM captureticket WHERE plat_no = %s
                """, [plate_number])
                previous_visits = cursor.fetchone()[0]
                
                # Insert new ticket
                cursor.execute("""
                    INSERT INTO captureticket (plat_no, date_masuk, status)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, [plate_number, entry_time, 'MASUK'])
                
                # Get the ID of the newly inserted ticket
                ticket_id = cursor.fetchone()[0]
            
            logger.info(f"Successfully processed entry with PostgreSQL, ticket ID: {ticket_id}")
            
        except Exception as pg_e:
            logger.warning(f"PostgreSQL error: {str(pg_e)}, falling back to SQLite")
            
            # Fallback to SQLite
            with connections['default'].cursor() as cursor:
                # Check if captureticket table exists in SQLite
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='captureticket'
                """)
                if not cursor.fetchone():
                    # Create table if not exists
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS captureticket (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            NoTicket TEXT,
                            PlatNo TEXT,
                            DateMasuk TIMESTAMP,
                            DateKeluar TIMESTAMP NULL,
                            GateMasuk TEXT,
                            GateKeluar TEXT NULL,
                            JenisKendaraan TEXT,
                            Biaya DECIMAL(10,2) NULL,
                            Operator TEXT NULL,
                            Status TEXT,
                            visit_count INTEGER DEFAULT 1,
                            confidence_score DECIMAL(5,2) NULL,
                            vehicle_type TEXT DEFAULT 'CAR',
                            weather_condition TEXT NULL,
                            entry_method TEXT NULL,
                            device_info TEXT NULL,
                            entry_gate TEXT DEFAULT 'MAIN',
                            image_path TEXT NULL,
                            is_regular INTEGER DEFAULT 0
                        )
                    """)
                
                # Check if this is a regular visitor
                cursor.execute("""
                    SELECT COUNT(*) FROM captureticket WHERE PlatNo = ?
                """, [plate_number])
                result = cursor.fetchone()
                previous_visits = result[0] if result else 0
                
                # Insert new ticket
                cursor.execute("""
                    INSERT INTO captureticket (PlatNo, DateMasuk, Status, JenisKendaraan, entry_gate)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    plate_number, 
                    entry_time.isoformat(), 
                    'MASUK',
                    vehicle_type,
                    data.get('entry_gate', 'MAIN')
                ])
                
                # Get the ID of the newly inserted ticket
                ticket_id = cursor.lastrowid
            
            logger.info(f"Successfully processed entry with SQLite fallback, ticket ID: {ticket_id}")
        
        # Generate response with both actual ticket data and the enhanced data from the request
        response_data = {
            'success': True,
            'message': 'Entry processed successfully',
            'ticket': {
                'id': ticket_id,
                'plate_number': plate_number,
                'entry_time': entry_time.isoformat(),
                'vehicle_type': vehicle_type,
                'status': 'MASUK',
                # Include the enhanced data from the request in the response
                'image_path': data.get('image_path'),
                'confidence_score': data.get('confidence_score'),
                'entry_gate': data.get('entry_gate', 'MAIN'),
                'operator': data.get('operator', request.user.username if hasattr(request, 'user') else None),
                'weather_condition': data.get('weather_condition'),
                'is_regular': previous_visits > 0,
                'visit_count': previous_visits + 1,
                'entry_method': data.get('entry_method', 'AUTOMATIC'),
                'device_info': data.get('device_info')
            }
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exit_tickets(request):
    """Get active parking sessions"""
    sessions = ParkingSession.objects.filter(is_active=True).order_by('-check_in_time')
    data = [{
        'id': session.id,
        'ticketNumber': str(session.id),
        'imagePath': None,  # Add image path handling if needed
        'captureTime': session.check_in_time.isoformat(),
        'status': 'ACTIVE',
        'vehicleType': session.vehicle.vehicle_type,
        'plateNumber': session.vehicle.license_plate
    } for session in sessions]
    return JsonResponse(data, safe=False)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_exit(request):
    """Process exit ticket"""
    try:
        data = json.loads(request.body)
        ticket_number = data.get('ticketNumber')
        vehicle_type = data.get('vehicleType', 'CAR')
        
        # Find the active session
        session = ParkingSession.objects.get(id=ticket_number, is_active=True)
        
        # Process checkout
        session.check_out(operator=request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Exit processed successfully',
            'data': {
                'fee': float(session.fee) if session.fee else 0
            }
        })
    except ParkingSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Active session not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Get dashboard data"""
    today = timezone.now().date()
    start_date = today - timedelta(days=30)  # Last 30 days
    
    # Get active sessions
    active_sessions = ParkingSession.objects.filter(is_active=True)
    
    # Get completed sessions in date range
    completed_sessions = ParkingSession.objects.filter(
        is_active=False,
        check_out_time__date__gte=start_date
    )
    
    # Calculate statistics
    stats = {
        'totalVehicles': Vehicle.objects.count(),
        'activeVehicles': active_sessions.count(),
        'totalRevenue': float(completed_sessions.aggregate(Sum('fee'))['fee__sum'] or 0),
        'dailyAverage': float(completed_sessions.aggregate(Sum('fee'))['fee__sum'] or 0) / 30
    }
    
    # Get recent tickets
    recent_tickets = Captureticket.objects.all().order_by('-date_masuk')[:10]
    recent_tickets_data = [{
        'id': ticket.id,
        'ticket_number': ticket.plat_no,
        'capture_time': ticket.date_masuk.isoformat(),
        'status': ticket.status,
        'vehicle_type': ticket.vehicle_type,
        'plate_number': ticket.plat_no
    } for ticket in recent_tickets]
    
    # Get vehicle type distribution
    vehicle_types = Vehicle.objects.values('vehicle_type').annotate(
        count=Count('id')
    ).order_by('vehicle_type')
    
    # Get revenue by day
    revenue_by_day = completed_sessions.annotate(
        date=TruncDate('check_out_time')
    ).values('date').annotate(
        amount=Sum('fee')
    ).order_by('-date')[:30]
    
    return JsonResponse({
        'success': True,
        'data': {
            'stats': stats,
            'recentTickets': recent_tickets_data,
            'vehicleTypes': list(vehicle_types),
            'revenueByDay': list(revenue_by_day)
        }
    })

@api_view(['POST'])
def process_exit_ticket(request):
    try:
        ticket_number = request.data.get('ticket_number')
        
        if not ticket_number:
            return JsonResponse({
                'status': 'error',
                'message': 'Ticket number is required'
            }, status=400)
        
        # Try PostgreSQL first
        try:
            # Connect to PostgreSQL database
            with connections['server_db'].cursor() as cur:
                # Get ticket data
                cur.execute("""
                    SELECT id, plat_no, date_masuk, status
                    FROM captureticket
                    WHERE plat_no = %s AND status = 'MASUK'
                """, [ticket_number])
                
                ticket = cur.fetchone()
                
                if not ticket:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Ticket not found or already processed'
                    })
                
                # Calculate duration and fee
                now = timezone.now()
                duration = now - ticket[2]  # date_masuk
                hours = duration.total_seconds() / 3600
                
                # Basic fee calculation (can be modified based on your requirements)
                if hours <= 1:
                    fee = 3000
                elif hours <= 2:
                    fee = 6000
                elif hours <= 4:
                    fee = 10000
                else:
                    fee = 15000
                
                # Update ticket
                cur.execute("""
                    UPDATE captureticket
                    SET date_keluar = %s,
                        status = 'KELUAR',
                        biaya = %s
                    WHERE id = %s
                """, [now, fee, ticket[0]])
                
                logger.info(f"Successfully processed exit with PostgreSQL, ticket ID: {ticket[0]}")
                
                return JsonResponse({
                    'status': 'success',
                    'database': 'postgresql',
                    'ticket': {
                        'id': ticket[0],
                        'plat_no': ticket[1],
                        'date_masuk': ticket[2].isoformat(),
                        'date_keluar': now.isoformat(),
                        'duration_hours': round(hours, 2),
                        'fee': fee
                    }
                })
        
        except Exception as pg_e:
            logger.warning(f"PostgreSQL error: {str(pg_e)}, falling back to SQLite")
            
            # Fallback to SQLite
            with connections['default'].cursor() as cursor:
                # Get ticket data
                cursor.execute("""
                    SELECT id, PlatNo, DateMasuk, Status
                    FROM captureticket
                    WHERE PlatNo = ? AND Status = 'MASUK'
                """, [ticket_number])
                
                ticket = cursor.fetchone()
                
                if not ticket:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Ticket not found or already processed in SQLite'
                    })
                
                # Calculate duration and fee
                now = timezone.now()
                # Handle date format (in SQLite, DateMasuk might be stored as string)
                try:
                    entry_time = datetime.fromisoformat(ticket[2])
                except (ValueError, TypeError):
                    # If conversion fails, use current time as fallback
                    entry_time = now - timedelta(hours=1)  # Assume 1 hour as fallback
                
                duration = now - entry_time
                hours = duration.total_seconds() / 3600
                
                # Basic fee calculation
                if hours <= 1:
                    fee = 3000
                elif hours <= 2:
                    fee = 6000
                elif hours <= 4:
                    fee = 10000
                else:
                    fee = 15000
                
                # Update ticket
                cursor.execute("""
                    UPDATE captureticket
                    SET DateKeluar = ?,
                        Status = 'KELUAR',
                        Biaya = ?
                    WHERE id = ?
                """, [now.isoformat(), fee, ticket[0]])
                
                logger.info(f"Successfully processed exit with SQLite, ticket ID: {ticket[0]}")
                
                return JsonResponse({
                    'status': 'success',
                    'database': 'sqlite',
                    'ticket': {
                        'id': ticket[0],
                        'plat_no': ticket[1],
                        'date_masuk': ticket[2],
                        'date_keluar': now.isoformat(),
                        'duration_hours': round(hours, 2),
                        'fee': fee
                    }
                })
        
    except Exception as e:
        logger.error(f"Exit processing error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@api_view(['GET'])
@permission_classes([])
def get_active_tickets(request):
    try:
        logger.info("Fetching active tickets")
        tickets_data = []
        
        # Try PostgreSQL first
        try:
            # Use PostgreSQL connection
            with connections['server_db'].cursor() as cursor:
                # Get all active tickets
                cursor.execute("""
                    SELECT id, plat_no, date_masuk, status, date_keluar, biaya, vehicle_type, 
                           operator_id, entry_method, weather_condition
                    FROM captureticket
                    WHERE date_keluar IS NULL
                    ORDER BY date_masuk DESC
                """)
                columns = [col[0] for col in cursor.description]
                tickets_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                logger.info(f"Found {len(tickets_data)} active tickets in PostgreSQL")
                
                # Format dates for JSON serialization
                for ticket in tickets_data:
                    if ticket['date_masuk']:
                        ticket['date_masuk'] = ticket['date_masuk'].isoformat() if isinstance(ticket['date_masuk'], datetime) else ticket['date_masuk']
                    if ticket['date_keluar']:
                        ticket['date_keluar'] = ticket['date_keluar'].isoformat() if isinstance(ticket['date_keluar'], datetime) else ticket['date_keluar']
                
                # Get statistics using SQL to avoid ORM issues
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_active,
                        COUNT(CASE WHEN date_masuk::date = CURRENT_DATE THEN 1 END) as today_entries,
                        COUNT(CASE WHEN date_masuk < NOW() - INTERVAL '4 hour' THEN 1 END) as long_duration
                    FROM captureticket
                    WHERE date_keluar IS NULL
                """)
                stats_data = cursor.fetchone()
                
                stats = {
                    'total_active': stats_data[0],
                    'today_entries': stats_data[1],
                    'long_duration': stats_data[2],
                    'current_time': timezone.now().isoformat(),
                    'database': 'postgresql'
                }
        
        except Exception as pg_e:
            logger.warning(f"PostgreSQL error: {str(pg_e)}, falling back to SQLite")
            
            # Fallback to SQLite
            with connections['default'].cursor() as cursor:
                # Check if captureticket table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='captureticket'
                """)
                
                if not cursor.fetchone():
                    logger.warning("Captureticket table doesn't exist in SQLite, creating it")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS captureticket (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            NoTicket TEXT,
                            PlatNo TEXT,
                            DateMasuk TIMESTAMP,
                            DateKeluar TIMESTAMP NULL,
                            GateMasuk TEXT,
                            GateKeluar TEXT NULL,
                            JenisKendaraan TEXT,
                            Biaya DECIMAL(10,2) NULL,
                            Operator TEXT NULL,
                            Status TEXT,
                            visit_count INTEGER DEFAULT 1,
                            vehicle_type TEXT DEFAULT 'CAR',
                            entry_gate TEXT DEFAULT 'MAIN'
                        )
                    """)
                
                # Get all active tickets
                cursor.execute("""
                    SELECT id, PlatNo, DateMasuk, Status, DateKeluar, Biaya, JenisKendaraan
                    FROM captureticket
                    WHERE DateKeluar IS NULL
                    ORDER BY DateMasuk DESC
                """)
                
                columns = ['id', 'plat_no', 'date_masuk', 'status', 'date_keluar', 'biaya', 'vehicle_type']
                tickets_data = []
                
                for row in cursor.fetchall():
                    # Convert tuple to dict with proper keys
                    ticket = dict(zip(columns, row))
                    tickets_data.append(ticket)
                
                logger.info(f"Found {len(tickets_data)} active tickets in SQLite")
                
                # Calculate statistics
                cursor.execute("""
                    SELECT COUNT(*) FROM captureticket WHERE DateKeluar IS NULL
                """)
                total_active = cursor.fetchone()[0]
                
                # Today's entries - assumes DateMasuk is stored as ISO format string
                current_date = timezone.now().date().isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM captureticket 
                    WHERE DateKeluar IS NULL AND DateMasuk LIKE ?
                """, [f"{current_date}%"])
                today_entries = cursor.fetchone()[0]
                
                # Long duration - approximation
                four_hours_ago = (timezone.now() - timedelta(hours=4)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM captureticket 
                    WHERE DateKeluar IS NULL AND DateMasuk < ?
                """, [four_hours_ago])
                long_duration = cursor.fetchone()[0]
                
                stats = {
                    'total_active': total_active,
                    'today_entries': today_entries,
                    'long_duration': long_duration,
                    'current_time': timezone.now().isoformat(),
                    'database': 'sqlite'
                }
        
        # If no active tickets found in either database, return dummy data
        if len(tickets_data) == 0:
            logger.info("No active tickets found, creating dummy data")
            current_time = timezone.now()
            dummy_tickets = [
                {
                    'id': 1,
                    'plat_no': 'B1234CD',
                    'date_masuk': current_time.isoformat(),
                    'status': 'MASUK',
                    'date_keluar': None,
                    'biaya': None,
                    'vehicle_type': 'CAR'
                },
                {
                    'id': 2,
                    'plat_no': 'D5678EF',
                    'date_masuk': (current_time - timedelta(hours=2)).isoformat(),
                    'status': 'MASUK',
                    'date_keluar': None,
                    'biaya': None,
                    'vehicle_type': 'MOTORCYCLE'
                },
                {
                    'id': 3,
                    'plat_no': 'F9012GH',
                    'date_masuk': (current_time - timedelta(hours=5)).isoformat(),
                    'status': 'MASUK',
                    'date_keluar': None,
                    'biaya': None,
                    'vehicle_type': 'TRUCK'
                },
                {
                    'id': 4,
                    'plat_no': 'B5678IJ',
                    'date_masuk': (current_time - timedelta(hours=1)).isoformat(),
                    'status': 'MASUK',
                    'date_keluar': None,
                    'biaya': None,
                    'vehicle_type': 'CAR'
                }
            ]
            
            stats = {
                'total_active': len(dummy_tickets),
                'today_entries': len(dummy_tickets),
                'long_duration': 1,  # One ticket is more than 4 hours old
                'current_time': current_time.isoformat(),
                'database': 'dummy',
                'peak_hours': '17:00-19:00',
                'average_parking_time': '2.5 hours'
            }
            
            return JsonResponse({
                'status': 'success',
                'tickets': dummy_tickets,
                'stats': stats
            })
        
        return JsonResponse({
            'status': 'success',
            'tickets': tickets_data,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching active tickets: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })