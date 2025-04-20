from django.urls import path
from . import views
from . import api

app_name = 'parking'

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/add/', views.vehicle_add, name='vehicle_add'),
    path('spots/', views.parking_spot_list, name='parking_spot_list'),
    path('spots/add/', views.parking_spot_add, name='parking_spot_add'),
    path('spots/<int:spot_id>/edit/', views.parking_spot_edit, name='parking_spot_edit'),
    path('spots/<int:spot_id>/delete/', views.parking_spot_delete, name='parking_spot_delete'),
    path('check-in/', views.check_in, name='check_in'),
    path('check-out/', views.check_out_view, name='check_out'),
    path('sessions/', views.session_list, name='session_list'),
    path('test-captureticket/', views.test_captureticket, name='test_captureticket'),
    path('server-tickets/', views.view_captureticket, name='view_captureticket'),
    path('test-connection/', views.test_connection, name='test_connection'),
    path('create-test-data/', views.create_test_data, name='create_test_data'),
    path('shifts/', views.shift_list, name='shift_list'),
    path('shifts/<int:shift_id>/', views.shift_report, name='shift_report'),
    path('shifts/<int:shift_id>/export/', views.export_shift_report, name='export_shift_report'),
    path('start-shift/', views.start_shift, name='start_shift'),
    path('end-shift/', views.end_shift, name='end_shift'),
    path('real-parking-data/', views.real_parking_data, name='real_parking_data'),
    path('entry-monitor/', views.entry_monitor, name='entry_monitor'),
    path('api/entry-monitor-data/', views.entry_monitor_data, name='entry_monitor_data'),
    
    # API endpoints
    path('api/capture-tickets/', api.capture_tickets, name='api_capture_tickets'),
    path('api/exit/tickets/', api.exit_tickets, name='api_exit_tickets'),
    path('api/process-exit/', api.process_exit, name='process_exit'),
    path('api/process-entry/', api.process_entry, name='process_entry'),
    path('api/get-active-tickets/', api.get_active_tickets, name='get_active_tickets'),
    path('api/dashboard/', api.dashboard, name='api_dashboard'),
    path('api/active-tickets/', views.get_active_tickets, name='get_active_tickets'),
] 