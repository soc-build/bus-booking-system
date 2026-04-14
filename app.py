from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pymysql
import os
from db_config import get_connection, init_database

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Initialize database on startup
init_database()

# Get the absolute path to frontend folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

# ==================== ROUTES ====================
@app.route('/')
def home():
    """Serve the index.html file"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from frontend folder"""
    return send_from_directory(FRONTEND_DIR, filename)

@app.route('/api/health')
def health():
    try:
        conn = get_connection()
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"})
    except:
        return jsonify({"status": "healthy", "database": "disconnected"})

@app.route('/api/buses', methods=['GET'])
def get_buses():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM buses ORDER BY bus_no")
    buses = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(buses)

@app.route('/api/buses', methods=['POST'])
def add_bus():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO buses (bus_no, bus_name, route, bus_type, total_seats, available_seats, rent)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (data['bus_no'], data['bus_name'], data['route'], data['bus_type'], 
          data['total_seats'], data['total_seats'], data['rent']))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Bus added"}), 201

@app.route('/api/buses/<int:bus_no>', methods=['DELETE'])
def delete_bus(bus_no):
    """Delete a bus (only if no active bookings)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check for active bookings
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM bookings 
            WHERE bus_no = %s AND status = 'CONFIRMED'
        """, (bus_no,))
        
        result = cursor.fetchone()
        if result['count'] > 0:
            return jsonify({"error": "Cannot delete bus with active bookings"}), 400
        
        # Delete the bus
        cursor.execute("DELETE FROM buses WHERE bus_no = %s", (bus_no,))
        
        if cursor.rowcount == 0:
            return jsonify({"error": "Bus not found"}), 404
        
        conn.commit()
        return jsonify({"message": f"Bus #{bus_no} deleted successfully"}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, bs.bus_name, bs.route 
        FROM bookings b 
        JOIN buses bs ON b.bus_no = bs.bus_no 
        ORDER BY b.booking_date DESC
    """)
    bookings = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(bookings)

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check maximum 4 tickets per booking
    if data['seats_booked'] > 4:
        return jsonify({"error": "Maximum 4 tickets per booking allowed!"}), 400
    if data['seats_booked'] < 1:
        return jsonify({"error": "Must book at least 1 seat!"}), 400
    
    cursor.execute("SELECT * FROM buses WHERE bus_no = %s", (data['bus_no'],))
    bus = cursor.fetchone()
    
    if not bus:
        return jsonify({"error": "Bus not found"}), 404
    
    if bus['available_seats'] < data['seats_booked']:
        return jsonify({"error": f"Only {bus['available_seats']} seats available!"}), 400
    
    total = data['seats_booked'] * bus['rent']
    
    cursor.execute("""
        INSERT INTO bookings (bus_no, passenger_name, passenger_phone, seats_booked, total_amount)
        VALUES (%s, %s, %s, %s, %s)
    """, (data['bus_no'], data['passenger_name'], data['passenger_phone'], 
          data['seats_booked'], total))
    
    booking_id = cursor.lastrowid
    
    cursor.execute("UPDATE buses SET available_seats = available_seats - %s WHERE bus_no = %s",
                   (data['seats_booked'], data['bus_no']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({
        "booking_id": booking_id, 
        "message": f"Booking confirmed! {data['seats_booked']} seat(s) booked successfully."
    }), 201

@app.route('/api/bookings/search')
def search_bookings():
    query = request.args.get('q', '')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, bs.bus_name, bs.route 
        FROM bookings b 
        JOIN buses bs ON b.bus_no = bs.bus_no 
        WHERE b.booking_id LIKE %s OR b.passenger_phone LIKE %s
        ORDER BY b.booking_date DESC
    """, (f'%{query}%', f'%{query}%'))
    bookings = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(bookings)

@app.route('/api/bookings/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM bookings WHERE booking_id = %s AND status = 'CONFIRMED'", (booking_id,))
    booking = cursor.fetchone()
    
    if booking:
        cursor.execute("UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = %s", (booking_id,))
        cursor.execute("UPDATE buses SET available_seats = available_seats + %s WHERE bus_no = %s",
                       (booking['seats_booked'], booking['bus_no']))
        conn.commit()
    
    cursor.close()
    conn.close()
    return jsonify({"message": "Cancelled"})

@app.route('/api/admin/setup', methods=['POST'])
def admin_setup():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM admins")
    if cursor.fetchone()['count'] > 0:
        return jsonify({"error": "Admin already exists"}), 400
    
    cursor.execute("INSERT INTO admins (password) VALUES (%s)", (data['password'],))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Setup complete"})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE password = %s", (data['password'],))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if admin:
        return jsonify({"message": "Login successful"})
    return jsonify({"error": "Invalid password"}), 401

@app.route('/api/admin/reset-bus/<int:bus_no>', methods=['POST'])
def reset_single_bus(bus_no):
    """Reset available seats for a specific bus"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT bus_name, total_seats, available_seats FROM buses WHERE bus_no = %s", (bus_no,))
        bus = cursor.fetchone()
        
        if not bus:
            return jsonify({"error": "Bus not found"}), 404
        
        cursor.execute("""
            UPDATE buses 
            SET available_seats = total_seats 
            WHERE bus_no = %s
        """, (bus_no,))
        
        conn.commit()
        
        return jsonify({
            "message": f"✅ Bus #{bus_no} ({bus['bus_name']}) reset to {bus['total_seats']} seats!",
            "bus_no": bus_no,
            "bus_name": bus['bus_name'],
            "total_seats": bus['total_seats']
        }), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚌 Bus Booking System - MySQL Connected")
    print("="*50)
    print(f"📍 Frontend Directory: {FRONTEND_DIR}")
    print("📍 http://localhost:5000")
    print("📊 Database: bus_booking_system")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)