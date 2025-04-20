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
from datetime import datetime, timedelta, time
import pandas as pd
import xlsxwriter
from io import BytesIO
import json
import socket
from django.db.utils import connections
import logging

logger = logging.getLogger(__name__)

def get_active_shift(user):
    """
    Get the active shift for a given user.
    Returns None if no active shift is found.
    """
    return Shift.objects.filter(operator=user, is_active=True).first()

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
    
    try:
        # Create new shift
        shift = Shift.objects.create(
            operator=request.user,
            start_time=timezone.now(),
            is_active=True,
            total_vehicles=0,
            total_revenue=0
        )
        
        # Try to connect to server to verify connection
        conn = psycopg2.connect(
            dbname="parkir2",
            user="postgres",
            password="postgres",
            host="192.168.2.6",
            port="5432"
        )
        conn.close()
        
        messages.success(request, 'Shift started successfully! Server connection verified.')
    except psycopg2.Error as e:
        messages.warning(request, f'Shift started but server connection failed: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error starting shift: {str(e)}')
        return redirect('parking:dashboard')
    
    return redirect('parking:dashboard')

@login_required(login_url='parking:login')
def end_shift(request):
    active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
    if not active_shift:
        messages.warning(request, 'No active shift found!')
        return redirect('parking:dashboard')
    
    if request.method == 'POST':
        try:
            # Get local statistics
            shift_start = active_shift.start_time
            shift_end = timezone.now()
            
            local_vehicles = Captureticket.objects.filter(
                date_masuk__range=(shift_start, shift_end)
            ).count()
            
            local_revenue = Captureticket.objects.filter(
                date_masuk__range=(shift_start, shift_end),
                date_keluar__isnull=False
            ).aggregate(Sum('biaya'))['biaya__sum'] or 0
            
            # Try to get server statistics
            try:
                conn = psycopg2.connect(
                    dbname="parkir2",
                    user="postgres",
                    password="postgres",
                    host="192.168.2.6",
                    port="5432"
                )
                cur = conn.cursor()
                
                # Get server tickets for the shift period
                cur.execute("""
                    SELECT 
                        date_masuk, 
                        date_keluar, 
                        biaya
                    FROM public.captureticket 
                    WHERE date_masuk BETWEEN %s AND %s
                    ORDER BY date_masuk DESC
                """, [shift_start, shift_end])
                
                server_tickets = cur.fetchall()
                
                server_vehicles = len(server_tickets)
                server_revenue = sum([
                    ticket[2] or 0 for ticket in server_tickets
                    if ticket[1] is not None  # Only count completed tickets
                ])
                
                cur.close()
                conn.close()
                
            except Exception as e:
                print(f"Server connection error during end shift: {str(e)}")
                server_vehicles = 0
                server_revenue = 0
            
            # Update shift record
            notes = request.POST.get('notes', '')
            active_shift.end_time = shift_end
            active_shift.is_active = False
            active_shift.notes = notes
            active_shift.total_vehicles = local_vehicles + server_vehicles
            active_shift.total_revenue = local_revenue + server_revenue
            active_shift.save()
            
            messages.success(request, 'Shift ended successfully!')
            return redirect('parking:shift_report', shift_id=active_shift.id)
            
        except Exception as e:
            messages.error(request, f'Error ending shift: {str(e)}')
            return redirect('parking:dashboard')
    
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
    # Get local shifts
    shifts = Shift.objects.all().order_by('-start_time')
    
    # Get server data
    try:
        conn = psycopg2.connect(
            dbname="parkir2",  # Changed from parking_db to parkir2
            user="postgres",
            password="postgres",  # Changed from admin to postgres
            host="192.168.2.6",
            port="5432"
        )
        cur = conn.cursor()
        
        # Get tickets from server for the current day
        today = timezone.now().date()
        cur.execute("""
            SELECT 
                date_masuk, 
                date_keluar, 
                plat_no, 
                biaya,
                status,
                entry_gate
            FROM public.captureticket 
            WHERE DATE(date_masuk) = %s
            ORDER BY date_masuk DESC
        """, [today])
        
        server_tickets = cur.fetchall()
        
        # Calculate statistics for each shift
        for shift in shifts:
            # Local statistics from Captureticket model
            shift_start = shift.start_time
            shift_end = shift.end_time or timezone.now()
            
            shift.total_vehicles = Captureticket.objects.filter(
                date_masuk__range=(shift_start, shift_end)
            ).count()
            
            shift.total_revenue = Captureticket.objects.filter(
                date_masuk__range=(shift_start, shift_end),
                date_keluar__isnull=False
            ).aggregate(Sum('biaya'))['biaya__sum'] or 0
            
            # Server statistics
            server_vehicles = len([
                ticket for ticket in server_tickets
                if shift_start <= ticket[0].replace(tzinfo=timezone.utc) <= shift_end
            ])
            
            server_revenue = sum([
                ticket[3] or 0 for ticket in server_tickets
                if shift_start <= ticket[0].replace(tzinfo=timezone.utc) <= shift_end
                and ticket[1] is not None  # Only count completed tickets
            ])
            
            shift.server_vehicles = server_vehicles
            shift.server_revenue = server_revenue
            
            # Calculate duration
            duration = shift_end - shift_start
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            shift.duration = f"{int(hours)} hours, {int(minutes)} minutes"
            
            if not shift.end_time:
                shift.duration += " (ongoing)"
                shift.is_active = True
            else:
                shift.is_active = False
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Server connection error: {str(e)}")  # Debug print
        messages.error(request, f'Error connecting to server: {str(e)}')
        # Set default values if server connection fails
        for shift in shifts:
            shift.server_vehicles = 0
            shift.server_revenue = 0
            duration = (shift.end_time or timezone.now()) - shift.start_time
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            shift.duration = f"{int(hours)} hours, {int(minutes)} minutes"
            if not shift.end_time:
                shift.duration += " (ongoing)"
                shift.is_active = True
            else:
                shift.is_active = False
    
    # Apply filters
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if status == 'active':
        shifts = [s for s in shifts if not s.end_time]
    elif status == 'completed':
        shifts = [s for s in shifts if s.end_time]
    
    if date_from and date_to:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            shifts = [s for s in shifts if date_from.date() <= s.start_time.date() <= date_to.date()]
        except ValueError:
            messages.error(request, 'Invalid date format')
    
    context = {
        'shifts': shifts,
        'filters': {
            'status': status,
            'date_from': date_from if isinstance(date_from, str) else date_from.strftime('%Y-%m-%d') if date_from else '',
            'date_to': date_to if isinstance(date_to, str) else date_to.strftime('%Y-%m-%d') if date_to else '',
        }
    }
    
    return render(request, 'parking/shift_list.html', context)

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
    
    # Get active shift
    active_shift = Shift.objects.filter(end_time__isnull=True).first()
    
    # Try to get PostgreSQL data for supplementary information if available
    db_source = 'normal'
    
    try:
        # Check if we can connect to PostgreSQL
        try:
            with connections['server_db'].cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM captureticket WHERE date_masuk >= %s", [today])
                pg_data_available = True
                logger.info("PostgreSQL connection successful for dashboard")
        except Exception as e:
            pg_data_available = False
            db_source = 'sqlite_fallback'
            logger.warning(f"PostgreSQL not available for dashboard: {str(e)}")
    except Exception:
        pg_data_available = False
        db_source = 'sqlite_fallback'
    
    # Get basic stats from Django ORM (SQLite)
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
    
    # Get real-time statistics
    real_time = {
        'entrances': ParkingSession.objects.filter(check_in_time__date=today).count(),
        'exits': ParkingSession.objects.filter(check_out_time__date=today).count(),
        'last_hour_entrances': ParkingSession.objects.filter(
            check_in_time__gte=now - timedelta(hours=1)
        ).count(),
        'last_hour_exits': ParkingSession.objects.filter(
            check_out_time__gte=now - timedelta(hours=1)
        ).count(),
    }
    
    # Today's statistics
    today_stats = {
        'total_vehicles': total_today,
        'total_revenue': today_revenue,
        'occupancy_rate': int((total_spots - available_spots) / total_spots * 100) if total_spots > 0 else 0,
        'active_sessions': active_vehicles,
    }
    
    # Get recent activity
    recent_activity = []
    for session in recent_sessions:
        recent_activity.append({
            'timestamp': session.check_in_time,
            'type': 'Check-in',
            'license_plate': session.vehicle.license_plate,
            'operator': session.created_by.username if session.created_by else 'System',
            'status': 'IN'
        })
        if session.check_out_time:
            recent_activity.append({
                'timestamp': session.check_out_time,
                'type': 'Check-out',
                'license_plate': session.vehicle.license_plate,
                'operator': session.checked_out_by.username if session.checked_out_by else 'System',
                'status': 'OUT'
            })
    
    # Sort by timestamp descending
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:10]  # Get only most recent 10
    
    # Floor status - organize by floor
    floor_status = {}
    for spot in ParkingSpot.objects.all():
        floor = spot.floor
        if floor not in floor_status:
            floor_status[floor] = {
                'total': 0,
                'occupied': 0,
                'available': 0,
                'occupancy_rate': 0
            }
        
        floor_status[floor]['total'] += 1
        if spot.status == 'AVAILABLE':
            floor_status[floor]['available'] += 1
        else:
            floor_status[floor]['occupied'] += 1
    
    # Calculate occupancy rate for each floor
    for floor in floor_status:
        if floor_status[floor]['total'] > 0:
            floor_status[floor]['occupancy_rate'] = int(floor_status[floor]['occupied'] / floor_status[floor]['total'] * 100)
    
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
        'real_time': real_time,
        'today_stats': today_stats,
        'recent_activity': recent_activity,
        'floor_status': floor_status,
        'db_source': db_source,
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
    # Check for active shift
    active_shift = get_active_shift(request.user)
    if not active_shift:
        messages.warning(request, 'No active shift found. Please start a new shift.')
        return redirect('parking:dashboard')

    try:
        # First try to use PostgreSQL
        try:
            with connections['server_db'].cursor() as cursor:
                # Get today's statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_kendaraan,
                        COUNT(CASE WHEN "DateKeluar" IS NULL THEN 1 END) as kendaraan_aktif,
                        COUNT(CASE WHEN "DateKeluar" IS NOT NULL THEN 1 END) as kendaraan_keluar,
                        COALESCE(SUM(CASE WHEN "DateKeluar" IS NOT NULL THEN "Biaya" ELSE 0 END), 0) as total_pendapatan,
                        COUNT(CASE WHEN "JenisKendaraan" = 'MOTOR' THEN 1 END) as total_motor,
                        COUNT(CASE WHEN "JenisKendaraan" = 'MOBIL' THEN 1 END) as total_mobil
                    FROM captureticket
                    WHERE DATE("DateMasuk") = CURRENT_DATE
                """)
                summary = dict(zip(
                    ['total_kendaraan', 'kendaraan_aktif', 'kendaraan_keluar', 'total_pendapatan', 'total_motor', 'total_mobil'], 
                    cursor.fetchone()
                ))

                # Get hourly statistics for today
                cursor.execute("""
                    SELECT 
                        EXTRACT(HOUR FROM "DateMasuk") as hour,
                        COUNT(*) as entries,
                        COUNT(CASE WHEN "DateKeluar" IS NOT NULL THEN 1 END) as exits
                    FROM captureticket
                    WHERE DATE("DateMasuk") = CURRENT_DATE
                    GROUP BY EXTRACT(HOUR FROM "DateMasuk")
                    ORDER BY hour
                """)
                hourly_stats = cursor.fetchall()
                
                hours = []
                entries = []
                exits = []
                for stat in hourly_stats:
                    hours.append(f"{int(stat[0]):02d}:00")
                    entries.append(stat[1])
                    exits.append(stat[2])

                # Get active tickets
                cursor.execute("""
                    SELECT 
                        id, "NoTicket", "DateMasuk", "PlatNo", 
                        "GateMasuk", "JenisKendaraan", "Operator"
                    FROM captureticket 
                    WHERE "DateKeluar" IS NULL
                    ORDER BY "DateMasuk" DESC
                """)
                columns = [col[0] for col in cursor.description]
                active_tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]

                # Get completed tickets for today
                cursor.execute("""
                    SELECT 
                        id, "NoTicket", "DateMasuk", "DateKeluar", "PlatNo", 
                        "GateMasuk", "GateKeluar", "JenisKendaraan", "Biaya", "Operator"
                    FROM captureticket 
                    WHERE "DateKeluar" IS NOT NULL 
                    AND DATE("DateMasuk") = CURRENT_DATE
                    ORDER BY "DateKeluar" DESC
                """)
                columns = [col[0] for col in cursor.description]
                completed_tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                db_source = 'postgresql'
                logger.info("Using PostgreSQL database for session list")
                
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
                    # Create table if not exists
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
                
                # Handling date format for SQLite which stores dates as strings
                today = timezone.now().date().isoformat()
                
                # Get today's statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_kendaraan,
                        COUNT(CASE WHEN DateKeluar IS NULL THEN 1 END) as kendaraan_aktif,
                        COUNT(CASE WHEN DateKeluar IS NOT NULL THEN 1 END) as kendaraan_keluar,
                        COALESCE(SUM(CASE WHEN DateKeluar IS NOT NULL THEN Biaya ELSE 0 END), 0) as total_pendapatan,
                        COUNT(CASE WHEN JenisKendaraan = 'MOTOR' THEN 1 END) as total_motor,
                        COUNT(CASE WHEN JenisKendaraan = 'MOBIL' OR JenisKendaraan = 'CAR' THEN 1 END) as total_mobil
                    FROM captureticket
                    WHERE DateMasuk LIKE ?
                """, [f"{today}%"])
                
                summary_data = cursor.fetchone()
                summary = {
                    'total_kendaraan': summary_data[0],
                    'kendaraan_aktif': summary_data[1],
                    'kendaraan_keluar': summary_data[2],
                    'total_pendapatan': summary_data[3],
                    'total_motor': summary_data[4],
                    'total_mobil': summary_data[5]
                }
                
                # Simplified hourly statistics for SQLite
                # Since we can't easily extract hour from timestamp in SQLite, 
                # we'll create a simple 24-hour structure
                hours = [f"{hour:02d}:00" for hour in range(24)]
                current_hour = timezone.now().hour
                
                # Generate dummy data or get simple hour counts
                cursor.execute("""
                    SELECT COUNT(*) FROM captureticket WHERE DateMasuk LIKE ?
                """, [f"{today}%"])
                total_entries = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM captureticket WHERE DateMasuk LIKE ? AND DateKeluar IS NOT NULL
                """, [f"{today}%"])
                total_exits = cursor.fetchone()[0]
                
                # Distribute entries and exits across hours (simple approximation)
                entries = [0] * 24
                exits = [0] * 24
                
                # Simple distribution logic - most entries in morning, most exits in evening
                for h in range(current_hour + 1):
                    if h < 12:  # Morning hours get more entries
                        entries[h] = int(total_entries * (0.7 / 12)) if total_entries > 0 else 0
                    else:  # Afternoon hours get fewer entries
                        entries[h] = int(total_entries * (0.3 / 12)) if total_entries > 0 else 0
                        
                    if h < 12:  # Morning hours get fewer exits
                        exits[h] = int(total_exits * (0.3 / 12)) if total_exits > 0 else 0
                    else:  # Afternoon hours get more exits
                        exits[h] = int(total_exits * (0.7 / 12)) if total_exits > 0 else 0
                
                # Get active tickets
                cursor.execute("""
                    SELECT 
                        id, NoTicket, DateMasuk, PlatNo, 
                        GateMasuk, JenisKendaraan, Operator
                    FROM captureticket 
                    WHERE DateKeluar IS NULL
                    ORDER BY DateMasuk DESC
                """)
                
                columns = ['id', 'NoTicket', 'DateMasuk', 'PlatNo', 'GateMasuk', 'JenisKendaraan', 'Operator']
                active_tickets = []
                
                for row in cursor.fetchall():
                    ticket = dict(zip(columns, row))
                    active_tickets.append(ticket)
                
                # Get completed tickets for today
                cursor.execute("""
                    SELECT 
                        id, NoTicket, DateMasuk, DateKeluar, PlatNo, 
                        GateMasuk, GateKeluar, JenisKendaraan, Biaya, Operator
                    FROM captureticket 
                    WHERE DateKeluar IS NOT NULL 
                    AND DateMasuk LIKE ?
                    ORDER BY DateKeluar DESC
                """, [f"{today}%"])
                
                columns = ['id', 'NoTicket', 'DateMasuk', 'DateKeluar', 'PlatNo', 'GateMasuk', 'GateKeluar', 'JenisKendaraan', 'Biaya', 'Operator']
                completed_tickets = []
                
                for row in cursor.fetchall():
                    ticket = dict(zip(columns, row))
                    completed_tickets.append(ticket)
                
                db_source = 'sqlite'
                logger.info("Using SQLite database for session list")

        context = {
            'summary': summary,
            'hourly_labels': json.dumps(hours),
            'hourly_entries': json.dumps(entries),
            'hourly_exits': json.dumps(exits),
            'active_tickets': active_tickets,
            'completed_tickets': completed_tickets,
            'active_shift': active_shift,
            'db_source': db_source,
        }

        return render(request, 'parking/session_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in session_list: {str(e)}")
        messages.error(request, f'Database error: {str(e)}')
        return redirect('parking:dashboard')

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
def get_active_tickets(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id, "NoTicket", "DateMasuk", "PlatNo", 
                    "GateMasuk", "JenisKendaraan", "Operator", "Status"
                FROM captureticket 
                WHERE "DateKeluar" IS NULL
                ORDER BY "DateMasuk" DESC
            """)
            columns = [col[0] for col in cursor.description]
            active_tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]

            tickets_data = []
            for ticket in active_tickets:
                tickets_data.append({
                    'id': ticket['id'],
                    'NoTicket': ticket['NoTicket'],
                    'DateMasuk': ticket['DateMasuk'].strftime('%Y-%m-%d %H:%M:%S') if ticket['DateMasuk'] else None,
                    'PlatNo': ticket['PlatNo'],
                    'GateMasuk': ticket['GateMasuk'] or 'GATE-1',
                    'JenisKendaraan': ticket['JenisKendaraan'],
                    'Operator': ticket['Operator'] or 'SYSTEM',
                    'Status': 'ACTIVE'
                })

            return JsonResponse({
                'status': 'success',
                'tickets': tickets_data
            })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

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

