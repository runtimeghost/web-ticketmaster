import psycopg
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'postgres')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD')

db_url = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        # Keep only the first booking (id=1), delete duplicates (id=2 and id=3)
        cur.execute("DELETE FROM payments WHERE booking_id IN (2, 3)")
        cur.execute("DELETE FROM tickets WHERE booking_id IN (2, 3)")
        cur.execute("DELETE FROM bookings WHERE id IN (2, 3)")
        print("Deleted duplicate bookings 2 and 3.")
        
        # Verify
        cur.execute("SELECT id, user_id, event_id, total_price, status FROM bookings")
        for r in cur.fetchall():
            print(r)
    conn.commit()
    print("Done.")
