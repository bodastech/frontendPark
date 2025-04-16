import serial
import win32print
import time
import psycopg2
from datetime import datetime

# Printer Configuration
PRINTER_HANDLE = None

# Database Configuration
DB_HOST = "192.168.2.6"
DB_NAME = "parkir2"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

# Tarif Configuration
TARIF_CONFIG = {
    'Motor': {
        'base_fee': 2500,    # Tarif dasar 1 jam pertama
        'next_fee': 1000,    # Tarif per jam berikutnya
    },
    'Mobil': {
        'base_fee': 4000,    # Tarif dasar 1 jam pertama
        'next_fee': 2000,    # Tarif per jam berikutnya
    }
}

def calculate_fee(entry_time, vehicle_type='Motor'):
    """Calculate parking fee based on duration and vehicle type"""
    now = datetime.now()
    duration = now - entry_time
    hours = duration.total_seconds() / 3600
    
    tarif = TARIF_CONFIG.get(vehicle_type, TARIF_CONFIG['Motor'])
    
    # Perhitungan tarif
    if hours <= 1:
        return tarif['base_fee']
    else:
        additional_hours = int(hours)
        return tarif['base_fee'] + (additional_hours - 1) * tarif['next_fee']

def format_duration(entry_time):
    """Format duration for printing"""
    duration = datetime.now() - entry_time
    hours = int(duration.total_seconds() // 3600)
    minutes = int((duration.total_seconds() % 3600) // 60)
    return f"{hours} jam {minutes} menit"

def print_exit_ticket(ticket_data):
    """Print exit ticket using ESC/POS commands"""
    global PRINTER_HANDLE
    try:
        # Get the default printer
        printer_name = win32print.GetDefaultPrinter()
        print(f"Printing to: {printer_name}")

        # Open the printer
        PRINTER_HANDLE = win32print.OpenPrinter(printer_name)

        # Start a print job
        job_id = win32print.StartDocPrinter(PRINTER_HANDLE, 1, ("Exit Ticket", None, "RAW"))
        win32print.StartPagePrinter(PRINTER_HANDLE)

        # Format ticket content
        ticket_content = (
            f"RSI BNA PARKING\n"
            f"====================\n"
            f"TIKET KELUAR\n"
            f"====================\n"
            f"No. Tiket: {ticket_data['ticket_number']}\n"
            f"Plat: {ticket_data['plate_number']}\n"
            f"Jenis: {ticket_data['vehicle_type']}\n"
            f"-------------------\n"
            f"Masuk  : {ticket_data['entry_time'].strftime('%Y-%m-%d %H:%M')}\n"
            f"Keluar : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Durasi : {format_duration(ticket_data['entry_time'])}\n"
            f"-------------------\n"
            f"Tarif  : Rp {ticket_data['fee']:,}\n"
            f"====================\n"
            f"Terima Kasih\n"
            f"\n\n\n"  # Extra lines for spacing after cut
        ).encode()

        # ESC/POS commands for ticket printing
        esc_pos_commands = (
            b"\x1B\x40" +          # Initialize printer
            b"\x1B\x61\x01" +      # Center alignment
            ticket_content +        # Ticket content
            b"\x1D\x56\x41\x00"    # Auto-cut command
        )

        # Send the ESC/POS commands to the printer
        win32print.WritePrinter(PRINTER_HANDLE, esc_pos_commands)

        # End the print job
        win32print.EndPagePrinter(PRINTER_HANDLE)
        win32print.EndDocPrinter(PRINTER_HANDLE)

        print("Exit ticket printed successfully!")
        
    except Exception as e:
        print(f"Error printing exit ticket: {e}")
        raise
    finally:
        # Close the printer handle
        if PRINTER_HANDLE:
            try:
                win32print.ClosePrinter(PRINTER_HANDLE)
                PRINTER_HANDLE = None
            except Exception as e:
                print(f"Error closing printer handle: {e}")

def get_ticket_data(ticket_number):
    """Get ticket data from database"""
    connection = None
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = connection.cursor()

        # Get ticket data
        query = """
            SELECT c.plat_no, c.date_masuk, c.vehicle_type 
            FROM captureticket c
            WHERE c.plat_no = %s AND c.status = 'MASUK'
        """
        cursor.execute(query, (ticket_number,))
        result = cursor.fetchone()

        if not result:
            raise Exception("Ticket not found or already processed")

        plate_number, entry_time, vehicle_type = result
        
        # Calculate fee
        fee = calculate_fee(entry_time, vehicle_type)

        return {
            'ticket_number': ticket_number,
            'plate_number': plate_number,
            'entry_time': entry_time,
            'vehicle_type': vehicle_type,
            'fee': fee
        }

    except Exception as e:
        print(f"Error getting ticket data: {e}")
        raise
    finally:
        if connection:
            connection.close()

def update_ticket_status(ticket_number, fee):
    """Update ticket status in database"""
    connection = None
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = connection.cursor()

        # Update ticket status
        query = """
            UPDATE captureticket 
            SET status = 'KELUAR',
                date_keluar = %s,
                biaya = %s
            WHERE plat_no = %s AND status = 'MASUK'
        """
        cursor.execute(query, (datetime.now(), fee, ticket_number))
        connection.commit()

    except Exception as e:
        print(f"Error updating ticket status: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()

def process_exit_ticket(ticket_number):
    """Process exit ticket - main function"""
    try:
        # Step 1: Get ticket data
        ticket_data = get_ticket_data(ticket_number)
        
        # Step 2: Print exit ticket
        print_exit_ticket(ticket_data)
        
        # Step 3: Update ticket status
        update_ticket_status(ticket_number, ticket_data['fee'])
        
        print(f"Exit processed successfully for ticket {ticket_number}")
        return ticket_data
        
        except Exception as e:
        print(f"Error processing exit: {e}")
        raise

if __name__ == "__main__":
    try:
        # Test with a ticket number
        ticket_number = input("Enter ticket number: ")
        process_exit_ticket(ticket_number)
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
