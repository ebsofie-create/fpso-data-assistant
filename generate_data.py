
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
RAW = Path(__file__).parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

DAYS = 60
START = pd.Timestamp("2026-08-01")

VESSELS = ["FPSO Aurora", "FPSO Borealis", "FPSO Corona"]
EQUIPMENT_TYPES = {
    # type: (normal temp C, normal vibration mm/s, normal pressure bar)
    "Gas compressor": (85, 3.0, 45),
    "Water injection pump": (60, 2.2, 120),
    "Crude export pump": (55, 2.0, 30),
    "Power generator": (90, 2.8, 8),
}

# ---------------------------------------------------------------- equipment
equipment = []
for v_i, vessel in enumerate(VESSELS):
    for e_i, etype in enumerate(EQUIPMENT_TYPES):
        equipment.append(
            {
                "equipment_id": f"{vessel.split()[1][:3].upper()}-{e_i + 1:02d}",
                "vessel": vessel,
                "equipment_type": etype,
            }
        )
equipment = pd.DataFrame(equipment)

# ---------------------------------------------------------------- failures
# Pick a few equipment units that will fail. Before each failure, vibration
# and temperature drift upwards (the "signal" a root-cause analysis should find).
failure_modes = [
    ("Bearing wear", "vibration"),
    ("Seal leakage", "pressure"),
    ("Cooling degradation", "temperature"),
]
failures = []
failing_units = rng.choice(equipment["equipment_id"], size=6, replace=False)
for i, eq in enumerate(failing_units):
    mode, driver = failure_modes[i % len(failure_modes)]
    start = START + pd.Timedelta(hours=int(rng.integers(15 * 24, (DAYS - 5) * 24)))
    downtime = float(rng.choice([6, 12, 18, 30, 48]))
    failures.append(
        {
            "failure_id": f"F{i + 1:03d}",
            "equipment_id": eq,
            "failure_start": start,
            "downtime_hours": downtime,
            "failure_mode": mode,
            "_driver": driver,
        }
    )
failures = pd.DataFrame(failures)

# ---------------------------------------------------------------- sensor data
hours = pd.date_range(START, periods=DAYS * 24, freq="h")
rows = []
for _, eq in equipment.iterrows():
    t0, v0, p0 = EQUIPMENT_TYPES[eq["equipment_type"]]
    temp = t0 + rng.normal(0, 1.5, len(hours))
    vib = v0 + rng.normal(0, 0.25, len(hours))
    pres = p0 + rng.normal(0, p0 * 0.02, len(hours))
    running = np.ones(len(hours), dtype=bool)

    for _, f in failures[failures["equipment_id"] == eq["equipment_id"]].iterrows():
        idx = hours.get_loc(f["failure_start"])
        ramp = np.linspace(0, 1, 72)  # 72 h degradation before failure
        lo = idx - 72
        if f["_driver"] == "vibration":
            vib[lo:idx] += ramp * v0 * 1.8
            temp[lo:idx] += ramp * 6
        elif f["_driver"] == "pressure":
            pres[lo:idx] -= ramp * p0 * 0.25
        else:
            temp[lo:idx] += ramp * 18
        running[idx : idx + int(f["downtime_hours"])] = False

    for h, ts in enumerate(hours):
        if not running[h]:
            continue  # no readings while the equipment is down
        rows.append(
            {
                "timestamp": ts,
                "equipment_id": eq["equipment_id"],
                "temperature": round(temp[h], 2),
                "temp_unit": "C",
                "vibration_mm_s": round(vib[h], 3),
                "pressure_bar": round(pres[h], 2),
            }
        )

sensors = pd.DataFrame(rows)

# --- make it messy -----------------------------------------------------------
n = len(sensors)
# 1) ~3 % of temperatures logged in Fahrenheit (one vessel's legacy logger)
f_idx = sensors.sample(frac=0.03, random_state=1).index
sensors.loc[f_idx, "temperature"] = (sensors.loc[f_idx, "temperature"] * 9 / 5 + 32).round(2)
sensors.loc[f_idx, "temp_unit"] = "F"
# 2) sensor glitches
for seed, col in enumerate(["temperature", "vibration_mm_s", "pressure_bar"]):
    g_idx = sensors.sample(n=40, random_state=10 + seed).index
    sensors.loc[g_idx, col] = 9999
# 3) missing values
for seed, col in enumerate(["temperature", "vibration_mm_s", "pressure_bar"]):
    m_idx = sensors.sample(frac=0.01, random_state=20 + seed).index
    sensors.loc[m_idx, col] = np.nan
# 4) duplicated rows
sensors = pd.concat([sensors, sensors.sample(n=300, random_state=3)])
# 5) two timestamp formats
ts_str = sensors["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
alt = sensors.sample(frac=0.2, random_state=4).index
ts_str.loc[alt] = sensors.loc[alt, "timestamp"].dt.strftime("%d.%m.%Y %H:%M")
sensors["timestamp"] = ts_str
sensors = sensors.sample(frac=1, random_state=5).reset_index(drop=True)

# ---------------------------------------------------------------- maintenance log
notes_by_mode = {
    "Bearing wear": [
        "Operator reported unusual noise from drive end.",
        "Lube oil sample showed elevated metal particles.",
        "Vibration alarm acknowledged, monitoring continued.",
    ],
    "Seal leakage": [
        "Minor leak observed at mechanical seal, drip tray placed.",
        "Seal flush flow lower than normal.",
        "Discharge pressure fluctuating, cause not identified.",
    ],
    "Cooling degradation": [
        "Cooling water inlet temperature higher than usual.",
        "Heat exchanger fouling suspected, cleaning postponed.",
        "High temperature alarm, load reduced temporarily.",
    ],
}
routine = [
    "Routine inspection, no findings.",
    "Filter replaced as per schedule.",
    "Lubrication performed.",
    "Calibration of pressure transmitter completed.",
]
maint = []
for _, eq in equipment.iterrows():
    for _ in range(rng.integers(3, 7)):
        maint.append(
            {
                "date": (START + pd.Timedelta(days=int(rng.integers(0, DAYS)))).date(),
                "equipment_id": eq["equipment_id"],
                "work_type": "Preventive",
                "note": rng.choice(routine),
            }
        )
for _, f in failures.iterrows():
    for k, note in enumerate(notes_by_mode[f["failure_mode"]]):
        maint.append(
            {
                "date": (f["failure_start"] - pd.Timedelta(days=4 - k)).date(),
                "equipment_id": f["equipment_id"],
                "work_type": "Observation",
                "note": note,
            }
        )
    maint.append(
        {
            "date": (f["failure_start"] + pd.Timedelta(hours=f["downtime_hours"])).date(),
            "equipment_id": f["equipment_id"],
            "work_type": "Corrective",
            "note": f"Equipment tripped. Repair completed after {f['downtime_hours']:.0f} h.",
        }
    )
maint = pd.DataFrame(maint).sort_values("date")

# ---------------------------------------------------------------- save
equipment.to_csv(RAW / "equipment.csv", index=False)
sensors.to_csv(RAW / "sensor_readings.csv", index=False)
failures.drop(columns="_driver").to_csv(RAW / "failure_events.csv", index=False)
maint.to_csv(RAW / "maintenance_log.csv", index=False)

print(f"Wrote {len(equipment)} equipment, {len(sensors):,} sensor rows, "
      f"{len(failures)} failures, {len(maint)} maintenance entries to {RAW}")