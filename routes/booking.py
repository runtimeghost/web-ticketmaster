"""Booking routes – lock → checkout → pay / cancel, history, ticket view."""

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from psycopg.rows import dict_row

from utils import generate_seat_label, generate_ticket_code, login_required

booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/events/<int:event_id>/lock', methods=['POST'])
@login_required
def lock_seats(event_id: int):
    user_id = session['user_id']
    vip_qty = int(request.form.get('vip_qty', 0))
    normal_qty = int(request.form.get('normal_qty', 0))
    student_qty = int(request.form.get('student_qty', 0))

    if vip_qty + normal_qty + student_qty == 0:
        flash('Please select at least one ticket.', 'error')
        return redirect(url_for('events.event_detail', event_id=event_id))

    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT event_date, event_time, vip_available, normal_available, student_available FROM events WHERE id = %s",
                (event_id,),
            )
            event = cur.fetchone()

            if event is None:
                flash('Event not found.', 'error')
                return redirect(url_for('events.list_events'))
                
            from datetime import datetime
            now = datetime.now()
            if event['event_date'] < now.date() or (event['event_date'] == now.date() and event['event_time'] < now.time()):
                flash('This event has already taken place.', 'error')
                return redirect(url_for('events.event_detail', event_id=event_id))

            if (event['vip_available'] < vip_qty or 
                event['normal_available'] < normal_qty or 
                event['student_available'] < student_qty):
                flash('Not enough seats available for selected types.', 'error')
                return redirect(url_for('events.event_detail', event_id=event_id))

            cur.execute(
                """
                UPDATE events
                   SET vip_available = vip_available - %s,
                       normal_available = normal_available - %s,
                       student_available = student_available - %s
                 WHERE id = %s
                """,
                (vip_qty, normal_qty, student_qty, event_id),
            )

            cur.execute(
                """
                INSERT INTO ticket_locks (user_id, event_id, vip_qty, normal_qty, student_qty, expires_at)
                VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL '5 minutes')
                RETURNING id
                """,
                (user_id, event_id, vip_qty, normal_qty, student_qty),
            )
            lock = cur.fetchone()

        conn.commit()

    return redirect(url_for('booking.checkout', lock_id=lock['id']))

@booking_bp.route('/checkout/<int:lock_id>')
@login_required
def checkout(lock_id: int):
    user_id = session['user_id']
    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT tl.*, e.title AS event_title, 
                       e.vip_price, e.normal_price, e.student_price,
                       e.venue AS event_venue, e.event_date, e.event_time,
                       e.image_url,
                       EXTRACT(EPOCH FROM (tl.expires_at - NOW())) AS remaining_seconds
                  FROM ticket_locks tl
                  JOIN events e ON e.id = tl.event_id
                 WHERE tl.id = %s
                """,
                (lock_id,),
            )
            lock = cur.fetchone()

    if lock is None or lock['user_id'] != user_id:
        flash('Lock not found or access denied.', 'error')
        return redirect(url_for('events.list_events'))

    if lock['remaining_seconds'] < 0:
        flash('Your reservation has expired. Please try again.', 'error')
        return redirect(url_for('events.list_events'))

    total_price = (
        float(lock['vip_price']) * lock['vip_qty'] +
        float(lock['normal_price']) * lock['normal_qty'] +
        float(lock['student_price']) * lock['student_qty']
    )

    lock_data = dict(lock)
    event_data = {
        'id': lock['event_id'],
        'title': lock['event_title'],
        'venue': lock['event_venue'],
        'event_date': lock['event_date'],
        'event_time': lock['event_time'],
        'image_url': lock['image_url'],
    }

    return render_template(
        'booking/checkout.html',
        lock=lock_data,
        event=event_data,
        total_price=total_price,
    )

@booking_bp.route('/checkout/<int:lock_id>/pay', methods=['POST'])
@login_required
def pay(lock_id: int):
    user_id = session['user_id']
    payment_method = request.form.get('payment_method', 'card')

    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Delete the lock first using SELECT FOR UPDATE to prevent double-payment
            cur.execute(
                """
                SELECT tl.*, e.vip_price, e.normal_price, e.student_price,
                       EXTRACT(EPOCH FROM (tl.expires_at - NOW())) AS remaining_seconds
                  FROM ticket_locks tl
                  JOIN events e ON e.id = tl.event_id
                 WHERE tl.id = %s
                   FOR UPDATE OF tl
                """,
                (lock_id,),
            )
            lock = cur.fetchone()

            if lock is None or lock['user_id'] != user_id:
                flash('Lock not found or access denied.', 'error')
                return redirect(url_for('events.list_events'))

            if lock['remaining_seconds'] < 0:
                flash('Your reservation has expired. Please try again.', 'error')
                return redirect(url_for('events.list_events'))

            total_price = (
                float(lock['vip_price']) * lock['vip_qty'] +
                float(lock['normal_price']) * lock['normal_qty'] +
                float(lock['student_price']) * lock['student_qty']
            )

            cur.execute(
                """
                INSERT INTO bookings (user_id, event_id, vip_qty, normal_qty, student_qty, total_price, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'confirmed')
                RETURNING id
                """,
                (user_id, lock['event_id'], lock['vip_qty'], lock['normal_qty'], lock['student_qty'], total_price),
            )
            booking = cur.fetchone()

            cur.execute(
                """
                INSERT INTO payments (booking_id, amount, payment_method, status)
                VALUES (%s, %s, %s, 'completed')
                """,
                (booking['id'], total_price, payment_method),
            )

            seat_idx = 1
            for t_type, qty in [('VIP', lock['vip_qty']), ('Normal', lock['normal_qty']), ('Student', lock['student_qty'])]:
                for _ in range(qty):
                    cur.execute(
                        """
                        INSERT INTO tickets (booking_id, ticket_code, seat_label, ticket_type)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (booking['id'], generate_ticket_code(), generate_seat_label(seat_idx), t_type),
                    )
                    seat_idx += 1

            cur.execute("DELETE FROM ticket_locks WHERE id = %s", (lock_id,))
        conn.commit()

    flash('Booking confirmed! Your tickets are ready.', 'success')
    return redirect(url_for('booking.booking_history'))

