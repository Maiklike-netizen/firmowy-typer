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

# --- FUNKCJA API (Z RETRIES) ---
@st.cache_data(ttl=3600)
def pobierz_mecze_api():
    url = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {"X-Auth-Token": st.secrets["api"]["football_key"], "User-Agent": "Mozilla/5.0"}
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

# --- POBIERANIE I PRZYGOTOWANIE DANYCH ---
try:
    mecze_api = pobierz_mecze_api()
    lista = []
    for m in mecze_api:
        data_utc = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
        data_pl = data_utc + timedelta(hours=2)
        lista.append({
            "ID_Meczu": str(m['id']),
            "Gospodarz": m['homeTeam'].get('name', 'TBD'),
            "Gosc": m['awayTeam'].get('name', 'TBD'),
            "Data": data_pl,
            "Wynik_Gospodarz": m['score']['fullTime'].get('home'),
            "Wynik_Gosc": m['score']['fullTime'].get('away'),
            "Status": "Zakończony" if m['status'] == 'FINISHED' else "Zaplanowany"
        })
    df_mecze = pd.DataFrame(lista)
except:
    df_mecze = conn.read(worksheet="Mecze", ttl=10)
    df_mecze["ID_Meczu"] = df_mecze["ID_Meczu"].astype(str)
    df_mecze["Data"] = pd.to_datetime(df_mecze["Data"])

# Pobieranie typów
df_typy = conn.read(worksheet="Typy", ttl=0)
df_typy["ID_Meczu"] = df_typy["ID_Meczu"].astype(str)
df_typy = df_typy.drop_duplicates(subset=["Pracownik", "ID_Meczu"], keep="last")

# --- INTERFEJS ---
tab1, tab2 = st.tabs(["📅 Mecze", "🏆 Ranking"])

with tab1:
    pracownik = st.text_input("👤 Podaj swoje imię / Nick").strip()
    teraz = datetime.now()
    # Filtr: +/- 3 dni od dzisiaj
    df_widok = df_mecze[(df_mecze['Data'] >= teraz - timedelta(days=1)) & (df_mecze['Data'] <= teraz + timedelta(days=2))]

    for _, row in df_widok.iterrows():
        with st.container(border=True):
            st.subheader(f"🏟️ {row['Gospodarz']} vs {row['Gosc']}")
            st.caption(f"🕒 {row['Data'].strftime('%d.%m %H:%M')}")
            
            if row['Status'] == "Zaplanowany" and row['Data'] > teraz:
                moj_typ = df_typy[(df_typy["Pracownik"] == pracownik) & (df_typy["ID_Meczu"] == row['ID_Meczu'])]
                with st.form(f"f_{row['ID_Meczu']}"):
                    c1, c2 = st.columns(2)
                    tg = c1.number_input("Gospodarz", value=int(moj_typ.iloc[0]["Typ_Gospodarz"]) if not moj_typ.empty else 0)
                    tgo = c2.number_input("Gość", value=int(moj_typ.iloc[0]["Typ_Gosc"]) if not moj_typ.empty else 0)
                    if st.form_submit_button("Zapisz typ"):
                        if not pracownik: st.error("Podaj imię!")
                        else:
                            nowy = pd.DataFrame([{"Pracownik": pracownik, "ID_Meczu": row['ID_Meczu'], "Typ_Gospodarz": tg, "Typ_Gosc": tgo, "Data_Zapisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                            conn.update(worksheet="Typy", data=pd.concat([conn.read(worksheet="Typy"), nowy]))
                            st.rerun()
            else:
                st.info(f"Wynik końcowy: {row['Wynik_Gospodarz']} : {row['Wynik_Gosc']}")

with tab2:
    if not df_typy.empty:
        punkty = {}
        for _, typ in df_typy.iterrows():
            mecz = df_mecze[df_mecze['ID_Meczu'] == typ['ID_Meczu']]
            if not mecz.empty and mecz.iloc[0]['Status'] == "Zakończony":
                osoba = typ['Pracownik']
                wg, wgo = mecz.iloc[0]['Wynik_Gospodarz'], mecz.iloc[0]['Wynik_Gosc']
                tg, tgo = int(typ['Typ_Gospodarz']), int(typ['Typ_Gosc'])
                
                pkt = 0
                if tg == wg and tgo == wgo: pkt = 3
                elif (tg > tgo and wg > wgo) or (tg < tgo and wg < wgo) or (tg == tgo and wg == wgo): pkt = 1
                punkty[osoba] = punkty.get(osoba, 0) + pkt
        
        df_ranking = pd.DataFrame(list(punkty.items()), columns=['Pracownik', 'Suma_Punktow']).sort_values('Suma_Punktow', ascending=False)
        st.table(df_ranking)
