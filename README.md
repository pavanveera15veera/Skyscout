# CS 6083 — PS3 Q1: Airline Flight & Booking Web App

Built with Flask + SQLite using the flights.sql data from PS2 Q2.

## Setup (30 seconds)

```bash
pip install flask
python app.py
# → http://127.0.0.1:5000
```

The database `airline.db` is already pre-loaded from flights.sql. No setup needed.

## What Each Part Does

| Part | URL | Description |
|------|-----|-------------|
| (a) | `GET /` | Search form: origin code, destination code, date range |
| (b) | `POST /flights` | All matching flights — shown regardless of booking status |
| (c) | `GET /seats/<flight>/<date>` | Capacity, booked, available, seat map |

## Demo Routes (all from flights.sql data)

| Route | Dates | Notes |
|-------|-------|-------|
| JFK → LAX | 2025-12-29 to 2025-12-31 | Shows AA101 (Dec29: 5/20) + AA101 (Dec31: 15/20) + AA205 (Dec31: 4/20) |
| ATL → MIA | 2025-12-31 | DL410 — 14/15 seats booked (almost full) |
| JFK → ATL | 2025-12-30 to 2025-12-31 | DL620 on both dates |
| SFO → ORD | 2025-12-31 | UA302 — **fully booked** (10/10) |
| LHR → JFK | 2025-12-31 | BA178 — 6/25 (lots of seats) |
| CDG → NRT | 2025-12-30 | AF023 — 19hr flight, arrives next day |
| SIN → LHR | 2025-12-30 | SQ321 |
| LAX → SFO | 2025-12-31 | UA789 |

## Key SQL Queries

### Part (b) — flights list
```sql
SELECT f.flight_number, f.departure_date, fs.airline_name,
       fs.origin_code, fs.dest_code, fs.departure_time, fs.duration, f.plane_type
FROM Flight f
JOIN FlightService fs ON f.flight_number = fs.flight_number
JOIN Airport a1 ON fs.origin_code = a1.airport_code
JOIN Airport a2 ON fs.dest_code   = a2.airport_code
WHERE fs.origin_code = ? AND fs.dest_code = ?
  AND f.departure_date BETWEEN ? AND ?
ORDER BY f.departure_date, fs.departure_time
```

### Part (c) — seat availability
```sql
SELECT ac.capacity,
       COUNT(b.seat_number)              AS booked_seats,
       ac.capacity - COUNT(b.seat_number) AS available_seats
FROM Flight f
JOIN Aircraft ac ON f.plane_type = ac.plane_type
LEFT JOIN Booking b ON b.flight_number = f.flight_number AND b.departure_date = f.departure_date
WHERE f.flight_number = ? AND f.departure_date = ?
GROUP BY f.flight_number, f.departure_date, ac.capacity
```

**LEFT JOIN** is used so that flights with zero bookings still return a row (count = 0).

## Schema Used (from flights.sql / PS2)

- `Airport` (airport_code PK, name, city, country)
- `Aircraft` (plane_type PK, capacity)
- `FlightService` (flight_number PK, airline_name, origin_code→Airport, dest_code→Airport, departure_time, duration)
- `Flight` (flight_number, departure_date → composite PK, plane_type→Aircraft)
- `Passenger` (pid PK, passenger_name)
- `Booking` (pid, flight_number, departure_date → composite PK, seat_number)

## Switch to PostgreSQL

In `app.py`, replace `get_db()`:
```python
import psycopg2, psycopg2.extras
def get_db():
    conn = psycopg2.connect(host="localhost", dbname="airline_db", user="...", password="...")
    conn.row_factory = psycopg2.extras.RealDictCursor
    return conn
```
And change `?` placeholders → `%s` in all SQL queries.
