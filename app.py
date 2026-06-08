import streamlit as st
import pandas as pd

# Konfiguracja wyglądu strony
st.set_page_config(page_title="Firmowy Typer", page_icon="⚽", layout="centered")

st.title("⚽ Firmowy Typer - Mistrzostwa Świata")

# Utworzenie dwóch głównych zakładek
zakladka_typy, zakladka_ranking = st.tabs(["Wpisz swoje typy", "Ranking Firmowy"])

with zakladka_typy:
    st.header("Wytypuj wyniki najbliższych meczów")
    st.info("Wybierz swoje przewidywania. Masz czas do pierwszego gwizdka!")
    
    # Przykładowy formularz dla jednego meczu
    with st.form("formularz_mecz_1"):
        st.subheader("Polska vs Meksyk")
        kolumna1, kolumna2 = st.columns(2)
        
        with kolumna1:
            gospodarz = st.number_input("Polska", min_value=0, step=1)
        with kolumna2:
            gosc = st.number_input("Meksyk", min_value=0, step=1)
        
        zapisz = st.form_submit_button("Zapisz swój typ")
        
        if zapisz:
            st.success(f"Zapisano! Twój typ to: Polska {gospodarz} - {gosc} Meksyk")

with zakladka_ranking:
    st.header("Aktualny Ranking")
    st.write("Sprawdź, kto z firmy radzi sobie najlepiej:")
    
    # Przykładowa tabela (później podłączymy tu prawdziwe dane)
    dane_testowe = {
        "Pozycja": [1, 2, 3],
        "Pracownik": ["Janek", "Anna", "Tomek"],
        "Punkty": [12, 9, 4]
    }
    
    tabela = pd.DataFrame(dane_testowe)
    st.dataframe(tabela, hide_index=True, use_container_width=True)