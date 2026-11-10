-- SIMULATED B sample data; only initialized in a fresh Docker data volume.
-- The 07:00-09:00 UTC periods are 08:00-10:00 Europe/Berlin in November.
-- Current E=5 kWh, earlier reference R=7 kWh, current off-hours O=2 kWh.
USE smart_energy_ha3;

INSERT INTO buildings (building_id, name) VALUES (1, 'Demo Office');
INSERT INTO meters (meter_id, building_id, name) VALUES (101, 1, 'Main Meter');

INSERT INTO readings (meter_id, start_utc, end_utc, energy_kwh) VALUES
    (101, '2026-11-03 07:00:00', '2026-11-03 08:00:00', 3.000000),
    (101, '2026-11-03 08:00:00', '2026-11-03 09:00:00', 4.000000),
    (101, '2026-11-04 07:00:00', '2026-11-04 08:00:00', 2.000000),
    (101, '2026-11-04 08:00:00', '2026-11-04 09:00:00', 3.000000),
    -- Preserve the separate HA3 sample used by demo_capstone_b.py --mysql.
    (101, '2026-11-04 09:00:00', '2026-11-04 09:05:00', 3.000000),
    (101, '2026-11-04 09:05:00', '2026-11-04 09:10:00', 2.000000);
