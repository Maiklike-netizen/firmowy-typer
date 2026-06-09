import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="Firmowy Typer", page_icon="⚽", layout="centered")
st.title("⚽ Firmowy Typer - MŚ 2026")

# Inicjalizacja zmiennej na starcie
nadchodzace_mecze = []

@st.cache_data(ttl=3600)
def pobierz_mecze():
    # Sprawdź w dokumentacji API czy to jest poprawny URL
    url = "https://worldcup2026-api.com/matches" 
    try:
        response = requests.get(url)
        dane = response.json()
        return dane # Zwracamy listę meczów
    except Exception as e:
        st.error(f"Błąd połączenia z API: {e}")
        return []
st.write(pobierz_mecze())

# Pobranie danych
wszystkie_mecze = pobierz_mecze()

# Bezpieczne filtrowanie
if wszystkie_mecze:
    nadchodzace_mecze = [m for m in wszystkie_mecze if m['fixture']['status']['short'] in ['NS', 'TBD']]
    nadchodzace_mecze = sorted(nadchodzace_mecze, key=lambda x: x['fixture']['timestamp'])[:5]

# Połączenie z bazą
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df_typy = conn.read(worksheet="Typy", ttl=0)
except Exception:
    df_typy = pd.DataFrame(columns=["Pracownik", "ID_Meczu", "Typ_Gospodarz", "Typ_Gosc", "Punkty"])

st.write("### 📅 Wytypuj najbliższe mecze:")
pracownik = st.text_input("👤 Podaj swoje imię / Nick", placeholder="np. Janek")

if not nadchodzace_mecze:
    st.info("Brak nadchodzących meczów w API. Sprawdź, czy klucz API jest aktywny lub czy liga/sezon są poprawne.")
else:
    for mecz in nadchodzace_mecze:
        id_meczu = str(mecz['fixture']['id'])
        gospodarz = mecz['teams']['home']['name']
        gosc = mecz['teams']['away']['name']
        data_meczu = datetime.fromtimestamp(mecz['fixture']['timestamp']).strftime('%d.%m.%Y %H:%M')
        
        with st.form(f"form_mecz_{id_meczu}"):
            st.markdown(f"#### 🏟️ {gospodarz} vs {gosc}")
            st.caption(f"🕒 {data_meczu}")
            kol1, kol2 = st.columns(2)
            with kol1:
                typ_gosp = st.number_input(f"Gole - {gospodarz}", min_value=0, step=1, key=f"gosp_{id_meczu}")
            with kol2:
                typ_gosc = st.number_input(f"Gole - {gosc}", min_value=0, step=1, key=f"gosc_{id_meczu}")
            if st.form_submit_button("Zapisz typ"):
                if not pracownik:
                    st.error("Podaj imię!")
                else:
                    nowy_typ = pd.DataFrame([{"Pracownik": pracownik, "ID_Meczu": id_meczu, "Typ_Gospodarz": typ_gosp, "Typ_Gosc": typ_gosc, "Punkty": 0}])
                    zaktualizowane_typy = pd.concat([df_typy, nowy_typ], ignore_index=True)
                    conn.update(worksheet="Typy", data=zaktualizowane_typy)
                    st.success("Zapisano!")
