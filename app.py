import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# Konfiguracja strony
st.set_page_config(page_title="Firmowy Typer MŚ 2026", page_icon="🏆", layout="centered")
st.title("🏆 Firmowy Typer - MŚ 2026")

# Inicjalizacja połączenia z Google Sheets
conn = st.connection("gsheets", type="streamlit_gsheets.GSheetsConnection")

# --- FUNKCJA POBIERANIA Z API (Z AUTOMATYCZNYM PONAWIANIEM) ---
@st.cache_data(ttl=3600)
def pobierz_z_api_z_retries():
    url = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {
        "X-Auth-Token": st.secrets["api"]["football_key"], # Zmieniono na pobieranie z secrets dla bezpieczeństwa
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    max_retries = 3
    for i in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 429:
                time.sleep(2)
                continue
            response.raise_for_status()
            return response.json().get('matches', [])
        except (requests.exceptions.RequestException, Exception) as e:
            if i < max_retries - 1:
                time.sleep(1.5)
                continue
            else:
                raise e

# --- POBIERANIE TERMINARZA ---
lista_meczow = []
try:
    mecze_api = pobierz_z_api_z_retries()
    if mecze_api:
        for m in mecze_api:
            data_utc = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
            data_pl = data_utc + timedelta(hours=2) # Czas PL (CEST)
            
            lista_meczow.append({
                "ID_Meczu": str(m['id']),
                "Gospodarz": m['homeTeam'].get('name', 'TBD'),
                "Gosc": m['awayTeam'].get('name', 'TBD'),
                "Data_Meczu": data_pl.strftime("%Y-%m-%d %H:%M:%S"),
                "Status": "Zaplanowany" if m['status'] in ['SCHEDULED', 'TIMED'] else ("W trakcie" if m['status'] in ['IN_PLAY', 'PAUSED'] else "Zakończony"),
                "Gole_Gospodarz": m['score']['fullTime'].get('home', None),
                "Gole_Gosc": m['score']['fullTime'].get('away', None)
            })
        df_mecze = pd.DataFrame(lista_meczow)
except Exception:
    try:
        df_mecze = conn.read(worksheet="Mecze", ttl=10)
        df_mecze["ID_Meczu"] = df_mecze["ID_Meczu"].astype(str)
    except Exception:
        df_mecze = pd.DataFrame()

# --- POBIERANIE I DEDUPLIKACJA TYPÓW (Bierzemy tylko najnowszy) ---
try:
    df_typy = conn.read(worksheet="Typy", ttl=0)
    df_typy["ID_Meczu"] = df_typy["ID_Meczu"].astype(str)
    # Zostawiamy tylko najnowszy typ dla każdego pracownika i meczu
    if not df_typy.empty:
        df_typy = df_typy.drop_duplicates(subset=["Pracownik", "ID_Meczu"], keep="last")
except Exception:
    df_typy = pd.DataFrame(columns=["Pracownik", "ID_Meczu", "Typ_Gospodarz", "Typ_Gosc", "Data_Zapisu"])

# --- INTERFEJS UŻYTKOWNIKA (ZAKŁADKI) ---
tab1, tab2 = st.tabs(["📅 Mecze i Typowanie", "🏆 Ranking Firmowy"])

with tab1:
    st.write("Wpisz swoje imię, aby typować lub edytować swoje wyniki.")
    pracownik = st.text_input("👤 Podaj swoje imię / Nick", placeholder="np. Jan Kowalski").strip()
    st.divider()

    if not df_mecze.empty:
        teraz = datetime.now()
        
        for _, row in df_mecze.iterrows():
            id_m = str(row['ID_Meczu'])
            gosp = row['Gospodarz']
            gosc = row['Gosc']
            status = row['Status']
            
            try:
                data_m = datetime.strptime(str(row['Data_Meczu']), "%Y-%m-%d %H:%M:%S")
            except:
                data_m = teraz
                
            czy_przed_meczem = teraz < data_m
            
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                col1.subheader(f"🏟️ {gosp} vs {gosc}")
                
                if status == "Zaplanowany" and czy_przed_meczem:
                    col2.markdown("🟢 **Zaplanowany**")
                elif status == "W trakcie" or (not czy_przed_meczem and status != "Zakończony"):
                    col2.markdown("🟡 **W trakcie / Blokada**")
                else:
                    col2.markdown("🔴 **Zakończony**")
                    
                st.caption(f"🕒 Rozpoczęcie: {data_m.strftime('%d.%m.%Y %H:%M')}")
                
                if czy_przed_meczem and status == "Zaplanowany":
                    # Sprawdzamy czy już typował - pre-fill formularza
                    moj_typ = df_typy[(df_typy["Pracownik"] == pracownik) & (df_typy["ID_Meczu"] == id_m)] if pracownik else pd.DataFrame()
                    domyslny_tg = int(float(moj_typ.iloc[0]["Typ_Gospodarz"])) if not moj_typ.empty else 0
                    domyslny_tgo = int(float(moj_typ.iloc[0]["Typ_Gosc"])) if not moj_typ.empty else 0
                    przycisk_txt = "🔄 Zaktualizuj typ" if not moj_typ.empty else "✅ Zapisz typ"
                    
                    with st.form(f"form_{id_m}"):
                        c1, c2 = st.columns(2)
                        tg = c1.number_input(f"Gole {gosp}", min_value=0, step=1, value=domyslny_tg, key=f"tg_{id_m}")
                        tgo = c2.number_input(f"Gole {gosc}", min_value=0, step=1, value=domyslny_tgo, key=f"tgo_{id_m}")
                        
                        if st.form_submit_button(przycisk_txt):
                            if not pracownik:
                                st.error("Wpisz imię na samej górze!")
                            else:
                                nowy_typ = pd.DataFrame([{
                                    "Pracownik": pracownik, 
                                    "ID_Meczu": id_m, 
                                    "Typ_Gospodarz": tg, 
                                    "Typ_Gosc": tgo,
                                    "Data_Zapisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }])
                                # Odczytujemy świeżą bazę bez deduplikacji, dopisujemy i zapisujemy
                                fresh_df = conn.read(worksheet="Typy", ttl=0)
                                updated_df = pd.concat([fresh_df, nowy_typ], ignore_index=True)
                                conn.update(worksheet="Typy", data=updated_df)
                                st.success("Zapisano! Możesz go edytować do startu meczu.")
                                st.rerun()
                else:
                    g_g = row.get('Gole_Gospodarz', '-')
                    g_go = row.get('Gole_Gosc', '-')
                    st.info(f"🔒 Mecz zablokowany. Oficjalny wynik: **{g_g} : {g_go}**")

with tab2:
    st.subheader("🏆 Tabela Wyników")
    
    if not df_mecze.empty and not df_typy.empty:
        # Filtrujemy tylko zakończone mecze, które mają jakikolwiek wynik
        zakonczone = df_mecze[df_mecze['Status'] == "Zakończony"].dropna(subset=['Gole_Gospodarz', 'Gole_Gosc'])
        
        ranking_data = {}
        
        for _, typ in df_typy.iterrows():
            osoba = typ['Pracownik']
            id_m = typ['ID_Meczu']
            
            if osoba not in ranking_data:
                ranking_data[osoba] = {"Punkty": 0, "Idealne_trafienia": 0}
                
            # Sprawdzamy czy ten mecz się zakończył
            mecz_info = zakonczone[zakonczone['ID_Meczu'] == id_m]
            if not mecz_info.empty:
                try:
                    tg = int(float(typ['Typ_Gospodarz']))
                    tgo = int(float(typ['Typ_Gosc']))
                    wg = int(float(mecz_info.iloc[0]['Gole_Gospodarz']))
                    wgo = int(float(mecz_info.iloc[0]['Gole_Gosc']))
                    
                    # Obliczanie punktów
                    if tg == wg and tgo == wgo:
                        ranking_data[osoba]["Punkty"] += 3
                        ranking_data[osoba]["Idealne_trafienia"] += 1
                    elif (tg > tgo and wg > wgo) or (tg < tgo and wg < wgo) or (tg == tgo and wg == wgo):
                        ranking_data[osoba]["Punkty"] += 1
                except:
                    pass # Pomijamy błędy rzutowania na int (np. puste pola)
                    
        # Tworzenie Dataframe z rankingu
        if ranking_data:
            df_ranking = pd.DataFrame.from_dict(ranking_data, orient='index').reset_index()
            df_ranking.rename(columns={'index': 'Pracownik'}, inplace=True)
            df_ranking = df_ranking.sort_values(by=['Punkty', 'Idealne_trafienia'], ascending=[False, False]).reset_index(drop=True)
            df_ranking.index += 1 # Numeracja od 1
            
            st.dataframe(df_ranking, use_container_width=True)
        else:
            st.info("Żaden mecz z wytypowanych jeszcze się nie zakończył. Czekamy na pierwsze punkty!")
    else:
        st.info("Brak danych do wygenerowania rankingu. Czekamy na pierwsze typy i rozegrane mecze!")
