# Parking Management System 

## Offline Mode with SQLite

This application is configured to work with a PostgreSQL database server by default. However, it now includes a SQLite fallback mechanism when the server is down or unavailable.

### How It Works

1. The application tries to connect to the PostgreSQL server first
2. If the connection fails, it automatically falls back to using the local SQLite database
3. Data is synchronized between both databases when possible

### Setup

When the application starts, it automatically:
1. Checks if the SQLite database is set up
2. Creates necessary tables if they don't exist
3. Attempts to copy data from PostgreSQL to SQLite if possible

### Manual Setup

You can manually initialize the SQLite database with:

```
python manage.py setup_sqlite
```

### Databases

The application uses two databases:
- `default`: SQLite database for local/offline operation
- `server_db`: PostgreSQL database for normal online operation

### API Endpoints

All API endpoints will work regardless of which database is being used. The responses will include a `database` field to indicate which database was used to retrieve the data.

### Synchronization

When the PostgreSQL server becomes available again, any data that was added to SQLite while offline will need to be manually synchronized. This feature will be added in a future update.

## Installation and Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Start the server: `python manage.py runserver`

## Requirements

- Python 3.8+
- Django 5.0+
- PostgreSQL 12+ (for online mode)
- SQLite 3 (for offline mode) 