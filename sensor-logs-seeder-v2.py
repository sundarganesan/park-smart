import psycopg2
import random
import uuid
from datetime import datetime, timedelta
import os

# -----------------------
# Credential Handling
# -----------------------
def read_credentials(filepath):
    user = password = None
    try:
        with open(filepath, "r") as file:
            for line in file:
                if line.lower().startswith("user:"):
                    user = line.split(":", 1)[1].strip()
                elif line.lower().startswith("password:"):
                    password = line.split(":", 1)[1].strip()
        if not user or not password:
            raise ValueError("Missing user or password in credentials file.")
        print("✅ Credentials loaded from file.")
        return user, password
    except Exception as e:
        print(f"⚠️  Failed to read credentials from file: {e}")
        print("📝 Please enter credentials manually.")
        user = input("👤 CockroachDB username: ")
        password = input("🔑 CockroachDB password: ")
        return user, password

# -----------------------
# User Date Input
# -----------------------
def get_date_input(prompt):
    while True:
        try:
            return datetime.strptime(input(prompt + " (YYYY-MM-DD): "), "%Y-%m-%d").date()
        except ValueError:
            print("❌ Invalid format. Use YYYY-MM-DD.")

# -----------------------
# Main Logic
# -----------------------

# Get date range
start_date = get_date_input("📅 Enter start date")
end_date = get_date_input("📅 Enter end date")

if start_date > end_date:
    print("❌ Start date must be before or equal to end date.")
    exit(1)

# Weekday occupancy mapping (based on typical US workweek)
occupancy_by_day = {
    0: 0.85,  # Monday
    1: 0.95,  # Tuesday
    2: 0.98,  # Wednesday
    3: 0.90,  # Thursday
    4: 0.60,  # Friday
}

# Read credentials from local secrets file
creds_file = os.path.join(os.path.dirname(__file__), "secrets", "pwd.txt")
user, password = read_credentials(creds_file)

# Connect to CockroachDB
print("\n🔌 Connecting to CockroachDB...")
try:
    conn = psycopg2.connect(
        dbname="defaultdb",
        user=user,
        password=password,
        host="social-elves-11376.j77.aws-us-west-2.cockroachlabs.cloud",
        port=26257,
        sslmode="require"
    )
    conn.autocommit = True
    cur = conn.cursor()
    print("✅ Connected to CockroachDB.\n")
except Exception as e:
    print(f"❌ Failed to connect to CockroachDB: {e}")
    exit(1)

# Fetch sensors
print("📦 Fetching sensors...")
cur.execute("SELECT sensor_id FROM parksmart.sensors")
sensor_ids = [row[0] for row in cur.fetchall()]
print(f"✅ {len(sensor_ids)} sensors found.\n")

# Workdays in range
print("📆 Filtering workdays...")
all_days = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
work_days = [d for d in all_days if d.weekday() < 5]
print(f"✅ {len(work_days)} workdays detected.\n")

# Generate logs
print("🧠 Generating sensor logs...")
events = []

for day in work_days:
    weekday = day.weekday()
    occupancy_rate = occupancy_by_day.get(weekday, 0.0)
    occupied_sensors = random.sample(sensor_ids, int(len(sensor_ids) * occupancy_rate))

    for sensor_id in occupied_sensors:
        # Morning entry: 8:30–10:30
        entry_time = datetime.combine(day, datetime.min.time()) + timedelta(hours=8, minutes=30) + timedelta(minutes=random.randint(0, 120))
        events.append((str(uuid.uuid4()), sensor_id, "entry", entry_time))

        # Optional lunch exit/entry
        if random.random() < 0.3:
            exit_lunch = datetime.combine(day, datetime.min.time()) + timedelta(hours=12) + timedelta(minutes=random.randint(0, 30))
            reentry_lunch = exit_lunch + timedelta(minutes=random.randint(30, 60))
            events.append((str(uuid.uuid4()), sensor_id, "exit", exit_lunch))
            events.append((str(uuid.uuid4()), sensor_id, "entry", reentry_lunch))

        # Evening exit: 4:30–5:30
        exit_time = datetime.combine(day, datetime.min.time()) + timedelta(hours=16, minutes=30) + timedelta(minutes=random.randint(0, 60))
        events.append((str(uuid.uuid4()), sensor_id, "exit", exit_time))

    print(f"   ➤ {day.strftime('%A %Y-%m-%d')} | Occupancy: {int(occupancy_rate * 100)}% | Events: {len(occupied_sensors) * 2}–{len(occupied_sensors) * 3}")

print(f"\n📊 Total sensor events to insert: {len(events)}\n")

# Insert logs in batches
print("💾 Inserting sensor logs...")
batch_size = 1000
for i in range(0, len(events), batch_size):
    batch = events[i:i + batch_size]
    args_str = b",".join(cur.mogrify("(%s, %s, %s, %s)", event) for event in batch)
    cur.execute(
        b"INSERT INTO parksmart.sensorlogs (id, sensor_id, event_type, event_timestamp) VALUES " + args_str
    )
    print(f"   ➤ Inserted batch {i // batch_size + 1} ({len(batch)} records)")

# Cleanup
cur.close()
conn.close()
print("\n✅ All sensor logs inserted.")
print("🔒 Connection closed.")
