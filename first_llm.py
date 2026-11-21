import os
import sqlite3

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# Henter API-nøkkelen fra .env-filen (så den aldri står i koden)
load_dotenv()

# Groq bruker samme kode som OpenAI, vi peker bare til Groq sin adresse
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# Bytt til et modellnavn fra Models-siden i Groq Console
MODELL = "openai/gpt-oss-120b"

# ---------------------------------------------------------------
# DEL 1: Ditt første API-kall
# ---------------------------------------------------------------
svar = client.chat.completions.create(
    model=MODELL,
    max_tokens=1500,
    messages=[
        {"role": "user", "content": "Forklar kort hva en FPSO er, i to setninger."}
    ],
)
print("=== Første svar ===")
print(svar.choices[0].message.content)

# ---------------------------------------------------------------
# DEL 2: LLM + dine egne data
# Vi henter fakta fra databasen med SQL, gjør dem om til tekst,
# og ber modellen tolke dem.
# ---------------------------------------------------------------
con = sqlite3.connect("data/fpso.db")
feil = pd.read_sql_query("""
    SELECT e.vessel, e.equipment_type, f.failure_mode, f.downtime_hours
    FROM failure_events f
    JOIN equipment e ON f.equipment_id = e.equipment_id
""", con)
con.close()

tabell_som_tekst = feil.to_string(index=False)

instruks = (
    "Du er en erfaren pålitelighetsingeniør på FPSO-er. "
    "Svar kort og konkret, og begrunn med tallene du får. "
    "Ikke finn på tall som ikke står i dataene."
)
sporsmal = f"""Her er alle feil på flåten de siste 60 dagene:

{tabell_som_tekst}

Hvilket skip og hvilken feiltype bør prioriteres først, og hvorfor?"""

svar = client.chat.completions.create(
    model=MODELL,
    max_tokens=2000,
    messages=[
        {"role": "system", "content": instruks},
        {"role": "user", "content": sporsmal},
    ],
)
print("\n=== Analyse av dine data ===")
print(svar.choices[0].message.content)
