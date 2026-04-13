from flask import Flask, render_template, request
import sqlite3, os, re

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "airline.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def query(sql, params=()):
    conn = get_db()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows

def duration_to_minutes(dur_str):
    """Parse '3 hours 30 minutes' -> 210 minutes for arrival calculation."""
    if not dur_str:
        return 0
    hours   = re.search(r'(\d+)\s*hour',   dur_str)
    minutes = re.search(r'(\d+)\s*minute', dur_str)
    total = 0
    if hours:   total += int(hours.group(1))   * 60
    if minutes: total += int(minutes.group(1))
    return total

def add_minutes_to_time(time_str, minutes):
    """Add minutes to 'HH:MM:SS', return (date_offset, 'HH:MM:SS')."""
    h, m, s = map(int, time_str.split(':'))
    total_min = h * 60 + m + minutes
    days  = total_min // (24 * 60)
    total_min %= (24 * 60)
    return days, f"{total_min // 60:02d}:{total_min % 60:02d}:00"

def add_days_to_date(date_str, days):
    from datetime import date, timedelta
    d = date.fromisoformat(date_str)
    return str(d + timedelta(days=days))

# ── Part (a) Search Form ───────────────────────────────────────────────────────
@app.route("/")
def index():
    airports = query(
        "SELECT airport_code, name, city, country FROM Airport ORDER BY city, airport_code"
    )
    return render_template("index.html", airports=airports)

# ── Part (b) Flight Results ────────────────────────────────────────────────────
@app.route("/flights", methods=["POST"])
def flights():
    origin      = request.form.get("origin", "").strip().upper()
    destination = request.form.get("destination", "").strip().upper()
    date_from   = request.form.get("date_from", "")
    date_to     = request.form.get("date_to", "")

    results = query("""
        SELECT
            f.flight_number,
            f.departure_date,
            fs.airline_name,
            fs.origin_code,
            fs.dest_code,
            a1.city   AS origin_city,
            a1.country AS origin_country,
            a2.city   AS dest_city,
            a2.country AS dest_country,
            fs.departure_time,
            fs.duration,
            f.plane_type
        FROM Flight f
        JOIN FlightService fs ON f.flight_number = fs.flight_number
        JOIN Airport a1       ON fs.origin_code  = a1.airport_code
        JOIN Airport a2       ON fs.dest_code    = a2.airport_code
        WHERE fs.origin_code = ?
          AND fs.dest_code   = ?
          AND f.departure_date BETWEEN ? AND ?
        ORDER BY f.departure_date, fs.departure_time
    """, (origin, destination, date_from, date_to))

    orig_info = query("SELECT name, city, country FROM Airport WHERE airport_code=?", (origin,))
    dest_info = query("SELECT name, city, country FROM Airport WHERE airport_code=?", (destination,))

    return render_template("flights.html",
        flights=results,
        origin=origin, destination=destination,
        date_from=date_from, date_to=date_to,
        origin_info=orig_info[0] if orig_info else {},
        dest_info=dest_info[0]   if dest_info else {},
    )

# ── Part (c) Seat Availability ─────────────────────────────────────────────────
@app.route("/seats/<flight_number>/<departure_date>")
def seats(flight_number, departure_date):
    rows = query("""
        SELECT
            f.flight_number,
            f.departure_date,
            fs.airline_name,
            fs.origin_code,
            fs.dest_code,
            a1.name  AS origin_name,
            a1.city  AS origin_city,
            a2.name  AS dest_name,
            a2.city  AS dest_city,
            fs.departure_time,
            fs.duration,
            f.plane_type,
            ac.capacity,
            COUNT(b.seat_number)                     AS booked_seats,
            ac.capacity - COUNT(b.seat_number)        AS available_seats
        FROM Flight f
        JOIN FlightService fs ON f.flight_number = fs.flight_number
        JOIN Aircraft ac      ON f.plane_type    = ac.plane_type
        JOIN Airport a1       ON fs.origin_code  = a1.airport_code
        JOIN Airport a2       ON fs.dest_code    = a2.airport_code
        LEFT JOIN Booking b
            ON  b.flight_number  = f.flight_number
            AND b.departure_date = f.departure_date
        WHERE f.flight_number  = ?
          AND f.departure_date = ?
        GROUP BY f.flight_number, f.departure_date, ac.capacity
    """, (flight_number, departure_date))
    info = rows[0] if rows else None

    booked_seats = [r["seat_number"] for r in query(
        "SELECT seat_number FROM Booking WHERE flight_number=? AND departure_date=? ORDER BY seat_number",
        (flight_number, departure_date)
    )]

    # Compute arrival date/time
    arrival_info = {}
    if info:
        dur_min = duration_to_minutes(info["duration"])
        day_offset, arr_time = add_minutes_to_time(info["departure_time"], dur_min)
        arrival_info["time"] = arr_time
        arrival_info["date"] = add_days_to_date(departure_date, day_offset)
        arrival_info["next_day"] = day_offset > 0

    return render_template("seat_info.html",
        info=info,
        flight_number=flight_number,
        departure_date=departure_date,
        booked_seats=booked_seats,
        arrival=arrival_info,
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)
