import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# Konfiguracja strony
st.set_page_config(page_title="Firmowy Typer MŚ 2026", page_icon="🏆", layout="centered")
st.title("🏆 Firmowy Typer - MŚ 2026")

# Połączenie z Google Sheets
conn = st.connection("gsheets", type="streamlit_gsheets.GSheetsConnection")

# --- API: POBIERANIE Z RETRIES ---
@st.cache_data(ttl=3600)
def pobierz_z_api_z_retries():
    # Klucz pobierany ze Streamlit Secrets
    url = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {
        "X-Auth-Token": st.secrets["api"]["football_key"],
        "User-Agent": "Mozilla/5.0"
    }
    for i in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 429:
                time.sleep(2)
                continue
            response.raise_for_status()
            return response.json().get('matches', [])
        except Exception as e:
            if i == 2: raise e
            time.sleep(1.5)

# --- POBIERANIE DANYCH ---
lista_meczow = []
try:
    mecze_api = pobierz_z_api_z_retries()
    for m in mecze_api:
        data_utc = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
        data_pl = data_utc + timedelta(hours=2)
        lista_meczow.append({
            "ID_Meczu": str(m['id']),
            "Gospodarz": m['homeTeam'].get('name', 'TBD'),
            "Gosc": m['awayTeam'].get('name', 'TBD'),
            "Data_Meczu_Obj": data_pl,
            "Data_Meczu": data_pl.strftime("%Y-%m-%d %H:%M:%S"),
            "Status": "Zaplanowany" if m['status'] in ['SCHEDULED', 'TIMED'] else ("W trakcie" if m['status'] in ['IN_PLAY', 'PAUSED'] else "Zakończony"),
            "Gole_Gospodarz": m['score']['fullTime'].get('home'),
            "Gole_Gosc": m['score']['fullTime'].get('away')
        })
    df_mecze = pd.DataFrame(lista_meczow)
except Exception:
    df_mecze = conn.read(worksheet="Mecze", ttl=10)
    df_mecze["ID_Meczu"] = df_mecze["ID_Meczu"].astype(str)
    df_mecze["Data_Meczu_Obj"] = pd.to_datetime(df_mecze["Data_Meczu"])

# Upewnienie się, że kolumny istnieją
if 'Gole_Gospodarz' not in df_mecze.columns: df_mecze['Gole_Gospodarz'] = None
if 'Gole_Gosc' not in df_mecze.columns: df_mecze['Gole_Gosc'] = None

# Pobieranie typów
try:
    df_typy = conn.read(worksheet="Typy", ttl=0)
    df_typy = df_typy.drop_duplicates(subset=["Pracownik", "ID_Meczu"], keep="last")
except:
    df_typy = pd.DataFrame(columns=["Pracownik", "ID_Meczu", "Typ_Gospodarz", "Typ_Gosc", "Data_Zapisu"])

# --- INTERFEJS ---
tab1, tab2 = st.tabs(["📅 Mecze", "🏆 Ranking"])

with tab1:
    pracownik = st.text_input("👤 Podaj imię / Nick").strip()
    
    # Filtr 3 dni
    teraz = datetime.now()
    koniec = teraz + timedelta(days=2, hours=23, minutes=59)
    df_widok = df_mecze[(df_mecze['Data_Meczu_Obj'] >= teraz) & (df_mecze['Data_Meczu_Obj'] <= koniec)]

    for _, row in df_widok.iterrows():
        with st.container(border=True):
            st.subheader(f"🏟️ {row['Gospodarz']} vs {row['Gosc']}")
            st.caption(f"🕒 {row['Data_Meczu']}")
            
            if row['Status'] == "Zaplanowany":
                moj_typ = df_typy[(df_typy["Pracownik"] == pracownik) & (df_typy["ID_Meczu"] == row['ID_Meczu'])]
                with st.form(f"f_{row['ID_Meczu']}"):
                    c1, c2 = st.columns(2)
                    tg = c1.number_input("Gospodarz", value=int(moj_typ.iloc[0]["Typ_Gospodarz"]) if not moj_typ.empty else 0)
                    tgo = c2.number_input("Gość", value=int(moj_typ.iloc[0]["Typ_Gosc"]) if not moj_typ.empty else 0)
                    if st.form_submit_button("Zapisz"):
                        nowy = pd.DataFrame([{"Pracownik": pracownik, "ID_Meczu": row['ID_Meczu'], "Typ_Gospodarz": tg, "Typ_Gosc": tgo, "Data_Zapisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                        conn.update(worksheet="Typy", data=pd.concat([conn.read(worksheet="Typy"), nowy]))
                        st.rerun()
            else:
                st.info(f"Wynik: {row['Gole_Gospodarz']} : {row['Gole_Gosc']}")

with tab2:
    if not df_typy.empty:
        punkty = {}
        for _, typ in df_typy.iterrows():
            mecz = df_mecze[df_mecze['ID_Meczu'] == typ['ID_Meczu']]
            if not mecz.empty and mecz.iloc[0]['Status'] == "Zakończony":
                osoba = typ['Pracownik']
                punkty.setdefault(osoba, 0)
                wg, wgo = mecz.iloc[0]['Gole_Gospodarz'], mecz.iloc[0]['Gole_Gosc']
                tg, tgo = int(typ['Typ_Gospodarz']), int(typ['Typ_Gosc'])
                if tg == wg and tgo == wgo: punkty[osoba] += 3
                elif (tg > tgo and wg > wgo) or (tg < tgo and wg < wgo) or (tg == tgo and wg == wgo): punkty[osoba] += 1
        
        ranking = pd.DataFrame(list(punkty.items()), columns=['Pracownik', 'Punkty']).sort_values('Punkty', ascending=False)
        st.dataframe(ranking, use_container_width=True)
