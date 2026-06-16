import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'postgres')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD')

db_url = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

def drop_all():
    print("Connecting to drop tables...")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            tables = [
                'payments', 'resale_requests', 'tickets', 
                'ticket_locks', 'bookings', 'events', 'users'
            ]
            for t in tables:
                print(f"Dropping {t}...")
                cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
        conn.commit()
    print("All tables dropped successfully.")

if __name__ == '__main__':
    drop_all()
