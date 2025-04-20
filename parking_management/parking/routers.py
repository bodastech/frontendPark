import psycopg2
from django.conf import settings
import logging
from django.utils import timezone

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseRouter:
    def __init__(self):
        self.server_db_available = True
        self.check_server_db_connection()
    
    def check_server_db_connection(self):
        """Check if the PostgreSQL server is available."""
        try:
            db_settings = settings.DATABASES['server_db']
            conn = psycopg2.connect(
                dbname=db_settings['NAME'],
                user=db_settings['USER'],
                password=db_settings['PASSWORD'],
                host=db_settings['HOST'],
                port=db_settings['PORT'],
                connect_timeout=3  # Short timeout to avoid long waits
            )
            conn.close()
            self.server_db_available = True
            logger.info("PostgreSQL server is available")
        except Exception as e:
            self.server_db_available = False
            logger.warning(f"PostgreSQL server is not available: {str(e)}")
    
    def db_for_read(self, model, **hints):
        """Route read operations to the appropriate database."""
        if model._meta.app_label == 'parking' and model.__name__ == 'Captureticket':
            # Check connection periodically (not on every request to avoid performance issues)
            if not self.server_db_available and not hasattr(self, 'last_check') or \
                    (hasattr(self, 'last_check') and (timezone.now() - self.last_check).total_seconds() > 300):
                self.check_server_db_connection()
                self.last_check = timezone.now()
            
            # If PostgreSQL is available, use it; otherwise, fall back to SQLite
            if self.server_db_available:
                return 'server_db'
        return 'default'

    def db_for_write(self, model, **hints):
        """Route write operations to the appropriate database."""
        if model._meta.app_label == 'parking' and model.__name__ == 'Captureticket':
            # Check connection periodically
            if not self.server_db_available and not hasattr(self, 'last_check') or \
                    (hasattr(self, 'last_check') and (timezone.now() - self.last_check).total_seconds() > 300):
                self.check_server_db_connection()
                self.last_check = timezone.now()
            
            # If PostgreSQL is available, use it; otherwise, fall back to SQLite
            if self.server_db_available:
                return 'server_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # For Captureticket model, don't run migrations on either database
        # since it's using direct SQL for PostgreSQL and we'll handle
        # the SQLite table creation manually
        if app_label == 'parking' and model_name == 'captureticket':
            return False
        return True 