import psycopg2
import pandas as pd
import os

# Load credentials from local file
def load_credentials(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            lines = f.readlines()
            creds = dict(line.strip().split(': ') for line in lines)
            return creds['user'], creds['password']
    else:
        print("Credentials file not found. Please enter manually.")
        user = input("Enter DB user: ")
        password = input("Enter DB password: ")
        return user, password

# File path to your credentials
CRED_PATH = r'C:\Users\sunda\Downloads\ID\Tech\CockroachDB\pwd.txt'
user, password = load_credentials(CRED_PATH)

# Connect to CockroachDB
conn = psycopg2.connect(
    dbname="defaultdb",
    user=user,
    password=password,
    host="social-elves-11376.j77.aws-us-west-2.cockroachlabs.cloud",
    port=26257,
    sslmode="require"
)

# Query sensor logs with sensor and lot info (optional join)
query = """
SELECT
    s.lot_id,
    l.name,
    sl.sensor_id,
    event_type,
    event_timestamp,
    DATE(event_timestamp) AS event_date,
    EXTRACT(DOW FROM event_timestamp) AS weekday,
    EXTRACT(HOUR FROM event_timestamp) AS hour,
    EXTRACT(MINUTE FROM event_timestamp) AS minute
FROM
    parksmart.sensorlogs sl
JOIN
    parksmart.sensors s ON sl.sensor_id = s.sensor_id
JOIN
    parksmart.lots l ON s.lot_id = l.lot_id;
"""

# Read data into DataFrame
df = pd.read_sql_query(query, conn)

# Save to CSV
output_file = "sensor_logs_export.csv"
df.to_csv(output_file, index=False)
print(f"Sensor logs exported to {output_file}")

# Close DB connection
conn.close()
