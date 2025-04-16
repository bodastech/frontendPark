from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Vehicle, ParkingSpot, ParkingSession, Shift, Captureticket
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.db import connection
import psycopg2
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import pandas as pd
import xlsxwriter
from io import BytesIO
import json

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('parking:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'parking/login.html')

def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('parking:login')

@login_required(login_url='parking:login')
def start_shift(request):
    # Check if user already has an active shift
    active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
    if active_shift:
        messages.warning(request, 'You already have an active shift!')
        return redirect('parking:dashboard')
    
    # Create new shift
    shift = Shift.objects.create(operator=request.user)
    messages.success(request, 'Shift started successfully!')
    return redirect('parking:dashboard')

@login_required(login_url='parking:login')
def end_shift(request):
    active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
    if not active_shift:
        messages.warning(request, 'No active shift found!')
        return redirect('parking:dashboard')
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        active_shift.notes = notes
        active_shift.end_shift()
        messages.success(request, 'Shift ended successfully!')
        return redirect('parking:shift_report', shift_id=active_shift.id)
    
    return render(request, 'parking/end_shift.html', {'shift': active_shift})

@login_required(login_url='parking:login')
def shift_report(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    
    # Generate hourly activity data
    hours = []
    checkins = []
    checkouts = []
    
    if shift.end_time:
        current_hour = shift.start_time.replace(minute=0, second=0, microsecond=0)
        end_hour = shift.end_time.replace(minute=0, second=0, microsecond=0)
        
        while current_hour <= end_hour:
            next_hour = current_hour + timedelta(hours=1)
            hours.append(current_hour.strftime('%H:%M'))
            
            # Count check-ins and check-outs for this hour
            checkins.append(shift.parking_sessions.filter(
                check_in_time__gte=current_hour,
                check_in_time__lt=next_hour
            ).count())
            
            checkouts.append(shift.parking_sessions.filter(
                check_out_time__gte=current_hour,
                check_out_time__lt=next_hour
            ).count())
            
            current_hour = next_hour
    
    # Generate revenue distribution data
    revenue_dist = [0, 0, 0, 0]  # [<1h, 1-2h, 2-4h, 4h+]
    
    for session in shift.parking_sessions.filter(check_out_time__isnull=False):
        duration = session.check_out_time - session.check_in_time
        hours = duration.total_seconds() / 3600
        
        if hours < 1:
            revenue_dist[0] += session.fee
        elif hours < 2:
            revenue_dist[1] += session.fee
        elif hours < 4:
            revenue_dist[2] += session.fee
        else:
            revenue_dist[3] += session.fee
    
    context = {
        'shift': shift,
        'hourly_labels': json.dumps(hours),
        'hourly_checkins': checkins,
        'hourly_checkouts': checkouts,
        'revenue_distribution': revenue_dist,
    }
    
    return render(request, 'parking/shift_report.html', context)

@login_required(login_url='parking:login')
def shift_list(request):
    shifts = Shift.objects.all()
    
    # Filter by date range
    date_range = request.GET.get('date_range')
    if date_range:
        start_date, end_date = date_range.split(' - ')
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        shifts = shifts.filter(start_time__date__range=[start_date, end_date])
    
    # Filter by status
    status = request.GET.get('status')
    if status == 'active':
        shifts = shifts.filter(end_time__isnull=True)
    elif status == 'completed':
        shifts = shifts.filter(end_time__isnull=False)
    
    # Sort
    sort_by = request.GET.get('sort', '-start_time')
    shifts = shifts.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(shifts, 10)
    page = request.GET.get('page')
    shifts = paginator.get_page(page)
    
    return render(request, 'parking/shift_list.html', {'shifts': shifts})

@login_required(login_url='parking:login')
def export_shift_report(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    
    # Create an in-memory output file for the Excel workbook
    output = BytesIO()
    
    # Create the Excel workbook and add a worksheet
    workbook = xlsxwriter.Workbook(output)
    
    # Add formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4F81BD',
        'font_color': 'white',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1
    })
    
    # Shift Summary Sheet
    summary_sheet = workbook.add_worksheet('Shift Summary')
    summary_sheet.set_column('A:B', 20)
    
    # Write shift summary
    summary_data = [
        ['Shift Information', ''],
        ['Operator', shift.operator.get_full_name()],
        ['Start Time', shift.start_time.strftime('%Y-%m-d %H:%M')],
        ['End Time', shift.end_time.strftime('%Y-%m-d %H:%M') if shift.end_time else 'Ongoing'],
        ['Total Vehicles', shift.total_vehicles],
        ['Total Revenue', f'Rp {shift.total_revenue}'],
        ['Status', 'Active' if shift.is_active else 'Completed'],
        ['Notes', shift.notes or '']
    ]
    
    for row, data in enumerate(summary_data):
        summary_sheet.write(row, 0, data[0], header_format if row == 0 else cell_format)
        summary_sheet.write(row, 1, data[1], header_format if row == 0 else cell_format)
    
    # Parking Sessions Sheet
    sessions_sheet = workbook.add_worksheet('Parking Sessions')
    sessions_sheet.set_column('A:G', 15)
    
    # Write headers
    headers = ['Check-in Time', 'Check-out Time', 'Vehicle', 'Spot', 'Duration', 'Fee', 'Status']
    for col, header in enumerate(headers):
        sessions_sheet.write(0, col, header, header_format)
    
    # Write parking session data
    sessions = shift.parking_sessions.all()
    for row, session in enumerate(sessions, start=1):
        data = [
            session.check_in_time.strftime('%Y-%m-d %H:%M'),
            session.check_out_time.strftime('%Y-%m-d %H:%M') if session.check_out_time else 'Ongoing',
            session.vehicle_license_plate,
            session.parking_spot.identifier,
            str(session.duration) if session.check_out_time else 'Ongoing',
            f'Rp {session.fee}',
            'Completed' if session.check_out_time else 'Active'
        ]
        for col, value in enumerate(data):
            sessions_sheet.write(row, col, value, cell_format)
    
    workbook.close()
    
    # Set up the response
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=shift_report_{shift_id}.xlsx'
    
    return response

@login_required(login_url='parking:login')
def dashboard(request):
    today = timezone.now().date()
    now = timezone.now()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    
    # Get basic stats
    total_today = ParkingSession.objects.filter(check_in_time__date=today).count()
    active_vehicles = ParkingSession.objects.filter(check_out_time__isnull=True).count()
    today_revenue = ParkingSession.objects.filter(
        check_out_time__date=today
    ).aggregate(total=Sum('fee'))['total'] or 0
    total_spots = ParkingSpot.objects.count()
    available_spots = ParkingSpot.objects.filter(status='AVAILABLE').count()
    
    # Get recent sessions
    recent_sessions = ParkingSession.objects.all().order_by('-check_in_time')[:10]
    
    # Get vehicle distribution
    vehicle_dist = {
        'motor': Vehicle.objects.filter(vehicle_type='MOTORCYCLE').count(),
        'car': Vehicle.objects.filter(vehicle_type='CAR').count(),
    }
    
    # Get hourly stats
    hours = []
    checkins = []
    checkouts = []
    
    for hour in range(24):
        hour_start = today_start + timedelta(hours=hour)
        hour_end = hour_start + timedelta(hours=1)
        
        if hour_end > now:
            break
            
        hours.append(f"{hour:02d}:00")
        checkins.append(
            ParkingSession.objects.filter(
                check_in_time__gte=hour_start,
                check_in_time__lt=hour_end
            ).count()
        )
        checkouts.append(
            ParkingSession.objects.filter(
                check_out_time__gte=hour_start,
                check_out_time__lt=hour_end
            ).count()
        )
    
    # Get active shift
    active_shift = Shift.objects.filter(end_time__isnull=True).first()
    
    context = {
        'total_today': total_today,
        'active_vehicles': active_vehicles,
        'today_revenue': today_revenue,
        'available_spots': available_spots,
        'total_spots': total_spots,
        'recent_sessions': recent_sessions,
        'vehicle_dist': vehicle_dist,
        'hourly_labels': hours,
        'hourly_checkins': checkins,
        'hourly_checkouts': checkouts,
        'active_shift': active_shift,
    }
    
    return render(request, 'parking/dashboard.html', context)

@login_required(login_url='parking:login')
def vehicle_list(request):
    vehicles = Vehicle.objects.all().order_by('-created_at')
    return render(request, 'parking/vehicle_list.html', {'vehicles': vehicles})

@login_required(login_url='parking:login')
def vehicle_add(request):
    if request.method == 'POST':
        license_plate = request.POST.get('license_plate')
        vehicle_type = request.POST.get('vehicle_type')
        owner_name = request.POST.get('owner_name')
        owner_contact = request.POST.get('owner_contact')
        
        Vehicle.objects.create(
            license_plate=license_plate,
            vehicle_type=vehicle_type,
            owner_name=owner_name,
            owner_contact=owner_contact
        )
        messages.success(request, 'Vehicle added successfully!')
        return redirect('parking:vehicle_list')
    
    return render(request, 'parking/vehicle_add.html')

@login_required(login_url='parking:login')
def parking_spot_list(request):
    spots = ParkingSpot.objects.all().order_by('floor', 'spot_number')
    return render(request, 'parking/spot_list.html', {'spots': spots})

@login_required(login_url='parking:login')
def parking_spot_add(request):
    if request.method == 'POST':
        spot_number = request.POST.get('spot_number')
        spot_type = request.POST.get('spot_type')
        floor = request.POST.get('floor')
        
        ParkingSpot.objects.create(
            spot_number=spot_number,
            spot_type=spot_type,
            floor=floor
        )
        messages.success(request, 'Parking spot added successfully!')
        return redirect('parking:parking_spot_list')
    
    return render(request, 'parking/spot_add.html')

@login_required(login_url='parking:login')
def check_in(request):
    # Check for active shift
    active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
    if not active_shift:
        messages.warning(request, 'You must start a shift first!')
        return redirect('parking:dashboard')
    
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle')
        spot_id = request.POST.get('parking_spot')
        
        if not all([vehicle_id, spot_id]):
            messages.error(request, 'Please fill all required fields.')
            return redirect('parking:check_in')
        
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)
        spot = get_object_or_404(ParkingSpot, id=spot_id)
        
        # Check if spot is available
        if not spot.is_available:
            messages.error(request, 'Selected parking spot is not available.')
            return redirect('parking:check_in')
        
        # Create parking session
        session = ParkingSession.objects.create(
            vehicle=vehicle,
            parking_spot=spot,
            shift=active_shift,
            check_in_time=timezone.now()
        )
        
        # Update spot availability
        spot.is_available = False
        spot.save()
        
        messages.success(request, f'Vehicle {vehicle.license_plate} checked in successfully.')
        return redirect('parking:dashboard')
    
    vehicles = Vehicle.objects.all()
    available_spots = ParkingSpot.objects.filter(is_available=True)
    
    return render(request, 'parking/check_in.html', {
        'vehicles': vehicles,
        'spots': available_spots
    })

