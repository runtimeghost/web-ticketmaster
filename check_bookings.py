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
        cur.execute("SELECT id, user_id, event_id, vip_qty, normal_qty, student_qty, total_price, status, created_at FROM bookings ORDER BY created_at DESC")
        rows = cur.fetchall()
        print(f"Total bookings: {len(rows)}")
        for r in rows:
            print(r)
