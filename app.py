import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Firmowy Typer", page_icon="⚽", layout="centered")

st.title("⚽ Firmowy Typer")

# Nawiązanie połączenia z Arkuszem Google
conn = st.connection("gsheets", type=GSheetsConnection)

# Pobranie danych z zakładki Typy (ttl=0 wyłącza pamięć podręczną, aby mieć wyniki na żywo)
df_typy = conn.read(worksheet="Typy", ttl=0)

st.subheader("Dodaj swój typ")

# Formularz do wpisywania na telefonie
with st.form("formularz_typowania"):
    pracownik = st.text_input("Twoje imię / Nick")
    id_meczu = st.text_input("ID Meczu (np. wpisz 1)") 
    
    kol1, kol2 = st.columns(2)
    with kol1:
        gospodarz = st.number_input("Wynik Gospodarza", min_value=0, step=1)
    with kol2:
        gosc = st.number_input("Wynik Gościa", min_value=0, step=1)
        
    zapisz = st.form_submit_button("Zapisz typ")

# Logika, która uruchamia się po kliknięciu przycisku
if zapisz:
    if not pracownik or not id_meczu:
        st.warning("Uzupełnij swoje imię i ID meczu!")
    else:
        # Zbudowanie nowego wiersza z danymi pracownika
        nowy_typ = pd.DataFrame([{
            "Pracownik": pracownik,
            "ID_Meczu": id_meczu,
            "Typ_Gospodarz": gospodarz,
            "Typ_Gosc": gosc,
            "Punkty": 0
        }])
        
        # Dołączenie nowego typu do istniejącej tabeli w pamięci
        zaktualizowane_typy = pd.concat([df_typy, nowy_typ], ignore_index=True)
        
        # Wysłanie całości z powrotem do Google Sheets
        conn.update(worksheet="Typy", data=zaktualizowane_typy)
        st.success("Brawo! Twój typ został zapisany w bazie.")

st.divider()

# Wyświetlanie danych prosto z tabeli
st.subheader("Zapisane typy w Arkuszu Google:")
st.dataframe(conn.read(worksheet="Typy", ttl=0), use_container_width=True)
