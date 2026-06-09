import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Firmowy Typer", page_icon="⚽", layout="centered")
st.title("⚽ Firmowy Typer - MŚ 2026")

# Funkcja pobierania z API
@st.cache_data(ttl=3600)
def pobierz_mecze_mundial():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-key": st.secrets["api"]["football_key"],
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    # Zgodnie z poradnikiem: League 1, Season 2026
    querystring = {"league": "1", "season": "2026"}
    try:
        response = requests.get(url, headers=headers, params=querystring)
        return response.json().get('response', [])
    except:
        return []

# Pobieramy mecze
mecze = pobierz_mecze_mundial()

# Połączenie z Google Sheets na typy
conn = st.connection("gsheets", type=GSheetsConnection)
df_typy = conn.read(worksheet="Typy", ttl=0)

pracownik = st.text_input("👤 Podaj swoje imię / Nick")

st.write("### 📅 Nadchodzące mecze MŚ 2026")

if not mecze:
    st.warning("API-Football na razie nie zwraca meczów MŚ 2026 (status pusty). Jeśli mecz zaraz się zaczyna, sprawdź to później.")
else:
    for mecz in mecze:
        # Wyświetlamy tylko mecze, które jeszcze się nie zaczęły
        if mecz['fixture']['status']['short'] == 'NS':
            gosp = mecz['teams']['home']['name']
            gosc = mecz['teams']['away']['name']
            id_m = str(mecz['fixture']['id'])
            
            with st.form(f"form_{id_m}"):
                st.write(f"**{gosp} vs {gosc}**")
                c1, c2 = st.columns(2)
                tg = c1.number_input(f"Gole {gosp}", min_value=0, step=1, key=f"tg_{id_m}")
                tgo = c2.number_input(f"Gole {gosc}", min_value=0, step=1, key=f"tgo_{id_m}")
                
                if st.form_submit_button("Zapisz typ"):
                    if not pracownik:
                        st.error("Wpisz imię!")
                    else:
                        nowy = pd.DataFrame([{"Pracownik": pracownik, "ID_Meczu": id_m, "Typ_Gospodarz": tg, "Typ_Gosc": tgo}])
                        df_typy = pd.concat([df_typy, nowy], ignore_index=True)
                        conn.update(worksheet="Typy", data=df_typy)
                        st.success("Zapisano!")
                        st.rerun()

st.divider()
st.dataframe(df_typy, use_container_width=True)
