import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="Firmowy Typer", page_icon="⚽", layout="centered")
st.title("⚽ Firmowy Typer - MŚ 2026")

# --- FUNKCJA POBIERANIA MECZÓW ---
@st.cache_data(ttl=3600)
def pobierz_mecze():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-key": st.secrets["api"]["football_key"],
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    # ID 1 to standardowe ID dla Mistrzostw Świata w API-Football
    querystring = {"league": "1", "season": "2026"}
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        dane = response.json()
        return dane.get('response', [])
    except Exception as e:
        st.error(f"Błąd połączenia z API: {e}")
        return []

# --- GŁÓWNA LOGIKA ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Pobranie danych
wszystkie_mecze = pobierz_mecze()
try:
    df_typy = conn.read(worksheet="Typy", ttl=0)
except Exception:
    df_typy = pd.DataFrame(columns=["Pracownik", "ID_Meczu", "Typ_Gospodarz", "Typ_Gosc", "Punkty"])

st.write("### 📅 Wytypuj najbliższe mecze:")
pracownik = st.text_input("👤 Podaj swoje imię / Nick", placeholder="np. Janek")

if not wszystkie_mecze:
    st.info("Brak meczów z API. Sprawdź: 1. Czy klucz API jest aktywny w RapidAPI, 2. Czy masz subskrypcję 'Free' na v3 API-Football.")
else:
    # Filtrujemy mecze (status NS = Not Started)
    nadchodzace = [m for m in wszystkie_mecze if m['fixture']['status']['short'] == 'NS'][:10]
    
    for mecz in nadchodzace:
        id_meczu = str(mecz['fixture']['id'])
        gosp_name = mecz['teams']['home']['name']
        gosc_name = mecz['teams']['away']['name']
        data = datetime.fromtimestamp(mecz['fixture']['timestamp']).strftime('%d.%m %H:%M')
        
        with st.form(f"form_{id_meczu}"):
            st.markdown(f"**{gosp_name} vs {gosc_name}** | {data}")
            c1, c2 = st.columns(2)
            typ_g = c1.number_input(f"{gosp_name}", min_value=0, step=1, key=f"g_{id_meczu}")
            typ_gs = c2.number_input(f"{gosc_name}", min_value=0, step=1, key=f"gs_{id_meczu}")
            
            if st.form_submit_button("Zapisz typ"):
                if not pracownik:
                    st.error("Podaj imię!")
                else:
                    nowy = pd.DataFrame([{"Pracownik": pracownik, "ID_Meczu": id_meczu, "Typ_Gospodarz": typ_g, "Typ_Gosc": typ_gs, "Punkty": 0}])
                    zaktualizowane = pd.concat([df_typy, nowy], ignore_index=True)
                    conn.update(worksheet="Typy", data=zaktualizowane)
                    st.success("Zapisano!")
                    st.rerun()

st.divider()
st.subheader("📊 Aktualne typy w arkuszu")
st.dataframe(df_typy, use_container_width=True)
