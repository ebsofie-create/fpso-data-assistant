import pandas as pd

# Les inn sensordataene
df = pd.read_csv("data/raw/sensor_readings.csv")

print("=== DE FØRSTE 10 RADENE ===")
print(df.head(10))

print("\n=== KOLONNER OG DATATYPER ===")
print(df.info())

print("\n=== STATISTIKK ===")
print(df.describe())
