import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib
from datetime import datetime

# === Load CSV ===
csv_path = "sensor_logs_export.csv"
df = pd.read_csv(csv_path, parse_dates=['event_timestamp'])

# === Prepare Data ===
df['timestamp'] = df['event_timestamp']
df.set_index('timestamp', inplace=True)

# Group into 30-minute buckets
grouped = df.groupby([pd.Grouper(freq='30Min'), 'lot_id', 'name', 'event_type']).size().unstack(fill_value=0).reset_index()
grouped['entry'] = grouped.get('entry', 0)
grouped['exit'] = grouped.get('exit', 0)
grouped['net_change'] = grouped['entry'] - grouped['exit']

# === Reconstruct Occupancy ===
occupancy_dfs = []
for lot_id in grouped['lot_id'].unique():
    lot_df = grouped[grouped['lot_id'] == lot_id].copy()
    lot_df.sort_values('timestamp', inplace=True)
    lot_df['occupancy'] = lot_df['net_change'].cumsum()
    occupancy_dfs.append(lot_df)

df_occupancy = pd.concat(occupancy_dfs)
df_occupancy['weekday'] = df_occupancy['timestamp'].dt.day_name()
df_occupancy['hour'] = df_occupancy['timestamp'].dt.hour
df_occupancy['minute'] = df_occupancy['timestamp'].dt.minute
df_occupancy['date'] = df_occupancy['timestamp'].dt.date

# === Train ML Model ===
features = ['lot_id', 'weekday', 'hour', 'minute']
df_model = df_occupancy.dropna(subset=['lot_id', 'weekday', 'hour', 'minute', 'occupancy']).copy()

# Encode lot_id and weekday
df_model['lot_id_encoded'] = df_model['lot_id'].astype('category').cat.codes
df_model['weekday_encoded'] = df_model['weekday'].astype('category').cat.codes

lot_id_map = df_model[['lot_id', 'lot_id_encoded']].drop_duplicates().set_index('lot_id').to_dict()['lot_id_encoded']
weekday_map = df_model[['weekday', 'weekday_encoded']].drop_duplicates().set_index('weekday').to_dict()['weekday_encoded']
reverse_weekday_map = {v: k for k, v in weekday_map.items()}
reverse_lot_map = df_model[['lot_id_encoded', 'name']].drop_duplicates().set_index('lot_id_encoded')['name'].to_dict()

X = df_model[['lot_id_encoded', 'weekday_encoded', 'hour', 'minute']]
y = df_model['occupancy']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))

# Save model
model_file = "availability_model.joblib"
joblib.dump((model, lot_id_map, weekday_map), model_file)

print(f"✅ Model trained and saved to {model_file}, RMSE: {rmse:.2f}")

# === Insights ===

# 1. Peak occupancy hour per lot/weekday
print("\n📈 Peak Occupancy Hours per Lot/Weekday:")
for (lot_id, name) in df_occupancy[['lot_id', 'name']].drop_duplicates().values:
    for weekday in df_occupancy['weekday'].unique():
        df_sub = df_occupancy[(df_occupancy['lot_id'] == lot_id) & (df_occupancy['weekday'] == weekday)]
        if not df_sub.empty:
            avg_by_hour = df_sub.groupby('hour')['occupancy'].mean()
            peak_hour = avg_by_hour.idxmax()
            print(f"  Lot {name} ({lot_id}), {weekday}: {peak_hour}:00")

# 2. Highest occupancy moment
max_occ = df_occupancy.loc[df_occupancy['occupancy'].idxmax()]
print(f"\n🚗 Highest Occupancy: {max_occ['occupancy']} at {max_occ['timestamp']} in Lot {max_occ['name']}")

# 3. Busiest 30-min incoming/outgoing traffic
print("\n🔼 Busiest 30-min Incoming Traffic:")
incoming_counts = df_occupancy.groupby(['date', 'timestamp'])['entry'].sum()
incoming_peak = incoming_counts.groupby('date').idxmax()
for date, (d, ts) in incoming_peak.items():
    print(f"  {d}: {ts.time()}")

print("\n🔽 Busiest 30-min Outgoing Traffic:")
outgoing_counts = df_occupancy.groupby(['date', 'timestamp'])['exit'].sum()
outgoing_peak = outgoing_counts.groupby('date').idxmax()
for date, (d, ts) in outgoing_peak.items():
    print(f"  {d}: {ts.time()}")

# === Predict Future Availability ===
print("\n📅 Predict Occupancy for a Future Timestamp:")
try:
    input_str = input("Enter timestamp (YYYY-MM-DD HH:MM): ").strip()
    input_lot = int(input("Enter lot_id: ").strip())
    dt = datetime.strptime(input_str, "%Y-%m-%d %H:%M")
    weekday_name = dt.strftime('%A')
    hour = dt.hour
    minute = dt.minute

    encoded_lot = lot_id_map.get(input_lot)
    encoded_weekday = weekday_map.get(weekday_name)

    if encoded_lot is None:
        print(f"❌ Lot ID {input_lot} not found in training data.")
    elif encoded_weekday is None:
        print(f"❌ Weekday '{weekday_name}' not found in training data.")
    else:
        pred_input = pd.DataFrame([[encoded_lot, encoded_weekday, hour, minute]],
                                  columns=['lot_id_encoded', 'weekday_encoded', 'hour', 'minute'])
        pred = model.predict(pred_input)[0]
        name = reverse_lot_map[encoded_lot]
        print(f"🔮 Predicted occupancy for Lot {name} at {dt}: {pred:.0f} cars")
except Exception as e:
    print(f"❌ Error: {e}")
