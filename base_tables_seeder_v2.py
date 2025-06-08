import random
import uuid
import csv
import argparse

from faker import Faker
from datetime import datetime
import psycopg2
import time
from tqdm import tqdm
import os
from collections import Counter

fake = Faker()


def read_db_credentials(path, headless=False):
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
            user = lines[0].split(':')[1].strip()
            password = lines[1].split(':')[1].strip()
            return user, password
    except FileNotFoundError:
        if headless:
            raise RuntimeError("[ERROR] Missing secrets/pwd.txt in headless mode")
        print("Password file not found. Please enter manually.")
        user = input("Enter DB user: ")
        password = input("Enter DB password: ")
        return user, password


def get_connection(headless=False):
    user, password = read_db_credentials("secrets/pwd.txt", headless=headless)
    return psycopg2.connect(
        dbname="social_elves",
        user=user,
        password=password,
        host="social-elves-11376.j77.aws-us-west-2.cockroachlabs.cloud",
        port=26257,
        sslmode="require"
    )


def write_csv(filename, rows, headers):
    full_path = os.path.join(seed_dir, filename)
    with open(full_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


parser = argparse.ArgumentParser()
parser.add_argument("--headless", action="store_true", help="Run script without interactive prompts")
args = parser.parse_args()

start_time = time.time()
print("[START] Script started at", datetime.now())
now = datetime.utcnow()

# Create seed_files folder if it doesn't exist
seed_dir = "seed_files"
os.makedirs(seed_dir, exist_ok=True)

# Ask user which tables to seed
if args.headless:
    seed_choice = "1"
    print("[INFO] Running in headless mode: Seeding base tables")
else:
    print("What do you want to seed?")
    print("1. Base tables")
    print("2. Log tables")
    seed_choice = input("Enter 1 or 2: ").strip()

if seed_choice == "2":
    print("[INFO] Seeding log tables...")

    if args.headless:
        log_csv_choice = "1"
        log_start_date = "2024-06-01"
        log_end_date = "2024-06-07"
        print(f"[INFO] Headless mode: Generating log data from {log_start_date} to {log_end_date}")
    else:
        # Ask for date range
        log_start_date = input("Enter START date (YYYY-MM-DD): ").strip()
        log_end_date = input("Enter END date (YYYY-MM-DD): ").strip()

        # Ask CSV or insert
        print("Do you want to:")
        print("1. Generate CSV files")
        print("2. Insert directly into CockroachDB (will also generate CSV files)")
        log_csv_choice = input("Enter 1 or 2: ").strip()

    print(f"[INFO] Would generate log data from {log_start_date} to {log_end_date} as per occupancy pattern.")
    if log_csv_choice == "1":
        print("[INFO] Writing CSV only...")
    else:
        print("[INFO] Writing CSV and inserting into DB...")


    # Load spot_rows, employee_rows, lot_id_map from CSV
    def load_csv(filepath):
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            return [row for row in reader]


    print("[INFO] Loading base table seed files...")
    spot_rows = load_csv(os.path.join("seed_files", "spot_seed.csv"))
    employee_rows = load_csv(os.path.join("seed_files", "employee_seed.csv"))
    lot_rows = load_csv(os.path.join("seed_files", "lot_seed.csv"))

    # Rebuild lot_id_map
    lot_id_map = {row[1]: row[0] for row in lot_rows}  # name -> UUID

    print(f"[INFO] Loaded {len(spot_rows)} spot rows")
    print(f"[INFO] Loaded {len(employee_rows)} employee rows")
    print(f"[INFO] Loaded {len(lot_rows)} lot rows (reconstructed lot_id_map)")

    from datetime import timedelta, date


    def daterange(start_date, end_date):
        for n in range(int((end_date - start_date).days) + 1):
            yield start_date + timedelta(n)


    # Parse user input dates
    start_dt = datetime.strptime(log_start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(log_end_date, "%Y-%m-%d").date()

    # Placeholder lists for generated logs
    sensor_log_rows = []
    employee_history_rows = []

    # Iterate days
    print("[INFO] Generating log data...")
    for single_date in tqdm(list(daterange(start_dt, end_dt)), desc="Processing dates"):
        if single_date.weekday() >= 5:
            continue  # Skip weekends

        # Generate employee parking history and sensor logs per present employee per day
        # In-office pattern by weekday
        weekday_in_office_pct = {
            0: 0.50,  # Monday
            1: 0.70,  # Tuesday
            2: 0.75,  # Wednesday
            3: 0.65,  # Thursday
            4: 0.30   # Friday
        }

        for employee_row in employee_rows:
            if random.random() < weekday_in_office_pct[single_date.weekday()]:
                employee_id = employee_row[1]
                lot_id = random.choice(list(lot_id_map.values()))
                spot_candidates = [r for r in spot_rows if r[2] == lot_id]
                chosen_spot = random.choice(spot_candidates)
                sensor_id = chosen_spot[3]

                # generate entry and exit timestamps
                ts_entry = datetime(single_date.year, single_date.month, single_date.day,
                                   random.randint(9, 11), random.randint(0, 59), random.randint(0, 59))
                ts_exit = datetime(single_date.year, single_date.month, single_date.day,
                                  random.randint(15, 17), random.randint(0, 59), random.randint(0, 59))
                if ts_exit <= ts_entry:
                    ts_exit = ts_entry + timedelta(hours=4)

                # append ENTRY and sensor OCCUPIED
                employee_history_rows.append([
                    str(uuid.uuid4()), employee_id, ts_entry, "ENTRY", lot_id,
                    now, "system", now, "system"
                ])
                sensor_log_rows.append([
                    str(uuid.uuid4()), ts_entry, "OCCUPIED", sensor_id,
                    "", now, "system", now, "system"
                ])

                # append EXIT and sensor VACANT
                employee_history_rows.append([
                    str(uuid.uuid4()), employee_id, ts_exit, "EXIT", lot_id,
                    now, "system", now, "system"
                ])
                sensor_log_rows.append([
                    str(uuid.uuid4()), ts_exit, "VACANT", sensor_id,
                    "", now, "system", now, "system"
                ])

print(f"[INFO] Generated {len(sensor_log_rows)} sensor_log rows")
print(f"[INFO] Generated {len(employee_history_rows)} employee_parking_history rows")

sensor_log_headers = [
    "id", "event_timestamp", "event_type", "sensor_id", "parking_tag",
    "created_at", "created_by", "updated_at", "updated_by"
]

employee_history_headers = [
    "id", "employee_id", "event_timestamp", "event_type", "lot_id",
    "created_at", "created_by", "updated_at", "updated_by"
]

write_csv("sensor_log_seed.csv", sensor_log_rows, sensor_log_headers)
write_csv("employee_parking_history_seed.csv", employee_history_rows, employee_history_headers)

if log_csv_choice == "2":
    print("[INFO] Inserting log tables into CockroachDB...")
    conn = get_connection(headless=args.headless)


    def insert_to_db(table, rows):
        with conn.cursor() as cur:
            for row in tqdm(rows, desc=f"Inserting {table}"):
                q = f"INSERT INTO park_smart.{table} VALUES ({','.join(['%s'] * len(row))})"
                cur.execute(q, row)
            conn.commit()


    insert_to_db("sensor_log", sensor_log_rows)
    insert_to_db("employee_parking_history", employee_history_rows)

    conn.close()
    print("[INFO] Log table insert complete ✅")

# For now — no actual log generation yet
print("[INFO] Log tables seeding logic to be implemented. Exiting.")
exit(0)

if args.headless:
    choice = "2"
    print("[INFO] Running in headless mode: Generating CSV + Inserting into DB")
else:
    print("Do you want to:")
    print("1. Generate CSV files")
    print("2. Insert directly into CockroachDB (will also generate CSV files)")
    choice = input("Enter 1 or 2: ").strip()

print("[INFO] Initializing constants and structures...")
OFFICE_ID = str(uuid.uuid4())
OFFICE_DATA = {
    "office_id": "1",
    "name": "Polaris McCoy Center",
    "address": "1111 Polaris Parkway, Columbus, OH 43240",
    "status": "OPEN",
    "status_description": "Open and Operational"
}

print("[INFO] Creating office rows...")
office_rows = [[
    OFFICE_ID, OFFICE_DATA["office_id"], OFFICE_DATA["name"], OFFICE_DATA["address"],
    OFFICE_DATA["status"], OFFICE_DATA["status_description"],
    now, now, 'system', 'system'
]]

BLOCKS = [
    ("A", "M", "N"), ("B", "B", "Q"), ("C", "M", "N"), ("D", "B", "C"),
    ("E", "L", "M"), ("F", "C", "B"), ("G", "L", "M"), ("H", "D", "C"),
    ("J", "K", "L"), ("K", "D", "C"), ("L", "K", "L"), ("M", "E", "D"),
    ("N", "J", "K"), ("P", "E", "F")
]

LOTS = [
    ("A", "NE"), ("B", "NE"), ("C", "E"), ("D", "E"),
    ("E", "SE"), ("F", "S"), ("G", "S"), ("H", "S"),
    ("J", "SW"), ("K", "W"), ("L", "W"), ("M", "NW"),
    ("N", "NW"), ("Q", "N"), ("X", "SW")
]

EMPLOYEE_COUNT = 12500
SPOT_COUNT = 11000
ADA_PCT = 0.03
EV_PCT = 0.02
REGULAR_PCT = 0.95

block_id_map = {}
lot_id_map = {}

print("[INFO] Creating lot rows with balanced random total spots...")
# Generate random weights for each lot
lot_weights = [random.uniform(0.5, 1.5) for _ in LOTS]
weight_sum = sum(lot_weights)

# Pre-calculate lot -> spot counts
lot_spot_counts = {}
for i, (lot_info, weight) in enumerate(zip(LOTS, lot_weights)):
    raw_count = SPOT_COUNT * (weight / weight_sum)
    count = int(round(raw_count))
    lot_spot_counts[lot_info[0]] = count

# Adjust rounding errors
total_assigned = sum(lot_spot_counts.values())
diff = SPOT_COUNT - total_assigned
if diff != 0:
    largest_lot = max(lot_spot_counts, key=lot_spot_counts.get)
    lot_spot_counts[largest_lot] += diff

# Now generate lot_rows
lot_rows = []
for name, location in LOTS:
    lot_id = str(uuid.uuid4())
    lot_id_map[name] = lot_id
    total = lot_spot_counts[name]

    lot_rows.append([
        lot_id, name, OFFICE_ID, f"Lot {name}", location, "ACTIVE", f"Lot {name} in use",
        total,
        int(total * REGULAR_PCT), int(total * ADA_PCT), int(total * EV_PCT),
        int(total * REGULAR_PCT), int(total * REGULAR_PCT), int(total * ADA_PCT), int(total * EV_PCT),
        now, now, 'system', 'system'
    ])

# Print per-lot stats
print("[INFO] Creating block rows...")
block_rows = []
for block_name, lot1, lot2 in BLOCKS:
    block_id = str(uuid.uuid4())
    block_id_map[block_name] = block_id
    preferred_lots = f"{lot_id_map[lot1]},{lot_id_map[lot2]}"
    block_rows.append([
        block_id, block_name, OFFICE_ID, 'ACTIVE', f"Block {block_name} is active",
        random.randint(500, 1200), preferred_lots,
        now, now, 'system', 'system'
    ])

# Print per-lot stats
print("[STATS] Per-lot spot counts:")
for name in sorted(lot_spot_counts.keys()):
    pct = lot_spot_counts[name] / SPOT_COUNT * 100
    print(f"  Lot {name}: {lot_spot_counts[name]} spots ({pct:.2f}%)")
print(f"  Total assigned: {sum(lot_spot_counts.values())} spots (target: {SPOT_COUNT})")

print("[INFO] Creating spot and sensor rows...")
spot_rows = []
sensor_rows = []
spot_counter = 0
for lot_name, lot_id in lot_id_map.items():
    lot_total = next((int(row[7]) for row in lot_rows if row[0] == lot_id), 0)
    print(f"[INFO] Generating {lot_total} spots for lot {lot_name}")
    type_counter = {'REGULAR': 0, 'ADA': 0, 'EV': 0}
    for i in tqdm(range(lot_total), desc=f"Processing lot {lot_name}"):
        spot_id = str(uuid.uuid4())
        sensor_id = str(uuid.uuid4())
        row_num = i // 10
        pos = i % 10
        spot_type = random.choices(['REGULAR', 'ADA', 'EV'], weights=[95, 3, 2])[0]
        type_counter[spot_type] += 1
        spot_rows.append([
            spot_id, f"{lot_name}-{i + 1}", lot_id, sensor_id, "AVAILABLE", "", spot_type, row_num, pos,
            now, now, 'system', 'system'
        ])
        sensor_rows.append([
            sensor_id, f"SENSOR-{sensor_id[:8]}", spot_id, "ACTIVE", "", "ULTRASONIC",
            now, now, 'system', 'system'
        ])
        spot_counter += 1
        if spot_counter >= SPOT_COUNT:
            break
    print(f"[SUMMARY] Lot {lot_name}:")
    for t in ['REGULAR', 'ADA', 'EV']:
        print(f"  {t}: {type_counter[t]} spots")
    print()
    if spot_counter >= SPOT_COUNT:
        break

print("[INFO] Creating employee rows...")
employee_rows = []

num_admins = 50
num_employees = int(EMPLOYEE_COUNT * 0.85)
num_contractors = EMPLOYEE_COUNT - num_admins - num_employees

# Build type pool
type_pool = (['ADMIN'] * num_admins) + (['EMPLOYEE'] * num_employees) + (['CONTRACTOR'] * num_contractors)
random.shuffle(type_pool)

for i in tqdm(range(EMPLOYEE_COUNT), desc="Generating employees"):
    emp_id = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + ''.join(random.choices('0123456789', k=6))
    emp_name = fake.name()
    block_id = random.choice(list(block_id_map.values()))
    lot_ids = random.sample(list(lot_id_map.values()), k=random.randint(0, 3))
    emp_type = type_pool[i]
    employee_rows.append([
        str(uuid.uuid4()), emp_id, emp_name, OFFICE_ID, block_id, "ACTIVE",
        fake.date_between(start_date='-5y', end_date='-1y'),
        datetime(9999, 12, 31).date(),
        emp_type, random.choice(list(lot_id_map.values())),
        ','.join(lot_ids), f"TAG-{emp_id}",
        'admin' if emp_type == 'ADMIN' else 'pass123', now, now, 'system', 'system'
    ])

print("\n[STATS] Employee type counts:")
emp_type_counter = Counter([row[8] for row in employee_rows])
for t in ['EMPLOYEE', 'CONTRACTOR', 'ADMIN']:
    print(f"  {t}: {emp_type_counter[t]}")
print(f"  Total employees: {len(employee_rows)} (target: {EMPLOYEE_COUNT})\n")

print("[INFO] Writing CSV files...")

# The actual header lists would be filled in here
write_csv("office_seed.csv", office_rows, [
    "id","office_id","name","address","status","status_description","created_at","created_by","updated_at","updated_by"
])
write_csv("block_seed.csv", block_rows, [
    "id","block_id","name","office_id","status","status_description","total_workstations","nearest_lots","created_at","created_by","updated_at","updated_by"
])
write_csv("lot_seed.csv", lot_rows, [
    "id","lot_id","office_id","name","location","status","status_description","total_spots","total_regular_spots","total_ada_spots","total_ev_spots","available_spots","available_regular_spots","available_ada_spots","available_ev_spots","created_at","created_by","updated_at","updated_by"
])
write_csv("spot_seed.csv", spot_rows, [
    "id","spot_id","lot_id","sensor_id","status","status_description","type","row_number","position_number","created_at","created_by","updated_at","updated_by"
])
write_csv("sensor_seed.csv", sensor_rows, [
    "id","sensor_id","spot_id","status","status_description","type","created_at","created_by","updated_at","updated_by"
])
write_csv("employee_seed.csv", employee_rows, [
    "id","employee_id","name","office_id","block_id","status","start_date","end_date","type","last_parked_lot","preferred_lots","parking_tag","password","created_at","created_by","updated_at","updated_by"
])

if choice == "2":
    print("[INFO] Inserting into CockroachDB...")
    conn = get_connection(headless=args.headless)


    def insert_to_db(table, rows):
        with conn.cursor() as cur:
            for row in tqdm(rows, desc=f"Inserting {table}"):
                q = f"INSERT INTO park_smart.{table} VALUES ({','.join(['%s'] * len(row))})"
                cur.execute(q, row)
            conn.commit()


    insert_to_db("office", office_rows)
    insert_to_db("block", block_rows)
    insert_to_db("lot", lot_rows)
    insert_to_db("spot", spot_rows)
    insert_to_db("sensor", sensor_rows)
    insert_to_db("employee", employee_rows)
    conn.close()
    print("[INFO] Insert complete ✅")

end_time = time.time()
print("[END] Script completed at", datetime.now())
print(f"[INFO] Total elapsed time: {end_time - start_time:.2f} seconds")
print(f"[SUMMARY] Grand totals:")
print(f"  Total lots: {len(lot_rows)}")
print(f"  Total spots: {len(spot_rows)}")
print(f"  Total sensors: {len(sensor_rows)}")
print(f"  Total employees: {len(employee_rows)}")
print()

# Save summary to CSV
summary_filename = os.path.join(seed_dir, "summary_report.csv")
with open(summary_filename, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total lots", len(lot_rows)])
    writer.writerow(["Total spots", len(spot_rows)])
    writer.writerow(["Total sensors", len(sensor_rows)])
    writer.writerow(["Total employees", len(employee_rows)])
    writer.writerow(["EMPLOYEE count", emp_type_counter['EMPLOYEE']])
    writer.writerow(["CONTRACTOR count", emp_type_counter['CONTRACTOR']])
    writer.writerow(["ADMIN count", emp_type_counter['ADMIN']])
    writer.writerow(["Elapsed time (seconds)", round(end_time - start_time, 2)])

print(f"[INFO] Summary saved to {summary_filename}")
