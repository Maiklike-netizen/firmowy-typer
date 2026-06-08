import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="Firmowy Typer", page_icon="⚽", layout="centered")
st.title("⚽ Firmowy Typer - MŚ 2026")

# Funkcja pobierająca mecze z darmowego API (Zapamiętuje wynik na 1 godzinę!)
@st.cache_data(ttl=3600)
def pobierz_mecze():
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    # League=1 to ID dla Mistrzostw Świata, sezon 2026
    querystring = {"league": "1", "season": "2026"}
    headers = {
        "X-RapidAPI-Key": st.secrets["api"]["football_key"],
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        dane = response.json()
        return dane.get('response', [])
    except Exception as e:
        return []

wszystkie_mecze = pobierz_mecze()

# TESTOWANIE: Wyświetlmy surowe dane, żeby zobaczyć co dostajemy z API
if not wszystkie_mecze:
    st.warning("API nie zwróciło żadnych danych. Sprawdź, czy klucz API jest poprawny.")
else:
    st.write("DEBUG: Otrzymano liczbę meczów:", len(wszystkie_mecze))
    # Pokazujemy strukturę jednego meczu, żeby zobaczyć, jak wygląda 'status'
    st.json(wszystkie_mecze[0]) 

# ... (reszta kodu dalej)

# Nawiązanie połączenia z bazą w Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df_typy = conn.read(worksheet="Typy", ttl=0)
except Exception:
    # Awaryjna pusta tabela, jeśli arkusz jest nowy
    df_typy = pd.DataFrame(columns=["Pracownik", "ID_Meczu", "Typ_Gospodarz", "Typ_Gosc", "Punkty"])

st.write("### 📅 Wytypuj najbliższe mecze:")

# Wspólne pole na imię, by nie wpisywać go przy każdym meczu
pracownik = st.text_input("👤 Podaj swoje imię / Nick w firmie", placeholder="np. Janek")
st.divider()

if not nadchodzace_mecze:
    st.info("Obecnie brak nadchodzących meczów do wytypowania lub trwa ładowanie danych z serwera.")
else:
    # Generujemy estetyczne kafelki dla każdego meczu
    for mecz in nadchodzace_mecze:
        id_meczu = str(mecz['fixture']['id'])
        gospodarz = mecz['teams']['home']['name']
        gosc = mecz['teams']['away']['name']
        data_meczu = datetime.fromtimestamp(mecz['fixture']['timestamp']).strftime('%d.%m.%Y %H:%M')
        
        # Tworzymy osobny formularz dla każdego spotkania
        with st.form(f"form_mecz_{id_meczu}"):
            st.markdown(f"#### 🏟️ {gospodarz} vs {gosc}")
            st.caption(f"🕒 Czas rozpoczęcia: {data_meczu}")
            
            kol1, kol2 = st.columns(2)
            with kol1:
                typ_gospodarz = st.number_input(f"Gole - {gospodarz}", min_value=0, step=1, key=f"gosp_{id_meczu}")
            with kol2:
                typ_gosc = st.number_input(f"Gole - {gosc}", min_value=0, step=1, key=f"gosc_{id_meczu}")
                
            zapisz = st.form_submit_button("Zapisz typ")
            
            # Logika po kliknięciu
            if zapisz:
                if not pracownik:
                    st.error("Wpisz swoje imię na samej górze ekranu przed zapisaniem typu!")
                else:
                    # Sprawdzamy, czy gracz już nie typował tego meczu
                    if not df_typy.empty and ((df_typy['Pracownik'] == pracownik) & (df_typy['ID_Meczu'].astype(str) == id_meczu)).any():
                        st.warning("Odrzucono! Już oddałeś swój typ na ten mecz.")
                    else:
                        nowy_typ = pd.DataFrame([{
                            "Pracownik": pracownik,
                            "ID_Meczu": id_meczu,
                            "Typ_Gospodarz": typ_gospodarz,
                            "Typ_Gosc": typ_gosc,
                            "Punkty": 0
                        }])
                        zaktualizowane_typy = pd.concat([df_typy, nowy_typ], ignore_index=True)
                        conn.update(worksheet="Typy", data=zaktualizowane_typy)
                        df_typy = zaktualizowane_typy 
                        st.success(f"Zapisano typ {typ_gospodarz}:{typ_gosc} dla spotkania {gospodarz} - {gosc}!")

st.divider()
st.subheader("Sprawdź, co typują inni:")
st.dataframe(df_typy, use_container_width=True)
