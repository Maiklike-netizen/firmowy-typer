import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="Firmowy Typer MŚ 2026", page_icon="⚽", layout="centered")
st.title("⚽ Firmowy Typer - MŚ 2026")

# Inicjalizacja połączenia z Google Sheets
conn = st.connection("gsheets", type="streamlit_gsheets.GSheetsConnection")

# --- PRÓBA POBRANIA Z API ---
@st.cache_data(ttl=300)
def pobierz_z_api():
    url = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {
        "X-Auth-Token": "0ad260bc8caa424994a2a11512f3c21b",
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers, timeout=3)
    response.raise_for_status()
    return response.json().get('matches', [])

# --- GŁÓWNA LOGIKA POBIERANIA TERMINARZA ---
lista_meczow = []
try:
    mecze_api = pobierz_z_api()
    if mecze_api:
        for m in mecze_api:
            # 1. Parsujemy tekst z API na prawdziwy obiekt daty (w strefie UTC)
            data_utc = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
            # 2. Dodajemy 2 godziny, aby dostosować czas do polskiej strefy letniej (CEST)
            data_pl = data_utc + timedelta(hours=2)
            
            lista_meczow.append({
                "ID_Meczu": str(m['id']),
                "Gospodarz": m['homeTeam'].get('name', 'TBD'),
                "Gosc": m['awayTeam'].get('name', 'TBD'),
                # Zapisujemy już poprawny, polski czas do tabeli
                "Data_Meczu": data_pl.strftime("%Y-%m-%d %H:%M:%S"),
                "Status": "Zaplanowany" if m['status'] in ['SCHEDULED', 'TIMED'] else ("W trakcie" if m['status'] in ['IN_PLAY', 'PAUSED'] else "Zakończony"),
                "Gole_Gospodarz": m['score']['fullTime'].get('home', None),
                "Gole_Gosc": m['score']['fullTime'].get('away', None)
            })
        df_mecze = pd.DataFrame(lista_meczow)
        st.success("🔄 Dane meczów załadowane na żywo z API (Czas PL)!")
except Exception as e:
    st.info("⚠️ Serwer API jest przeciążony. Uruchomiono terminarz awaryjny (Google Sheets).")
    try:
        df_mecze = conn.read(worksheet="Mecze", ttl=10)
        df_mecze["ID_Meczu"] = df_mecze["ID_Meczu"].astype(str)
    except Exception:
        df_mecze = pd.DataFrame()


# --- ŁADOWANIE TYPÓW UŻYTKOWNIKÓW ---
try:
    df_typy = conn.read(worksheet="Typy", ttl=0)
    df_typy["ID_Meczu"] = df_typy["ID_Meczu"].astype(str)
except Exception:
    df_typy = pd.DataFrame(columns=["Pracownik", "ID_Meczu", "Typ_Gospodarz", "Typ_Gosc"])

# --- INTERFEJS UŻYTKOWNIKA ---
pracownik = st.text_input("👤 Podaj swoje imię / Nick", placeholder="np. Jan Kowalski").strip()
st.divider()

if not df_mecze.empty:
    teraz = datetime.now()
    
    for _, row in df_mecze.iterrows():
        id_m = str(row['ID_Meczu'])
        gosp = row['Gospodarz']
        gosc = row['Gosc']
        status = row['Status']
        
        # Parsowanie daty meczu do porównania deadline'u
        try:
            data_m = datetime.strptime(str(row['Data_Meczu']), "%Y-%m-%d %H:%M:%S")
        except:
            data_m = teraz # Bezpiecznik na wypadek błędnego wpisu w arkuszu
            
        czy_przed_meczem = teraz < data_m
        
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            col1.subheader(f"🏟️ {gosp} vs {gosc}")
            
            # Kolorowanie statusów
            if status == "Zaplanowany" and czy_przed_meczem:
                col2.markdown("🟢 **Zaplanowany**")
            elif status == "W trakcie" or not czy_przed_meczem:
                col2.markdown("🟡 **W trakcie / Blokada**")
            else:
                col2.markdown("🔴 **Zakończony**")
                
            st.caption(f"🕒 Czas rozpoczęcia: {data_m.strftime('%d.%m.%Y %H:%M')}")
            
            # Logika blokowania formularza po czasie
            if czy_przed_meczem and status == "Zaplanowany":
                # Sprawdzenie czy ten użytkownik już typował ten mecz
                juz_typowal = not df_typy[(df_typy["Pracownik"] == pracownik) & (df_typy["ID_Meczu"] == id_m)].empty
                
                if juz_typowal:
                    st.success("✅ Twój typ na ten mecz jest już zapisany bezpiecznie w bazie.")
                else:
                    with st.form(f"form_{id_m}"):
                        c1, c2 = st.columns(2)
                        tg = c1.number_input(f"Gole {gosp}", min_value=0, step=1, key=f"tg_{id_m}")
                        tgo = c2.number_input(f"Gole {gosc}", min_value=0, step=1, key=f"tgo_{id_m}")
                        
                        if st.form_submit_button("Zapisz typ"):
                            if not pracownik:
                                st.error("Musisz podać swoje imię na górze strony!")
                            else:
                                nowy_typ = pd.DataFrame([{"Pracownik": pracownik, "ID_Meczu": id_m, "Typ_Gospodarz": tg, "Typ_Gosc": tgo}])
                                df_typy = pd.concat([df_typy, nowy_typ], ignore_index=True)
                                conn.update(worksheet="Typy", data=df_typy)
                                st.success("Typ zapisany!")
                                st.rerun()
            else:
                g_g = row.get('Gole_Gospodarz', '-')
                g_go = row.get('Gole_Gosc', '-')
                st.warning(f"🔒 Typowanie zamknięte. Wynik meczu: {g_g} : {g_go}")

st.divider()
st.subheader("📊 Wszystkie dotychczasowe typy w bazie")
st.dataframe(df_typy, use_container_width=True)
