import numpy as np
import pandas as pd

# Les inn rådataene
df = pd.read_csv("data/raw/sensor_readings.csv")
print("Rader før rydding:", len(df))

# ---------------------------------------------------------------
# PROBLEM 1: Tidsstempler i to ulike formater
# Noen er skrevet "2026-08-01 13:00:00", andre "01.08.2026 13:00".
# Vi prøver begge formatene og slår resultatene sammen.
# ---------------------------------------------------------------
format_1 = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
format_2 = pd.to_datetime(df["timestamp"], format="%d.%m.%Y %H:%M", errors="coerce")
df["timestamp"] = format_1.fillna(format_2)
print("Tidsstempler som ikke kunne leses:", df["timestamp"].isna().sum())

# ---------------------------------------------------------------
# PROBLEM 2: Duplikater (samme rad finnes to ganger)
# ---------------------------------------------------------------
antall_for = len(df)
df = df.drop_duplicates()
print("Duplikater fjernet:", antall_for - len(df))

# ---------------------------------------------------------------
# PROBLEM 3: Sensorfeil (verdien 9999)
# Vi gjør dem om til "mangler" (NaN), så de ikke ødelegger gjennomsnitt.
# ---------------------------------------------------------------
kolonner = ["temperature", "vibration_mm_s", "pressure_bar"]
print("Sensorfeil funnet:", (df[kolonner] == 9999).sum().sum())
df[kolonner] = df[kolonner].replace(9999, np.nan)

# ---------------------------------------------------------------
# PROBLEM 4: Fahrenheit -> Celsius
# Formel: (F - 32) * 5/9
# ---------------------------------------------------------------
er_fahrenheit = df["temp_unit"] == "F"
print("Fahrenheit-verdier omregnet:", er_fahrenheit.sum())
df.loc[er_fahrenheit, "temperature"] = (df.loc[er_fahrenheit, "temperature"] - 32) * 5 / 9
df = df.drop(columns="temp_unit")
df = df.rename(columns={"temperature": "temperature_c"})

# ---------------------------------------------------------------
# PROBLEM 5: Manglende verdier
# Korte hull (maks 3 timer) fylles med verdien midt mellom målingen
# før og etter (interpolering). Lengre hull lar vi stå tomme,
# for da ville vi funnet på data vi ikke vet noe om.
# Dette gjøres per utstyr, i tidsrekkefølge.
# ---------------------------------------------------------------
kolonner = ["temperature_c", "vibration_mm_s", "pressure_bar"]
df = df.sort_values(["equipment_id", "timestamp"])
print("Manglende verdier før utfylling:", df[kolonner].isna().sum().sum())
df[kolonner] = df.groupby("equipment_id")[kolonner].transform(
    lambda serie: serie.interpolate(limit=3, limit_area="inside")
)
print("Manglende verdier etter utfylling:", df[kolonner].isna().sum().sum())

# Lagre de ryddede dataene
df.to_csv("data/clean_sensor_readings.csv", index=False)
print("\nRader etter rydding:", len(df))
print(df.describe())