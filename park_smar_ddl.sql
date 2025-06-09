-- Switch to the target database
USE social_elves;

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS park_smart;

-- Office Table
CREATE TABLE park_smart.office (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office_id STRING NOT NULL,
    name STRING NOT NULL,
    address STRING,
    status STRING,
    status_description STRING,
    created_at TIMESTAMP DEFAULT current_timestamp,
    created_by STRING,
    updated_at TIMESTAMP DEFAULT current_timestamp,
    updated_by STRING
);
CREATE INDEX idx_office_office_id ON park_smart.office (office_id);

-- Block Table
CREATE TABLE park_smart.block (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_id STRING NOT NULL,
    name STRING NOT NULL,  -- Added name
    office_id UUID NOT NULL REFERENCES park_smart.office(id),
    status STRING,
    status_description STRING,
    total_workstations INT,
    nearest_lots STRING,
    created_at TIMESTAMP DEFAULT current_timestamp,
    created_by STRING,
    updated_at TIMESTAMP DEFAULT current_timestamp,
    updated_by STRING
);
CREATE INDEX idx_block_block_id ON park_smart.block (block_id);
CREATE INDEX idx_block_office_id ON park_smart.block (office_id);

-- Lot Table
CREATE TABLE park_smart.lot (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id STRING NOT NULL,
    office_id UUID NOT NULL REFERENCES park_smart.office(id),
    name STRING NOT NULL,
    location STRING,
    status STRING,
    status_description STRING,
    total_spots INT,
    total_regular_spots INT,
    total_ada_spots INT,
    total_ev_spots INT,
    available_spots INT,
    available_regular_spots INT,
    available_ada_spots INT,
    available_ev_spots INT,
    created_at TIMESTAMP DEFAULT current_timestamp,
    created_by STRING,
    updated_at TIMESTAMP DEFAULT current_timestamp,
    updated_by STRING
);
CREATE INDEX idx_lot_lot_id ON park_smart.lot (lot_id);
CREATE INDEX idx_lot_office_id ON park_smart.lot (office_id);

-- Spot Table
CREATE TABLE park_smart.spot (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spot_id STRING NOT NULL,
    lot_id UUID NOT NULL REFERENCES park_smart.lot(id),
    sensor_id UUID,
    status STRING,
    status_description STRING,
    type STRING,
    row_number INT,
    position_number INT,
    created_at TIMESTAMP DEFAULT current_timestamp,
    created_by STRING,
    updated_at TIMESTAMP DEFAULT current_timestamp,
    updated_by STRING
);
CREATE INDEX idx_spot_spot_id ON park_smart.spot (spot_id);
CREATE INDEX idx_spot_lot_id ON park_smart.spot (lot_id);
CREATE INDEX idx_spot_sensor_id ON park_smart.spot (sensor_id);

-- Sensor Table
CREATE TABLE park_smart.sensor (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sensor_id STRING NOT NULL,
    spot_id UUID NOT NULL REFERENCES park_smart.spot(id),
    status STRING,
    status_description STRING,
    type STRING,
    created_at TIMESTAMP DEFAULT current_timestamp,
    created_by STRING,
    updated_at TIMESTAMP DEFAULT current_timestamp,
    updated_by STRING
);
CREATE INDEX idx_sensor_sensor_id ON park_smart.sensor (sensor_id);
CREATE INDEX idx_sensor_spot_id ON park_smart.sensor (spot_id);

-- Sensor Logs Table
CREATE TABLE park_smart.sensor_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_timestamp TIMESTAMP NOT NULL,
    event_type STRING NOT NULL,
    sensor_id UUID NOT NULL REFERENCES park_smart.sensor(id),
    parking_tag STRING,
    created_at TIMESTAMP DEFAULT current_timestamp,
    created_by STRING,
    updated_at TIMESTAMP DEFAULT current_timestamp,
    updated_by STRING
);
CREATE INDEX idx_sensor_logs_sensor_id ON park_smart.sensor_logs (sensor_id);
CREATE INDEX idx_sensor_logs_event_timestamp ON park_smart.sensor_logs (event_timestamp);

-- Employee Table
CREATE TABLE park_smart.employee (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id STRING NOT NULL,
    name STRING NOT NULL,
    office_id UUID NOT NULL REFERENCES park_smart.office(id),
    block_id UUID REFERENCES park_smart.block(id),
    status STRING,
    start_date DATE,
    end_date DATE,
    type STRING,
    last_parked_lot UUID REFERENCES park_smart.lot(id),
    preferred_lots STRING,
    parking_tag STRING UNIQUE,
	password STRING,
    created_at TIMESTAMP DEFAULT current_timestamp,
    created_by STRING,
    updated_at TIMESTAMP DEFAULT current_timestamp,
    updated_by STRING
);
CREATE INDEX idx_employee_employee_id ON park_smart.employee (employee_id);
CREATE INDEX idx_employee_office_id ON park_smart.employee (office_id);
CREATE INDEX idx_employee_block_id ON park_smart.employee (block_id);
CREATE INDEX idx_employee_last_parked_lot ON park_smart.employee (last_parked_lot);

-- Employee Parking History Table
CREATE TABLE park_smart.employee_parking_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES park_smart.employee(id),
    event_timestamp TIMESTAMP NOT NULL,
    event_type STRING NOT NULL,
    lot_id UUID REFERENCES park_smart.lot(id),
    created_at TIMESTAMP DEFAULT current_timestamp,
    created_by STRING,
    updated_at TIMESTAMP DEFAULT current_timestamp,
    updated_by STRING
);
CREATE INDEX idx_eph_employee_id ON park_smart.employee_parking_history (employee_id);
CREATE INDEX idx_eph_lot_id ON park_smart.employee_parking_history (lot_id);
CREATE INDEX idx_eph_event_timestamp ON park_smart.employee_parking_history (event_timestamp);

-- Lot History Table
CREATE TABLE park_smart.lot_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id UUID NOT NULL REFERENCES park_smart.lot(id),
    history_timestamp TIMESTAMP NOT NULL,
    total_spots INT,
    total_regular_spots INT,
    total_ada_spots INT,
    total_ev_spots INT,
    available_spots INT,
    available_regular_spots INT,
    available_ada_spots INT,
    available_ev_spots INT,
    created_at TIMESTAMP DEFAULT current_timestamp,
    created_by STRING,
    updated_at TIMESTAMP DEFAULT current_timestamp,
    updated_by STRING
);
CREATE INDEX idx_lot_history_lot_id ON park_smart.lot_history (lot_id);
CREATE INDEX idx_lot_history_history_timestamp ON park_smart.lot_history (history_timestamp);
