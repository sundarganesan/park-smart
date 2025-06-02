import psycopg2
import uuid
import random
import time
from datetime import datetime, timedelta

# Vehicle types
VEHICLE_TYPES = ['regular', 'ev', 'ada']
EVENT_TYPES = ['entry', 'exit']

# Read DB credentials
def read_db_credentials(path):
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
            user = lines[0].split(':')[1].strip()
            password = lines[1].split(':')[1].strip()
        return user, password
    except FileNotFoundError:
        print("Password file not found. Please enter manually.")
        user = input("Enter DB user: ")
        password = input("Enter DB password: ")
        return user, password

# Connect to DB
def get_connection():
    user, password = read_db_credentials("secrets/pwd.txt")
    return psycopg2.connect(
        dbname="defaultdb",
        user=user,
        password=password,
        host="social-elves-11376.j77.aws-us-west-2.cockroachlabs.cloud",
        port=26257,
        sslmode="require"
    )

# Load lots and sensors
def load_lots_and_sensors(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT lot_id, total_regular_spots, total_ev_spots, total_ada_spots FROM parksmart.lots;")
        lots = cur.fetchall()

        cur.execute("SELECT sensor_id, lot_id FROM parksmart.sensors;")
        sensors = cur.fetchall()

    sensors_by_lot = {}
    for sensor_id, lot_id in sensors:
        sensors_by_lot.setdefault(lot_id, []).append(sensor_id)

    lot_dict = {lot_id: {'total_regular_spots': reg, 'total_ev_spots': ev, 'total_ada_spots': ada}
                for lot_id, reg, ev, ada in lots}

    return lot_dict, sensors_by_lot

# Update lots availability
def update_lot_availability(conn, lot_id, vehicle_type, event_type):
    spot_column = f"available_{vehicle_type}_spots"
    with conn.cursor() as cur:
        if event_type == 'entry':
            cur.execute(f"""
                UPDATE parksmart.lots
                SET {spot_column} = GREATEST({spot_column} - 1, 0)
                WHERE lot_id = %s;
            """, (lot_id,))
        else:
            cur.execute(f"""
                UPDATE parksmart.lots
                SET {spot_column} = LEAST({spot_column} + 1, total_{vehicle_type}_spots)
                WHERE lot_id = %s;
            """, (lot_id,))

        # Update available_spots
        cur.execute("""
            UPDATE parksmart.lots
            SET available_spots = available_regular_spots + available_ev_spots + available_ada_spots
            WHERE lot_id = %s;
        """, (lot_id,))
    conn.commit()

# Insert sensor log event
def insert_sensor_log(conn, sensor_id, event_type, timestamp):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO parksmart.sensorlogs (id, sensor_id, event_type, event_timestamp)
            VALUES (%s, %s, %s, %s);
        """, (str(uuid.uuid4()), sensor_id, event_type, timestamp))
    conn.commit()

# Main simulation loop
def run_simulation(start_time, duration_minutes):
    conn = get_connection()
    lot_info, sensors_by_lot = load_lots_and_sensors(conn)
    print(f"✅ Loaded {len(lot_info)} lots for simulation.")

    end_time = start_time + timedelta(minutes=duration_minutes)
    current_time = start_time

    while current_time < end_time:
        for lot_id in lot_info.keys():
            if lot_id not in sensors_by_lot:
                continue

            vehicle_type = random.choice(VEHICLE_TYPES)
            event_type = random.choices(EVENT_TYPES, weights=[0.7, 0.3])[0]  # Entry more likely
            sensor_id = random.choice(sensors_by_lot[lot_id])

            print(f"[{current_time.strftime('%H:%M:%S')}] {event_type.upper()} - Lot: {lot_id}, Sensor: {sensor_id}, Vehicle: {vehicle_type}")

            insert_sensor_log(conn, sensor_id, event_type, current_time)
            update_lot_availability(conn, lot_id, vehicle_type, event_type)

        time.sleep(1)  # simulate real-time delay
        current_time += timedelta(seconds=30)

    print("🛑 Simulation completed.")
    conn.close()

# --- Entry Point ---
if __name__ == "__main__":
    start_input = input("Enter simulation start datetime (YYYY-MM-DD HH:MM:SS): ")
    duration_input = int(input("Enter duration in minutes: "))
    try:
        start_dt = datetime.strptime(start_input, "%Y-%m-%d %H:%M:%S")
        run_simulation(start_dt, duration_input)
    except ValueError:
        print("Invalid date format.")
