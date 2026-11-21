import sqlite3

import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)

# ---------------------------------------------------------------
# DEL 1: Legg dataene inn i en database
# SQLite er en enkel database som lagres som én fil (data/fpso.db).
# ---------------------------------------------------------------
tabeller = {
    "equipment": pd.read_csv("data/raw/equipment.csv"),
    "sensor_readings": pd.read_csv("data/clean_sensor_readings.csv"),
    "failure_events": pd.read_csv("data/raw/failure_events.csv"),
    "maintenance_log": pd.read_csv("data/raw/maintenance_log.csv"),
}

con = sqlite3.connect("data/fpso.db")
for navn, tabell in tabeller.items():
    tabell.to_sql(navn, con, if_exists="replace", index=False)
    print(f"Lagret {navn}: {len(tabell)} rader")


def sql(sporring):
    """Kjør en SQL-spørring og returner svaret som en tabell."""
    return pd.read_sql_query(sporring, con)


# ---------------------------------------------------------------
# DEL 2: Enkle SQL-spørringer for å bli kjent med dataene
# ---------------------------------------------------------------
print("\n=== Alt utstyr på FPSO Aurora ===")
print(sql("""
    SELECT equipment_id, equipment_type
    FROM equipment
    WHERE vessel = 'FPSO Aurora'
"""))

print("\n=== Alle feil, med skip og utstyrstype ===")
print(sql("""
    SELECT f.failure_id, e.vessel, e.equipment_type,
           f.failure_mode, f.downtime_hours
    FROM failure_events f
    JOIN equipment e ON f.equipment_id = e.equipment_id
    ORDER BY f.downtime_hours DESC
"""))

# ---------------------------------------------------------------
# DEL 3: Nøkkeltall - tilgjengelighet per skip
#
# Definisjoner (viktig å kunne forklare!):
#   Periode         = antall timer fra første til siste måling
#   Nedetid         = summen av timer utstyret sto stille pga. feil
#   Tilgjengelighet = (total tid - nedetid) / total tid
#
# Hvert skip har 4 utstyrsenheter, så total tid per skip
# er periode * antall utstyr.
# ---------------------------------------------------------------
print("\n=== Tilgjengelighet per skip ===")
print(sql("""
    WITH periode AS (
        SELECT (julianday(MAX(timestamp)) - julianday(MIN(timestamp))) * 24 + 1 AS timer
        FROM sensor_readings
    ),
    per_skip AS (
        SELECT e.vessel,
               COUNT(DISTINCT e.equipment_id)     AS antall_utstyr,
               COUNT(f.failure_id)                AS antall_feil,
               COALESCE(SUM(f.downtime_hours), 0) AS nedetid_timer
        FROM equipment e
        LEFT JOIN failure_events f ON f.equipment_id = e.equipment_id
        GROUP BY e.vessel
    )
    SELECT s.vessel,
           s.antall_feil,
           s.nedetid_timer,
           ROUND(100.0 * (p.timer * s.antall_utstyr - s.nedetid_timer)
                 / (p.timer * s.antall_utstyr), 2) AS tilgjengelighet_prosent
    FROM per_skip s, periode p
    ORDER BY tilgjengelighet_prosent
"""))

con.close()