@login_required(login_url='parking:login')
def check_out_view(request):
    # Check for active shift
    active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
    if not active_shift:
        messages.warning(request, 'You must start a shift first!')
        return redirect('parking:dashboard')
    
    if request.method == 'POST':
        ticket_number = request.POST.get('ticket_number')
        license_plate = request.POST.get('license_plate')
        
        if not ticket_number:
            messages.error(request, 'Please enter a ticket number.')
            return redirect('parking:check_out')
            
        try:
            # Find the parking session using the ticket number
            session = ParkingSession.objects.get(
                ticket_number=ticket_number,
                check_out_time__isnull=True  # Only get active sessions
            )
            
            # Verify license plate if provided
            if license_plate and session.vehicle.license_plate != license_plate:
                messages.error(request, 'License plate does not match ticket.')
                return redirect('parking:check_out')
            
            # Calculate duration and fee
            duration = timezone.now() - session.check_in_time
            hours = duration.total_seconds() / 3600
            
            # Basic fee calculation (you may want to adjust this)
            base_fee = 5000  # Base fee for first hour
            additional_fee = 2000  # Fee per additional hour
            total_fee = base_fee + max(0, int(hours - 1)) * additional_fee
            
            # Update session
            session.check_out_time = timezone.now()
            session.duration = duration
            session.fee = total_fee
            session.save()
            
            # Free up parking spot
            session.parking_spot.is_available = True
            session.parking_spot.save()
            
            # Prepare success message with receipt data
            receipt_data = {
                'tiket': session.ticket_number,
                'plat': session.vehicle.license_plate,
                'waktu_masuk': session.check_in_time.strftime('%Y-%m-%d %H:%M:%S'),
                'waktu_keluar': session.check_out_time.strftime('%Y-%m-%d %H:%M:%S'),
                'durasi': f"{int(hours)} jam {int((hours % 1) * 60)} menit",
                'tarif': total_fee
            }
            
            messages.success(request, 'Vehicle checked out successfully.')
            return JsonResponse({'success': True, 'data': receipt_data})
            
        except ParkingSession.DoesNotExist:
            messages.error(request, 'Invalid ticket number or ticket already used.')
            return JsonResponse({'success': False, 'message': 'Tiket tidak ditemukan'})
        except Exception as e:
            messages.error(request, f'Error processing checkout: {str(e)}')
            return JsonResponse({'success': False, 'message': str(e)})
    
    return render(request, 'parking/check_out.html')

