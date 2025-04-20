from django.core.management.base import BaseCommand
from django.db import connections, transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Set up SQLite database for offline mode'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up SQLite database...'))
        self.setup_captureticket_table()
        self.copy_data_if_possible()
        self.stdout.write(self.style.SUCCESS('SQLite database setup complete!'))
    
    def setup_captureticket_table(self):
        """Create Captureticket table in SQLite if it doesn't exist"""
        with connections['default'].cursor() as cursor:
            # Check if table exists
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='captureticket'
            ''')
            table_exists = cursor.fetchone()
            
            if not table_exists:
                self.stdout.write('Creating captureticket table in SQLite...')
                cursor.execute('''
                    CREATE TABLE captureticket (
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
                ''')
                self.stdout.write(self.style.SUCCESS('Table created successfully!'))
            else:
                self.stdout.write('Captureticket table already exists in SQLite.')
    
    def copy_data_if_possible(self):
        """Try to copy data from PostgreSQL to SQLite if PostgreSQL is available"""
        try:
            self.stdout.write('Attempting to copy data from PostgreSQL to SQLite...')
            
            # Try connecting to PostgreSQL
            with connections['server_db'].cursor() as pg_cursor:
                # Query to get all the data
                pg_cursor.execute('''
                    SELECT  
                        id, NoTicket, PlatNo, DateMasuk, DateKeluar, 
                        GateMasuk, GateKeluar, JenisKendaraan, Biaya, 
                        Operator, Status
                    FROM captureticket
                ''')
                records = pg_cursor.fetchall()
                
                if records:
                    self.stdout.write(f'Found {len(records)} records to copy')
                    
                    # Get the column names
                    columns = [col[0] for col in pg_cursor.description]
                    
                    # Now insert into SQLite
                    with transaction.atomic(using='default'):
                        with connections['default'].cursor() as sqlite_cursor:
                            # Clear existing data
                            sqlite_cursor.execute('DELETE FROM captureticket')
                            
                            # Prepare placeholders for SQLite insert
                            placeholders = ', '.join(['?' for _ in columns])
                            columns_str = ', '.join(columns)
                            
                            # Insert records
                            for record in records:
                                sqlite_cursor.execute(
                                    f'INSERT INTO captureticket ({columns_str}) VALUES ({placeholders})',
                                    record
                                )
                    
                    self.stdout.write(self.style.SUCCESS(f'Successfully copied {len(records)} records to SQLite'))
                else:
                    self.stdout.write('No records found in PostgreSQL to copy')
        
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not copy data: {str(e)}'))
            self.stdout.write(self.style.WARNING('Continuing with empty SQLite database')) 