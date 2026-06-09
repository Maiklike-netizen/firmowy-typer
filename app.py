import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Diagnostyka API", layout="wide")
st.title("🔍 Diagnostyka Połączenia API")

@st.cache_data(ttl=60)
def pobierz_surowe_dane():
    url = "https://v3.football.api-sports.io/leagues"
    headers = {
        "x-rapidapi-key": st.secrets["api"]["football_key"],
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    querystring = {"season": "2026", "country": "World"}
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        return response.json().get('response', [])
    except Exception as e:
        return f"BŁĄD: {str(e)}"

dane = pobierz_surowe_dane()

if isinstance(dane, str):
    st.error(dane)
elif not dane:
    st.warning("API zwróciło pustą listę. Spróbuj zmienić parametry (np. usuń 'country').")
    st.write(dane)
else:
    st.success("Sukces! Dane odebrane.")
    # Wyświetlamy pierwszy element, żeby zobaczyć strukturę
    st.write("### Struktura jednego rekordu (pierwszy wynik):")
    st.json(dane[0])
    
    # Próbujemy przekształcić to na tabelę w bezpieczny sposób
    try:
        st.write("### Przetworzona tabela:")
        df = pd.json_normalize(dane)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Nie udało się stworzyć tabeli: {e}")
