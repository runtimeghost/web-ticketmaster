"""Admin dashboard, event creation, reports, and resale management."""

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from psycopg.rows import dict_row

from utils import admin_required

admin_bp = Blueprint('admin', __name__)

# Note: This blueprint is registered with url_prefix='/admin'.


# ── Dashboard ───────────────────────────────────────────────────────


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Aggregate stats
            cur.execute("SELECT COUNT(*) AS event_count FROM events")
            event_count = cur.fetchone()['event_count']

            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total_revenue FROM payments"
            )
            total_revenue = cur.fetchone()['total_revenue']

            cur.execute(
                "SELECT COALESCE(SUM(vip_qty + normal_qty + student_qty), 0) AS total_tickets_sold FROM bookings WHERE status = 'confirmed'"
            )
            total_tickets_sold = cur.fetchone()['total_tickets_sold']

            cur.execute(
                "SELECT COUNT(*) AS pending_resales FROM resale_requests WHERE status = 'pending'"
            )
            pending_resales = cur.fetchone()['pending_resales']

            stats = {
                'event_count': event_count,
                'total_revenue': total_revenue,
                'total_tickets_sold': total_tickets_sold,
                'pending_resales': pending_resales,
            }

            # Recent bookings
            cur.execute(
                """
                SELECT u.username, e.title AS event_title,
                       (b.vip_qty + b.normal_qty + b.student_qty) AS quantity, 
                       b.total_price, b.status, b.created_at
                  FROM bookings b
                  JOIN users  u ON u.id = b.user_id
                  JOIN events e ON e.id = b.event_id
                 ORDER BY b.created_at DESC
                 LIMIT 10
                """
            )
            recent_bookings = cur.fetchall()

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_bookings=recent_bookings,
    )


# ── Create event (form) ────────────────────────────────────────────


@admin_bp.route('/events/new')
@admin_required
def new_event():
    return render_template('events/create.html')


# ── Create event (submit) ──────────────────────────────────────────


@admin_bp.route('/events', methods=['POST'])
@admin_required
def create_event():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    venue = request.form.get('venue', '').strip()
    event_date = request.form.get('event_date', '').strip()
    event_time = request.form.get('event_time', '').strip()
    image_url = request.form.get('image_url', '').strip()

    try:
        vip_seats = int(request.form.get('vip_seats', '0'))
        vip_price = float(request.form.get('vip_price', '0'))
        normal_seats = int(request.form.get('normal_seats', '0'))
        normal_price = float(request.form.get('normal_price', '0'))
        student_seats = int(request.form.get('student_seats', '0'))
        student_price = float(request.form.get('student_price', '0'))
    except (ValueError, TypeError):
        flash('Invalid seats or price value.', 'error')
        return redirect(url_for('admin.new_event'))

    if not all([title, venue, event_date, event_time]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('admin.new_event'))

    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO events
                    (title, description, venue, event_date, event_time,
                     vip_seats, vip_available, vip_price,
                     normal_seats, normal_available, normal_price,
                     student_seats, student_available, student_price,
                     image_url, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    title, description, venue, event_date, event_time,
                    vip_seats, vip_seats, vip_price,
                    normal_seats, normal_seats, normal_price,
                    student_seats, student_seats, student_price,
                    image_url or None, session['user_id'],
                ),
            )
            new_event = cur.fetchone()

        conn.commit()

    flash('Event created successfully!', 'success')
    return redirect(url_for('events.event_detail', event_id=new_event['id']))


# ── Reports ─────────────────────────────────────────────────────────


@admin_bp.route('/reports')
@admin_required
def reports():
    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT e.id        AS event_id,
                       e.title     AS event_title,
                       e.event_date,
                       (e.vip_seats + e.normal_seats + e.student_seats) AS total_seats,
                       COALESCE(SUM(b.vip_qty + b.normal_qty + b.student_qty), 0) AS tickets_sold,
                       COALESCE(SUM(b.total_price), 0) AS revenue
                  FROM events e
                  LEFT JOIN bookings b
                         ON b.event_id = e.id
                        AND b.status = 'confirmed'
                 GROUP BY e.id, e.title, e.event_date, e.vip_seats, e.normal_seats, e.student_seats
                 ORDER BY e.event_date ASC
                """
            )
            report_data = cur.fetchall()

    total_revenue = sum(float(r['revenue']) for r in report_data)
    total_tickets = sum(int(r['tickets_sold']) for r in report_data)

    return render_template(
        'admin/reports.html',
        reports=report_data,
        total_revenue=total_revenue,
        total_tickets=total_tickets,
    )


# ── Resale management ──────────────────────────────────────────────


@admin_bp.route('/resale')
@admin_required
def resale_requests():
    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT rr.id,
                       t.ticket_code,
                       e.title    AS event_title,
                       u.username AS seller_username,
                       rr.price,
                       rr.status,
                       rr.created_at
                  FROM resale_requests rr
                  JOIN tickets  t ON t.id  = rr.ticket_id
                  JOIN bookings b ON b.id  = t.booking_id
                  JOIN events   e ON e.id  = b.event_id
                  JOIN users    u ON u.id  = rr.seller_id
                 ORDER BY rr.created_at DESC
                """
            )
            requests_list = cur.fetchall()

    return render_template('admin/resale_requests.html', requests=requests_list)


@admin_bp.route('/resale/<int:resale_id>/approve', methods=['POST'])
@admin_required
def approve_resale(resale_id: int):
    with current_app.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE resale_requests SET status = 'approved' WHERE id = %s",
                (resale_id,),
            )
        conn.commit()

    flash('Resale request approved.', 'success')
    return redirect(url_for('admin.resale_requests'))


@admin_bp.route('/resale/<int:resale_id>/reject', methods=['POST'])
@admin_required
def reject_resale(resale_id: int):
    with current_app.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE resale_requests SET status = 'rejected' WHERE id = %s",
                (resale_id,),
            )
        conn.commit()

    flash('Resale request rejected.', 'info')
    return redirect(url_for('admin.resale_requests'))
