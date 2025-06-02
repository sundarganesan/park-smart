import streamlit as st
import pandas as pd
import psycopg2
import time
from datetime import datetime

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

def load_lot_data():
    conn = get_connection()
    query = "SELECT lot_id, name, available_spots, available_regular_spots, available_ev_spots, available_ada_spots FROM parksmart.lots ORDER BY lot_id"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def load_recent_sensor_logs(limit=10):
    conn = get_connection()
    query = f"""
        SELECT sensor_id, event_type, event_timestamp 
        FROM parksmart.sensorlogs 
        ORDER BY event_timestamp DESC 
        LIMIT {limit}
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Highlight changes between DataFrames
def highlight_diff(df, prev_df):
    if prev_df is None:
        return pd.DataFrame("", index=df.index, columns=df.columns)
    diffs = df != prev_df
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    for col in df.columns:
        if col in diffs:
            styles[col] = diffs[col].apply(lambda changed: "background-color: yellow" if changed else "")
    return styles

st.set_page_config(page_title="Live Parking Monitor", layout="wide")
st.title("🚗 Live Parking Simulation Dashboard")

lot_placeholder = st.empty()
sensor_placeholder = st.empty()

prev_df = None
refresh_interval = 3  # seconds

while True:
    try:
        df = load_lot_data()
        style_df = df.style.apply(highlight_diff, prev_df=prev_df, axis=None)
        lot_placeholder.dataframe(style_df, use_container_width=True, height=600)
        prev_df = df.copy()

        sensor_logs = load_recent_sensor_logs()
        sensor_placeholder.dataframe(sensor_logs, use_container_width=True)

        time.sleep(refresh_interval)
    except Exception as e:
        st.error(f"Error: {e}")
        break
