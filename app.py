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
    # Usuwamy 'country', zostawiamy tylko 'season'
    querystring = {"season": "2026"}
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
    st.warning("Nadal pusto! Spróbujmy bez sezonu (może być błąd w dacie).")
    # Ostateczna próba: pobranie czegokolwiek
    st.write("Próbuję pobrać listę lig bez żadnych filtrów:")
    st.write(requests.get("https://v3.football.api-sports.io/leagues", 
             headers={"x-rapidapi-key": st.secrets["api"]["football_key"], 
                      "x-rapidapi-host": "v3.football.api-sports.io"}).json().get('response', [])[:5])
else:
    st.success(f"Sukces! Pobrano {len(dane)} lig.")
    df = pd.json_normalize(dane)
    st.dataframe(df, use_container_width=True)
