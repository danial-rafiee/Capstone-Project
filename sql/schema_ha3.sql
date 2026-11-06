-- HA3 demo schema. UTC timestamps are stored in DATETIME(6).
-- This creates missing objects; it does not migrate an existing schema.
CREATE DATABASE IF NOT EXISTS smart_energy_ha3 CHARACTER SET utf8mb4;
USE smart_energy_ha3;

CREATE TABLE IF NOT EXISTS buildings (
    building_id INT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    CHECK (building_id > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS meters (
    meter_id INT PRIMARY KEY,
    building_id INT NOT NULL,
    name VARCHAR(120) NOT NULL,
    CHECK (meter_id > 0),
    FOREIGN KEY (building_id) REFERENCES buildings(building_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS readings (
    reading_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    meter_id INT NOT NULL,
    start_utc DATETIME(6) NOT NULL,
    end_utc DATETIME(6) NOT NULL,
    energy_kwh DECIMAL(18,6) NOT NULL,
    CHECK (end_utc > start_utc),
    CHECK (energy_kwh >= 0),
    UNIQUE KEY uq_reading_interval (meter_id, start_utc, end_utc),
    FOREIGN KEY (meter_id) REFERENCES meters(meter_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS coach_evaluations (
    evaluation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    building_id INT NOT NULL,
    score DECIMAL(5,2) NOT NULL,
    penalty_eur DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    peak_detected BOOLEAN NOT NULL DEFAULT FALSE,
    advice_summary VARCHAR(255) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    FOREIGN KEY (building_id) REFERENCES buildings(building_id)
) ENGINE=InnoDB;
