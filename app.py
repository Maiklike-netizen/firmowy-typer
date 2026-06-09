import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Konfiguracja strony
st.set_page_config(page_title="Firmowy Typer MŚ 2026", page_icon="⚽", layout="centered")
st.title("⚽ Firmowy Typer - MŚ 2026")

# --- FUNKCJA POBIERANIA DANYCH Z FOOTBALL-DATA.ORG ---
@st.cache_data(ttl=600) # Odświeżaj co 10 minut
def pobierz_mecze_mundial():
    # 'WC' to kod dla World Cup w API football-data.org
    url = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {
        "X-Auth-Token": "0ad260bc8caa424994a2a11512f3c21b"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get('matches', [])
    except Exception as e:
        return f"Błąd połączenia z API: {e}"

# --- POŁĄCZENIE Z GOOGLE SHEETS (dla typów) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_typy = conn.read(worksheet="Typy", ttl=0)
except Exception:
    # Zabezpieczenie, jeśli arkusz jest pusty lub nie ma kolumn
    df_typy = pd.DataFrame(columns=["Pracownik", "ID_Meczu", "Gospodarz", "Gosc", "Typ_Gospodarz", "Typ_Gosc", "Data_Zapisu"])

# Pobieranie meczów
mecze_api = pobierz_mecze_mundial()

st.write("### 📅 Nadchodzące i aktualne mecze")
pracownik = st.text_input("👤 Podaj swoje imię / Nick", placeholder="np. Jan Kowalski")
st.divider()

if isinstance(mecze_api, str):
    st.error(mecze_api)
elif not mecze_api:
    st.warning("API nie zwróciło żadnych meczów. Możliwe, że dane o MŚ 2026 nie są jeszcze aktywne w football-data.org.")
else:
    teraz = datetime.utcnow() # API zwraca czas w UTC
    
    for mecz in mecze_api:
        id_m = str(mecz['id'])
        
        # Pobieranie nazw drużyn (jeśli są już znane, inaczej API podaje "TBD")
        gosp = mecz['homeTeam'].get('name', 'Nieznany (TBD)')
        gosc = mecz['awayTeam'].get('name', 'Nieznany (TBD)')
        
        # Czas meczu i formatowanie
        data_meczu_utc = datetime.strptime(mecz['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
        data_meczu_lokalna = data_meczu_utc + timedelta(hours=2) # Dopasowanie do polskiego czasu letniego (CEST)
        data_str = data_meczu_lokalna.strftime("%d.%m.%Y %H:%M")
        
        # Ustalanie statusu po polsku
        status_api = mecz['status']
        if status_api in ['SCHEDULED', 'TIMED']:
            status_pl = "🟢 Zaplanowany"
            czy_mozna_typowac = teraz < data_meczu_utc
        elif status_api in ['IN_PLAY', 'PAUSED']:
            status_pl = "🟡 W trakcie"
            czy_mozna_typowac = False
        elif status_api == 'FINISHED':
            status_pl = "🔴 Zakończony"
            czy_mozna_typowac = False
        else:
            status_pl = f"⚪ Inny ({status_api})"
            czy_mozna_typowac = False

        # Wyświetlanie karty meczu
        with st.container(border=True):
            cols = st.columns([3, 1])
            cols[0].subheader(f"🏟️ {gosp} vs {gosc}")
            cols[1].markdown(f"**{status_pl}**")
            st.caption(f"🕒 Start: {data_str}")
            
            # Formularz tylko dla meczów z otwartym oknem typowania
            if czy_mozna_typowac:
                with st.form(f"form_{id_m}"):
                    c1, c2 = st.columns(2)
                    tg = c1.number_input(f"Gole {gosp}", min_value=0, step=1, key=f"tg_{id_m}")
                    tgo = c2.number_input(f"Gole {gosc}", min_value=0, step=1, key=f"tgo_{id_m}")
                    
                    zapisz = st.form_submit_button("Zapisz typ")
                    if zapisz:
                        # Weryfikacja po stronie serwera (na wypadek, gdyby ktoś długo trzymał otwartą stronę)
                        if datetime.utcnow() >= data_meczu_utc:
                            st.error("Czas minął! Mecz już się rozpoczął.")
                        elif not pracownik:
                            st.error("Wpisz swoje imię, aby zapisać typ!")
                        else:
                            nowy_wiersz = pd.DataFrame([{
                                "Pracownik": pracownik,
                                "ID_Meczu": id_m,
                                "Gospodarz": gosp,
                                "Gosc": gosc,
                                "Typ_Gospodarz": tg,
                                "Typ_Gosc": tgo,
                                "Data_Zapisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }])
                            df_typy = pd.concat([df_typy, nowy_wiersz], ignore_index=True)
                            conn.update(worksheet="Typy", data=df_typy)
                            st.success(f"Zapisano typ {tg}:{tgo} dla {pracownik}!")
                            st.rerun()
            else:
                if status_api == 'FINISHED':
                    wynik_gosp = mecz['score']['fullTime'].get('home', '?')
                    wynik_gosc = mecz['score']['fullTime'].get('away', '?')
                    st.info(f"Typowanie zamknięte. Wynik końcowy: **{wynik_gosp} : {wynik_gosc}**")
                else:
                    st.warning("Typowanie zamknięte. Mecz wkrótce się rozpocznie lub już trwa.")

st.divider()
st.subheader("📊 Twoje i firmowe typy (z bazy)")
st.dataframe(df_typy, use_container_width=True)
