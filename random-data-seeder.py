import psycopg2
import uuid
import random
from faker import Faker

fake = Faker()

# Database connection settings
print("🔌 Connecting to CockroachDB...")
conn = psycopg2.connect(
    dbname="defaultdb",
    user="sundarganesan",
    password="LXVoLafODmQ9yqfKKRTYKg",
    host="social-elves-11376.j77.aws-us-west-2.cockroachlabs.cloud",
    port=26257,
    sslmode="require"
)
conn.autocommit = True
cur = conn.cursor()
print("✅ Connected to database.\n")

# Step 1: Insert 1 office
print("🏢 Inserting office...")
office_uuid = str(uuid.uuid4())
office_id = random.randint(1000, 9999)

cur.execute("""
    INSERT INTO parksmart.offices (id, office_id, name, address)
    VALUES (%s, %s, %s, %s)
""", (office_uuid, office_id, "Main Office", fake.address()))
print(f"✅ Inserted office with office_id = {office_id}\n")

# Generate unique INT8 IDs
def get_unique_ids(start, count):
    return list(range(start, start + count))

lot_base_id = 1000
sensor_base_id = 5000
lot_ids = get_unique_ids(lot_base_id, 15)
sensor_id_counter = sensor_base_id

# Step 2: Insert lots and sensors
print("🚗 Inserting lots and sensors...")
for i, lot_id in enumerate(lot_ids):
    lot_uuid = str(uuid.uuid4())
    lot_name = chr(65 + i)  # 'A' to 'O'
    location = fake.street_address()
    total_spots = random.randint(200, 500)

    total_ev_spots = int(total_spots * 0.1)
    total_ada_spots = int(total_spots * 0.05)
    total_regular_spots = total_spots - total_ev_spots - total_ada_spots

    print(f"  ➤ Inserting Lot {lot_name} (lot_id={lot_id}) with {total_spots} total spots...")

    # Insert lot with office_id
    cur.execute("""
        INSERT INTO parksmart.lots (
            id, lot_id, office_id, name, location,
            nearest_lot_id_1, nearest_lot_id_2, nearest_lot_id_3,
            total_spots, total_regular_spots, total_ev_spots, total_ada_spots,
            available_spots, available_regular_spots, available_ev_spots, available_ada_spots
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        lot_uuid, lot_id, office_id, lot_name, location,
        None, None, None,
        total_spots, total_regular_spots, total_ev_spots, total_ada_spots,
        total_spots, total_regular_spots, total_ev_spots, total_ada_spots
    ))

    # Insert sensors
    print(f"     ⏳ Inserting {total_spots} sensors for Lot {lot_name}...")
    for _ in range(total_spots):
        sensor_uuid = str(uuid.uuid4())
        sensor_id = sensor_id_counter
        sensor_id_counter += 1

        sensor_type = random.choice(["infrared", "ultrasonic", "magnetic"])

        cur.execute("""
            INSERT INTO parksmart.sensors (id, sensor_id, lot_id, sensor_type)
            VALUES (%s, %s, %s, %s)
        """, (sensor_uuid, sensor_id, lot_id, sensor_type))

    print(f"     ✅ Sensors for Lot {lot_name} inserted.\n")

print("🎉 All lots and sensors inserted.\n")

# Cleanup
cur.close()
conn.close()
print("🔒 Connection closed. Seeding complete.")
