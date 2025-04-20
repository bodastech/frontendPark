import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_management.settings')
django.setup()

from parking.models import Captureticket

tickets = Captureticket.objects.all().order_by('id')
print(f"Total records: {tickets.count()}\n")
print("All records:")
for ticket in tickets:
    print(f"ID: {ticket.id}")
    print(f"Plate: {ticket.plat_no}")
    print(f"Entry: {ticket.date_masuk}")
    print(f"Exit: {ticket.date_keluar}")
    print(f"Status: {ticket.status}")
    print(f"Fee: {ticket.biaya}")
    print("-" * 50) 