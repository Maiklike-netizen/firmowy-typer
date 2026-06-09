import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Firmowy Typer", page_icon="⚽", layout="centered")
st.title("⚽ Firmowy Typer - MŚ 2026")

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNKCJA API ---
@st.cache_data(ttl=3600)
def pobierz_dane_api(endpoint, querystring=None):
    url = f"https://v3.football.api-sports.io/{endpoint}"
    headers = {
        "x-rapidapi-key": st.secrets["api"]["football_key"],
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        return response.json().get('response', [])
    except Exception as e:
        return f"BŁĄD: {str(e)}"

# --- LOGIKA ---
st.write("### Diagnostyka połączenia:")
# Sprawdzamy listę lig, żeby znaleźć ID dla MŚ 2026
lista_lig = pobierz_dane_api("leagues", {"season": "2026", "country": "World"})

if isinstance(lista_lig, str):
    st.error(lista_lig)
else:
    st.success("Połączenie z API działa!")
    # Wyświetlamy znalezione ligi, żebyś mógł znaleźć ID dla "World Cup"
    df_lig = pd.DataFrame(lista_lig)
    st.write("Znalezione turnieje (szukaj World Cup):")
    st.dataframe(df_lig[['league', 'country']], use_container_width=True)

# Przykładowy formularz (zostaje bez zmian)
st.divider()
st.write("### 📅 Wytypuj mecz (po znalezieniu ID ligi):")
id_ligi = st.text_input("Wpisz ID ligi z tabeli powyżej:", "1")

if st.button("Pobierz mecze dla tej ligi"):
    mecze = pobierz_dane_api("fixtures", {"league": id_ligi, "season": "2026"})
    if isinstance(mecze, list) and len(mecze) > 0:
        st.write(f"Pobrano {len(mecze)} meczów!")
        st.json(mecze[0]) # Pokazuje strukturę pierwszego meczu
    else:
        st.warning("Brak meczów dla tego ID ligi.")
