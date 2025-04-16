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
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'captureticket'
        ORDER BY ordinal_position
    """)
    
    print("Columns in captureticket table:")
    for column in cur.fetchall():
        print(column[0])
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {str(e)}")