@login_required(login_url='parking:login')
def session_list(request):
    sessions = ParkingSession.objects.all().order_by('-check_in_time')
    return render(request, 'parking/session_list.html', {'sessions': sessions})

def test_captureticket(request):
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname="parkir2",
            user="postgres",
            password="postgres",
            host="192.168.2.6",
            port="5432"
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Get all records from captureticket table
        cur.execute("SELECT * FROM captureticket ORDER BY date_masuk DESC LIMIT 10")
        tickets = cur.fetchall()
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'tickets': [
                {
                    'id': ticket[0],
                    'plat_no': ticket[1],
                    'date_masuk': ticket[2].isoformat() if ticket[2] else None,
                    'date_keluar': ticket[3].isoformat() if ticket[3] else None,
                    'status': ticket[4],
                    'biaya': ticket[5]
                }
                for ticket in tickets
            ]
        })
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__
        })

@login_required(login_url='parking:login')
def view_captureticket(request):
    try:
        # Get the tickets using raw SQL for better control
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, plat_no, date_masuk, date_keluar, status, biaya 
                FROM captureticket 
                ORDER BY date_masuk DESC 
                LIMIT 100
            """)
            columns = [col[0] for col in cursor.description]
            tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Calculate statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_tickets,
                    COUNT(CASE WHEN date_keluar IS NULL THEN 1 END) as active_tickets,
                    COUNT(CASE WHEN date_keluar IS NOT NULL THEN 1 END) as completed_tickets,
                    SUM(CASE WHEN biaya IS NOT NULL THEN biaya ELSE 0 END) as total_revenue
                FROM captureticket
                WHERE date_masuk >= CURRENT_DATE
            """)
            stats = dict(zip(['total_tickets', 'active_tickets', 'completed_tickets', 'total_revenue'], cursor.fetchone()))
            
        return render(request, 'parking/captureticket_list.html', {
            'tickets': tickets,
            'stats': stats
        })
    except Exception as e:
        messages.error(request, f'Database error: {str(e)}')
        return redirect('parking:dashboard')

