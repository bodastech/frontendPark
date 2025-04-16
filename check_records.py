import psycopg2

try:
    conn = psycopg2.connect(
        host='192.168.2.6',
        port='5432',
        dbname='parkir2',
        user='postgres',
        password='postgres'
    )
    
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as total_records,
               MIN(created_at) as first_record,
               MAX(created_at) as last_record
        FROM captureticket
    """)
    
    result = cur.fetchone()
    
    print(f"Total records in captureticket: {result[0]}")
    print(f"First record: {result[1]}")
    print(f"Last record: {result[2]}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {str(e)}")