def create_test_data(request):
    try:
        # Create test vehicles
        vehicle1, _ = Vehicle.objects.get_or_create(
            license_plate="B 1234 CD",
            defaults={
                "vehicle_type": "CAR",
                "owner_name": "John Doe",
                "owner_contact": "08123456789"
            }
        )
        vehicle2, _ = Vehicle.objects.get_or_create(
            license_plate="B 5678 EF",
            defaults={
                "vehicle_type": "MOTORCYCLE",
                "owner_name": "Jane Doe",
                "owner_contact": "08234567890"
            }
        )
        vehicles = [vehicle1, vehicle2]

        # Create test parking spots
        spot1, _ = ParkingSpot.objects.get_or_create(
            spot_number="A-01",
            defaults={
                "spot_type": "CAR",
                "floor": 1,
                "status": "AVAILABLE"
            }
        )
        spot2, _ = ParkingSpot.objects.get_or_create(
            spot_number="B-01",
            defaults={
                "spot_type": "MOTORCYCLE",
                "floor": 1,
                "status": "AVAILABLE"
            }
        )
        spots = [spot1, spot2]

        # Create test user/operator if not exists
        user, created = User.objects.get_or_create(
            username="operator1",
            defaults={
                "first_name": "John",
                "last_name": "Operator",
                "email": "operator1@example.com"
            }
        )
        if created:
            user.set_password("password123")
            user.save()

        # Create test shift
        shift = Shift.objects.create(
            operator=user,
            start_time=timezone.now() - timedelta(hours=2)
        )

        # Delete any existing sessions for these spots
        ParkingSession.objects.filter(parking_spot__in=spots).delete()

        # Reset spot status
        for spot in spots:
            spot.status = "AVAILABLE"
            spot.save()

        # Create test parking sessions
        sessions = [
            ParkingSession.objects.create(
                vehicle=vehicles[0],
                parking_spot=spots[0],
                shift=shift,
                check_in_time=timezone.now() - timedelta(hours=2),
                check_out_time=timezone.now() - timedelta(hours=1),
                fee=10000,
                created_by=user,
                checked_out_by=user,
                is_active=False
            ),
            ParkingSession.objects.create(
                vehicle=vehicles[1],
                parking_spot=spots[1],
                shift=shift,
                check_in_time=timezone.now() - timedelta(minutes=30),
                created_by=user,
                is_active=True
            )
        ]

        # Update spot status for active session
        spots[1].status = "OCCUPIED"
        spots[1].save()

        return JsonResponse({
            'status': 'success',
            'message': 'Test data created successfully',
            'data': {
                'vehicles': [v.license_plate for v in vehicles],
                'spots': [s.spot_number for s in spots],
                'sessions': len(sessions)
            }
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required(login_url='parking:login')
def parking_spot_edit(request, spot_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        spot = ParkingSpot.objects.get(id=spot_id)
        
        # Get active session for this spot if any
        active_session = ParkingSession.objects.filter(
            parking_spot=spot,
            check_out_time__isnull=True,
            is_active=True
        ).first()
        
        # Validate required fields
        floor = request.POST.get('floor')
        spot_number = request.POST.get('spot_number')
        spot_type = request.POST.get('spot_type')
        
        if not all([floor, spot_number, spot_type]):
            return JsonResponse({
                'success': False,
                'message': 'Semua field harus diisi'
            })
            
        # Validate spot type
        if spot_type not in [t[0] for t in ParkingSpot.SPOT_TYPES]:
            return JsonResponse({
                'success': False,
                'message': 'Tipe spot tidak valid'
            })
        
        # If spot is occupied, validate changes
        if active_session:
            # Only check spot number uniqueness if it's being changed
            if spot_number != spot.spot_number:
                return JsonResponse({
                    'success': False,
                    'message': f'Tidak dapat mengubah nomor spot yang sedang digunakan oleh kendaraan {active_session.vehicle.license_plate}'
                })
            
            # Validate vehicle type compatibility
            vehicle_type = active_session.vehicle.vehicle_type
            if spot_type != vehicle_type:
                return JsonResponse({
                    'success': False,
                    'message': f'Tidak dapat mengubah tipe spot menjadi {spot_type} karena sedang digunakan oleh kendaraan tipe {vehicle_type}'
                })
        else:
            # Check if spot number is unique (excluding current spot)
            if ParkingSpot.objects.exclude(id=spot_id).filter(spot_number=spot_number).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Nomor spot sudah digunakan'
                })
        
        # Update spot
        spot.floor = floor
        spot.spot_number = spot_number
        spot.spot_type = spot_type
        spot.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Spot parkir berhasil diupdate'
        })
    except ParkingSpot.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': 'Spot tidak ditemukan'
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False, 
            'message': f'Input tidak valid: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error: {str(e)}'
        }, status=500)