@login_required(login_url='parking:login')
def test_connection(request):
    try:
        # Direct connection test using psycopg2
        conn = psycopg2.connect(
            dbname="parkir2",
            user="postgres",
            password="postgres",
            host="192.168.2.6",
            port="5432"
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Test basic connection and get version
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        
        # Get all schemas
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
        """)
        schemas = [row[0] for row in cur.fetchall()]
        
        # Get all tables from public schema
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        # Check if CaptureTicket table exists (case-insensitive)
        capture_table = None
        for table in tables:
            if table.lower() == 'captureticket':
                capture_table = table
                break
        
        # If we found the table, get its structure
        table_structure = []
        if capture_table:
            cur.execute(f"""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = '{capture_table}'
                ORDER BY ordinal_position
            """)
            table_structure = cur.fetchall()
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
        return JsonResponse({
            'status': 'Connected successfully',
            'version': version,
            'host': '192.168.2.6',
            'database': 'parkir2',
            'schemas': schemas,
            'tables': tables,
            'capture_ticket_table': {
                'name': capture_table,
                'columns': table_structure if capture_table else None
            }
        }, json_dumps_params={'indent': 2})
            
    except Exception as e:
        return JsonResponse({
            'status': 'Connection failed',
            'error': str(e),
            'error_type': type(e).__name__,
            'connection_details': {
                'host': '192.168.2.6',
                'database': 'parkir2',
                'port': '5432',
                'user': 'postgres'
            }
        }, json_dumps_params={'indent': 2})
