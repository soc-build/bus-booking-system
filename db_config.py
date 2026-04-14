import pymysql

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Default XAMPP password is empty
    'database': 'bus_booking_system',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_connection():
    """Get database connection"""
    return pymysql.connect(**DB_CONFIG)

def init_database():
    """Initialize database tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create buses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            bus_id INT PRIMARY KEY AUTO_INCREMENT,
            bus_no INT UNIQUE NOT NULL,
            bus_name VARCHAR(100) NOT NULL,
            route VARCHAR(200) NOT NULL,
            bus_type ENUM('BUSINESS', 'AC') NOT NULL,
            total_seats INT NOT NULL,
            available_seats INT NOT NULL,
            rent DECIMAL(10, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INT PRIMARY KEY AUTO_INCREMENT,
            bus_no INT NOT NULL,
            passenger_name VARCHAR(100) NOT NULL,
            passenger_phone VARCHAR(20),
            passenger_email VARCHAR(100),
            seats_booked INT NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('CONFIRMED', 'CANCELLED') DEFAULT 'CONFIRMED',
            FOREIGN KEY (bus_no) REFERENCES buses(bus_no)
        )
    """)
    
    # Create admins table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INT PRIMARY KEY AUTO_INCREMENT,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if buses table is empty
    cursor.execute("SELECT COUNT(*) as count FROM buses")
    count = cursor.fetchone()['count']
    
    if count == 0:
        # Insert sample data
        cursor.execute("""
            INSERT INTO buses (bus_no, bus_name, route, bus_type, total_seats, available_seats, rent) VALUES
            (1001, 'AFM Express', 'Dhaka - Rangpur', 'BUSINESS', 40, 40, 800),
            (1002, 'Lemon Line', 'Dhaka - Cox-Bazzer', 'BUSINESS', 35, 35, 1000),
            (1003, 'S.N.Express', 'Dhaka - Satkhira', 'BUSINESS', 45, 45, 650),
            (2001, 'Beach Voyager', 'Dhaka-Cox Bazar', 'AC', 42, 42, 2600),
            (2002, 'Mountain Express', 'Dhaka-Rangamati', 'AC', 42, 42, 1800),
            (2003, 'S.N.Express', 'Dhaka-Satkhira', 'AC', 42, 42, 1200)
        """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database initialized successfully!")