@login_required(login_url='parking:login')
def parking_spot_delete(request, spot_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        spot = ParkingSpot.objects.get(id=spot_id)
        
        # Check for active parking sessions
        active_session = ParkingSession.objects.filter(
            parking_spot=spot,
            check_out_time__isnull=True,
            is_active=True
        ).first()
        
        if active_session:
            return JsonResponse({
                'success': False, 
                'message': f'Tidak dapat menghapus spot yang sedang digunakan oleh kendaraan {active_session.vehicle.license_plate}'
            })
        
        # Check if spot has completed sessions
        if ParkingSession.objects.filter(parking_spot=spot, check_out_time__isnull=False).exists():
            return JsonResponse({
                'success': False,
                'message': 'Tidak dapat menghapus spot yang memiliki riwayat parkir'
            })
        
        spot.delete()
        return JsonResponse({
            'success': True,
            'message': 'Spot parkir berhasil dihapus'
        })
    except ParkingSpot.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': 'Spot tidak ditemukan'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error: {str(e)}'
        }, status=500)

@login_required(login_url='parking:login')
def real_parking_data(request):
    try:
        with connection.cursor() as cursor:
            # Get active parking sessions
            cursor.execute("""
                SELECT 
                    "Id",
                    "NoTicket",
                    "DateMasuk",
                    "PlatNo",
                    "JenisKendaraan",
                    "GateMasuk",
                    "Status"
                FROM "CaptureTickets"
                WHERE "Status" = 'MASUK'
                ORDER BY "DateMasuk" DESC
            """)
            columns = [col[0] for col in cursor.description]
            active_tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # Get completed sessions for today
            cursor.execute("""
                SELECT 
                    "Id",
                    "NoTicket",
                    "DateMasuk",
                    "DateKeluar",
                    "PlatNo",
                    "JenisKendaraan",
                    "GateMasuk",
                    "GateKeluar",
                    "Biaya",
                    "Status"
                FROM "CaptureTickets"
                WHERE "Status" = 'KELUAR' 
                AND DATE("DateKeluar") = CURRENT_DATE
                ORDER BY "DateKeluar" DESC
            """)
            columns = [col[0] for col in cursor.description]
            completed_tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # Get summary statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_kendaraan,
                    COUNT(CASE WHEN "Status" = 'MASUK' THEN 1 END) as kendaraan_aktif,
                    COUNT(CASE WHEN "Status" = 'KELUAR' AND DATE("DateKeluar") = CURRENT_DATE THEN 1 END) as kendaraan_keluar,
                    COALESCE(SUM(CASE WHEN "Status" = 'KELUAR' AND DATE("DateKeluar") = CURRENT_DATE THEN "Biaya" ELSE 0 END), 0) as total_pendapatan
                FROM "CaptureTickets"
                WHERE DATE("DateMasuk") = CURRENT_DATE OR (DATE("DateKeluar") = CURRENT_DATE AND "Status" = 'KELUAR')
            """)
            summary = dict(zip(['total_kendaraan', 'kendaraan_aktif', 'kendaraan_keluar', 'total_pendapatan'], cursor.fetchone()))

        return render(request, 'parking/real_parking_data.html', {
            'active_tickets': active_tickets,
            'completed_tickets': completed_tickets,
            'summary': summary
        })

    except Exception as e:
        messages.error(request, f'Database error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'Error mengambil data: {str(e)}'
        }, status=500)

@login_required(login_url='parking:login')
def entry_monitor(request):
    """View for monitoring parking entries from the client gate"""
    return render(request, 'parking/entry_monitor.html')

def entry_monitor_data(request):
    """API endpoint for getting real-time entry data"""
    try:
        # Get current date for filtering
        today = timezone.now().date()
        
        # Get statistics
        statistics = {
            'total_today': Captureticket.objects.filter(
                date_masuk__date=today
            ).count(),
            'last_hour': Captureticket.objects.filter(
                date_masuk__gte=timezone.now() - timedelta(hours=1)
            ).count(),
        }
        
        # Get recent entries (last 50)
        recent_entries = []
        entries = Captureticket.objects.filter(
            date_masuk__date=today
        ).order_by('-date_masuk')[:50]
        
        for entry in entries:
            recent_entries.append({
                'timestamp': entry.date_masuk.isoformat(),
                'ticket_id': entry.NoTicket,
                'plate_number': entry.PlatNo,
                'gate': entry.GateMasuk,
                'operator': entry.Operator if hasattr(entry, 'Operator') else 'SYSTEM',
                'status': 'SUCCESS',
                'image': entry.image_url if hasattr(entry, 'image_url') else None
            })
        
        # Check client status (192.168.2.7)
        client_status = 'DISCONNECTED'
        gate_status = 'OFFLINE'
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # 1 second timeout
            result = sock.connect_ex(('192.168.2.7', 80))
            if result == 0:
                client_status = 'CONNECTED'
                gate_status = 'ONLINE'
            sock.close()
        except:
            pass
        
        return JsonResponse({
            'statistics': statistics,
            'recent_entries': recent_entries,
            'status': {
                'gate': gate_status,
                'client': client_status
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
