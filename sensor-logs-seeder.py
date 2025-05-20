import psycopg2
import random
import uuid
from datetime import datetime, timedelta

# DB connection
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

print("📦 Fetching sensor IDs...")
cur.execute("SELECT sensor_id FROM parksmart.sensors")
sensor_ids = [row[0] for row in cur.fetchall()]
print(f"✅ Retrieved {len(sensor_ids)} sensors.\n")

# Simulation time window
start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
# Adjust to most recent Monday
start_date -= timedelta(days=start_date.weekday())

work_days = [start_date + timedelta(days=i) for i in range(5)]  # Mon-Fri

print("🧠 Generating sensor log events...")
events = []

for day in work_days:
    daily_occupied = set()

    for sensor_id in random.sample(sensor_ids, int(0.98 * len(sensor_ids))):
        # Entry between 8:30 AM - 10:30 AM
        entry_time = day + timedelta(hours=8, minutes=30) + timedelta(
            minutes=random.randint(0, 120)
        )
        events.append((str(uuid.uuid4()), sensor_id, "entry", entry_time))
        daily_occupied.add(sensor_id)

        # Optional lunch exit/entry
        if random.random() < 0.3:
            exit_lunch = day + timedelta(hours=12) + timedelta(minutes=random.randint(0, 30))
            entry_lunch = exit_lunch + timedelta(minutes=random.randint(30, 60))
            events.append((str(uuid.uuid4()), sensor_id, "exit", exit_lunch))
            events.append((str(uuid.uuid4()), sensor_id, "entry", entry_lunch))

        # Exit between 4:30 PM - 5:30 PM
        exit_time = day + timedelta(hours=16, minutes=30) + timedelta(minutes=random.randint(0, 60))
        events.append((str(uuid.uuid4()), sensor_id, "exit", exit_time))

print(f"📊 Generated {len(events)} sensor events.\n")

# Insert in batches
print("💾 Inserting into database...")
batch_size = 1000
for i in range(0, len(events), batch_size):
    batch = events[i:i + batch_size]
    args_str = b",".join(
        cur.mogrify("(%s, %s, %s, %s)", event) for event in batch
    )
    cur.execute(
        b"INSERT INTO parksmart.sensorlogs (id, sensor_id, event_type, event_timestamp) VALUES " + args_str
    )
    print(f"   ➤ Inserted batch {i // batch_size + 1} ({len(batch)} records)")

print("✅ Sensor logs seeding complete.\n")

cur.close()
conn.close()
print("🔒 Connection closed.")
