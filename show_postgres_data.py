import psycopg2
from datetime import datetime, timedelta
import locale

# Set locale ke Indonesia
locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')

def format_money(amount):
    return locale.currency(amount, grouping=True, symbol='Rp')

def format_duration(minutes):
    if minutes < 60:
        return f"{minutes} menit"
    hours = minutes / 60
    return f"{hours:.1f} jam"

def show_postgres_data():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host='192.168.2.6',
            database='parkir2',
            user='postgres',
            password='postgres'
        )
        
        print("\n=== SISTEM PARKIR - DATA REAL TIME ===")
        print(f"Laporan dibuat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 70)
        
        with conn.cursor() as cursor:
            # Get active tickets (MASUK)
            print("\n=== KENDARAAN MASUK ===")
            cursor.execute("""
                SELECT "Id", "TicketNumber", "CaptureTime", "Status", "plate_number", "vehicle_type", "ImagePath"
                FROM "CaptureTickets"
                WHERE "Status" = 'MASUK'
                ORDER BY "CaptureTime" DESC;
            """)
            
            active_tickets = cursor.fetchall()
            print(f"\nTotal Kendaraan Masuk: {len(active_tickets)}")
            
            if active_tickets:
                print("\nDetail Kendaraan Masuk:")
                for ticket in active_tickets:
                    print("\n" + "-" * 40)
                    print(f"ID: {ticket[0]}")
                    print(f"No. Tiket: {ticket[1]}")
                    print(f"Waktu Masuk: {ticket[2]}")
                    print(f"Status: {ticket[3]}")
                    print(f"Plat Nomor: {ticket[4] or '-'}")
                    print(f"Jenis: {ticket[5] or '-'}")
                    print(f"Foto: {ticket[6]}")

            # Get completed tickets (KELUAR)
            print("\n=== KENDARAAN KELUAR HARI INI ===")
            cursor.execute("""
                SELECT "Id", "TicketNumber", "CaptureTime", "Status", "plate_number", "vehicle_type"
                FROM "CaptureTickets"
                WHERE "Status" = 'KELUAR'
                AND DATE("CaptureTime") = CURRENT_DATE
                ORDER BY "CaptureTime" DESC;
            """)
            
            completed_tickets = cursor.fetchall()
            print(f"\nTotal Kendaraan Keluar: {len(completed_tickets)}")
            
            if completed_tickets:
                print("\nDetail Kendaraan Keluar:")
                for ticket in completed_tickets:
                    print("\n" + "-" * 40)
                    print(f"ID: {ticket[0]}")
                    print(f"No. Tiket: {ticket[1]}")
                    print(f"Waktu: {ticket[2]}")
                    print(f"Status: {ticket[3]}")
                    print(f"Plat Nomor: {ticket[4] or '-'}")
                    print(f"Jenis: {ticket[5] or '-'}")

            # Get daily statistics
            print("\n=== STATISTIK HARI INI ===")
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_kendaraan,
                    COUNT(CASE WHEN "Status" = 'MASUK' THEN 1 END) as kendaraan_masuk,
                    COUNT(CASE WHEN "Status" = 'KELUAR' THEN 1 END) as kendaraan_keluar
                FROM "CaptureTickets"
                WHERE DATE("CaptureTime") = CURRENT_DATE;
            """)
            
            stats = cursor.fetchone()
            print(f"\nTotal Kendaraan: {stats[0]}")
            print(f"Kendaraan Masuk: {stats[1]}")
            print(f"Kendaraan Keluar: {stats[2]}")

        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

def show_table_info():
    try:
        conn = psycopg2.connect(
            dbname="parkir2",
            user="postgres",
            password="postgres",
            host="192.168.2.6",
            port="5432"
        )
        
        cur = conn.cursor()
        
        print("\n=== STRUKTUR TABEL ===")
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'CaptureTickets'
            ORDER BY ordinal_position;
        """)
        columns = cur.fetchall()
        for col in columns:
            print(f"Kolom: {col[0]}, Tipe: {col[1]}, Panjang: {col[2]}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    show_postgres_data()
    show_table_info()