@booking_bp.route('/checkout/<int:lock_id>/cancel', methods=['POST'])
@login_required
def cancel(lock_id: int):
    user_id = session['user_id']
    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM ticket_locks WHERE id = %s", (lock_id,))
            lock = cur.fetchone()

            if lock is None or lock['user_id'] != user_id:
                flash('Lock not found or access denied.', 'error')
                return redirect(url_for('events.list_events'))

            cur.execute(
                """
                UPDATE events
                   SET vip_available = vip_available + %s,
                       normal_available = normal_available + %s,
                       student_available = student_available + %s
                 WHERE id = %s
                """,
                (lock['vip_qty'], lock['normal_qty'], lock['student_qty'], lock['event_id']),
            )
            cur.execute("DELETE FROM ticket_locks WHERE id = %s", (lock_id,))
        conn.commit()

    flash('Booking cancelled.', 'info')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
    if is_ajax:
        return jsonify({'status': 'cancelled'})
    return redirect(url_for('events.list_events'))

@booking_bp.route('/my-bookings')
@login_required
def booking_history():
    user_id = session['user_id']
    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT b.id, b.vip_qty, b.normal_qty, b.student_qty, b.total_price, b.status, b.created_at,
                       e.title  AS event_title,
                       e.event_date,
                       e.event_time,
                       e.venue  AS event_venue
                  FROM bookings b
                  JOIN events e ON e.id = b.event_id
                 WHERE b.user_id = %s
                 ORDER BY b.created_at DESC
                """,
                (user_id,),
            )
            bookings = cur.fetchall()

            for booking in bookings:
                cur.execute(
                    """
                    SELECT id, ticket_code, seat_label, ticket_type
                      FROM tickets
                     WHERE booking_id = %s
                    """,
                    (booking['id'],),
                )
                booking['tickets'] = cur.fetchall()

    return render_template('booking/history.html', bookings=bookings)

@booking_bp.route('/tickets/<ticket_code>')
@login_required
def view_ticket(ticket_code: str):
    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT t.ticket_code, t.seat_label, t.ticket_type,
                       e.title  AS event_title,
                       e.event_date,
                       e.event_time,
                       e.venue  AS event_venue,
                       u.username AS holder_name,
                       b.id    AS booking_id
                  FROM tickets t
                  JOIN bookings b ON b.id = t.booking_id
                  JOIN events   e ON e.id = b.event_id
                  JOIN users    u ON u.id = b.user_id
                 WHERE t.ticket_code = %s
                """,
                (ticket_code,),
            )
            ticket = cur.fetchone()

    if ticket is None:
        flash('Ticket not found.', 'error')
        return redirect(url_for('booking.booking_history'))

    return render_template('booking/ticket.html', ticket=ticket)
