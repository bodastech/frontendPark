from django.apps import AppConfig
import os
import logging

logger = logging.getLogger(__name__)


class ParkingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parking'

    def ready(self):
        # Only run when server is actually starting, not during Django checks
        if os.environ.get('RUN_MAIN', None) != 'true':
            return
            
        # Initialize SQLite database
        try:
            # Run our setup_sqlite command
            from django.core.management import call_command
            logger.info("Initializing SQLite database for offline use...")
            call_command('setup_sqlite')
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {str(e)}")
