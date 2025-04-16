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
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('captureticket', 'parkingsession', 'vehicle', 'parkingspot', 'shift')
    """)
    
    tables = cur.fetchall()
    print("Tables found:")
    for table in tables:
        print(table[0])
        
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {str(e)}")
