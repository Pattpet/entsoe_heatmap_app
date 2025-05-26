import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from entsoe import EntsoePandasClient
import plotly.graph_objects as go
import plotly.express as px

# --- Streamlit konfigurační stránka ---
st.set_page_config(
    page_title="Day-Ahead Electricity Price Heatmap",
    layout="wide", # Rozšíří graf přes celou šířku
    initial_sidebar_state="expanded" # Otevře sidebar automaticky
)

st.title("Day-Ahead Electricity Price Heatmap")
st.markdown("Vizualizace denních cen elektřiny napříč evropskými zeměmi.")

# --- API Token (z Streamlit secrets) ---
# Ujistěte se, že máte soubor .streamlit/secrets.toml
# s obsahem: entsoe_token = "VÁŠ_TOKEN"
try:
    token = st.secrets["entsoe_token"]
except KeyError:
    st.error("ENTSPE API token nebyl nalezen v `.streamlit/secrets.toml`. Prosím, vytvořte soubor a přidejte klíč 'entsoe_token'.")
    st.stop() # Zastaví běh aplikace, pokud token není k dispozici

client = EntsoePandasClient(api_key=token)

# --- Funkce pro stahování dat (s kešováním) ---
@st.cache_data(ttl=3600) # Kešuje data na 1 hodinu (3600 sekund)
def get_entsoe_data(selected_day_dt, selected_countries, api_token):
    """
    Stahuje data denních cen elektřiny z ENTSOE pro jeden vybraný den.
    Vrací DataFrame a seznam států, pro které se data nepodařilo načíst.
    """
    client_local = EntsoePandasClient(api_key=api_token)
    final_df_cached = pd.DataFrame()
    failed_countries_list = [] # Nový seznam pro sledování chybějících států

    start_ts = pd.Timestamp(selected_day_dt, tz='Europe/Brussels')
    end_ts = pd.Timestamp(selected_day_dt + timedelta(days=1), tz='Europe/Brussels')

    for country in selected_countries:
        try:
            price_series = client_local.query_day_ahead_prices(
                country_code=country,
                start=start_ts,
                end=end_ts
            )

            if price_series is None or price_series.empty:
                st.warning(f"Žádná data pro stát: **{country}** pro den {selected_day_dt.strftime('%Y-%m-%d')}.")
                failed_countries_list.append(country) # Přidáme stát do seznamu chyb
                continue

            final_df_cached[country] = price_series

        except Exception as e:
            st.error(f"Chyba při stahování dat pro stát: **{country}** – {e}")
            failed_countries_list.append(country) # Přidáme stát do seznamu chyb
            # Pro tuto ukázku pokračujeme, ale s chybovou zprávou
    return final_df_cached, failed_countries_list # Vracíme i seznam chyb

# --- Nastavení parametrů v postranním panelu (Sidebar) ---
with st.sidebar:
    st.header("Parametry dotazu")

    today = datetime.now().date()
    default_selected_day = today + timedelta(days=1)

    selected_day_input = st.date_input(
        "Vyberte den", 
        default_selected_day,
        max_value=default_selected_day # Zde se omezuje maximální výběr
    )
    
    all_countries = ["CZ", "PL", "DE_LU", "FR", "SK", "DK_1", "SE_4", "ES", "AT", "IT_NORD", "NO_3", "HU", "HR", "SI", "BE", "NL", "PT", "IE_SEM", "LT", "LV", "EE", "GR", "FI", "BG", "RO", "CH", "LU"]

    selected_countries = st.multiselect(
        "Vyberte země",
        options=all_countries,
        default=["CZ", "DE_LU", "FR", "SK", "PL", "AT"]
    )

    if not selected_countries:
        st.info("Prosím, vyberte alespoň jednu zemi pro zobrazení dat.")
        st.stop()

# --- Stahování a zobrazení dat ---
# Definice globálního fontu a velikosti
GLOBAL_FONT_FAMILY = "Arial"
GLOBAL_FONT_SIZE = 18
GLOBAL_FONT_COLOR = "black"

with st.spinner(f"Stahování dat z ENTSOE pro {selected_day_input.strftime('%Y-%m-%d')}..."):
    # Nyní get_entsoe_data vrací i seznam chyb
    final_df, failed_countries = get_entsoe_data(selected_day_input, selected_countries, token)

# --- Zobrazení chyb a tlačítka pro refresh ---
if failed_countries:
    st.error(
        f"Nepodařilo se načíst data pro: **{', '.join(failed_countries)}**. "
        "Zkuste prosím obnovit stránku."
    )
    # Tlačítko pro obnovení, použijeme ikonu šipky do kola
    if st.button("Obnovit data", key="refresh_button"):
        st.rerun()

if not final_df.empty:
    st.subheader(f"Ceny elektřiny Day-Ahead pro {selected_day_input.strftime('%Y-%m-%d')}")

    # --- Příprava dat pro heatmapu ---
    spreads = (final_df.max() - final_df.min()).round(1)
    new_labels = [f"{country}<br>{spread}" for country, spread in zip(final_df.columns, spreads)]
    text_labels = final_df.round(1).astype(str).values
    hour_labels = [f"{h:02d}:00" for h in range(24)]

    zmin = final_df.values.min()
    zmax = final_df.values.max()
    zmid = 0

    fig = go.Figure(
        data=go.Heatmap(
            z=final_df.values,
            x=final_df.columns,
            y=final_df.index.strftime('%H:%M'),
            colorscale=[
                [0.0, 'rgb(106,168,79)'],
                [abs(zmin) / (abs(zmin) + zmax) if (zmin < 0 and zmax > 0) else (0.0 if zmin >= 0 else 1.0), 'rgb(225,237,219)'],
                [1.0, 'rgb(204,0,0)']
            ],
            zmin=zmin,
            zmax=zmax,
            zmid=zmid,
            colorbar_title="price <br>[€/MWh]",
            colorbar=dict(
                title_font=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE, family=GLOBAL_FONT_FAMILY),
                tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 0.9, family=GLOBAL_FONT_FAMILY)
            ),
            text=text_labels,
            texttemplate="%{text}",
            textfont=dict(size=GLOBAL_FONT_SIZE * 0.9, family=GLOBAL_FONT_FAMILY),
            hoverinfo="z+x+y"
        )
    )

    fig.update_layout(
        title={
            'text': f"Day-Ahead Electricity Prices for {selected_day_input.strftime('%Y-%m-%d')}",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=GLOBAL_FONT_SIZE * 1.3, family=GLOBAL_FONT_FAMILY, color=GLOBAL_FONT_COLOR)
        },
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=800,
        xaxis=dict(
            tickmode='array',
            tickvals=final_df.columns,
            ticktext=new_labels,
            title="Country (bidding zone) / Spread [€/MWh]",
            title_font=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 1.1, family=GLOBAL_FONT_FAMILY),
            tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE, family=GLOBAL_FONT_FAMILY),
            linecolor=GLOBAL_FONT_COLOR,
            gridcolor="lightgray"
        ),
        yaxis=dict(
            autorange="reversed",
            tickmode='array',
            tickvals=final_df.index.strftime('%H:%M'),
            ticktext=hour_labels,
            ticklabelposition="outside right",
            tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE, family=GLOBAL_FONT_FAMILY),
            linecolor=GLOBAL_FONT_COLOR,
            gridcolor="lightgray"
        ),
        font=dict(family=GLOBAL_FONT_FAMILY, size=GLOBAL_FONT_SIZE, color=GLOBAL_FONT_COLOR),
        annotations=[dict(
            x=1,
            y=1.05,
            xref="paper",
            yref="paper",
            text="PattPet",
            showarrow=False,
            font=dict(size=GLOBAL_FONT_SIZE * 0.9, color=GLOBAL_FONT_COLOR, family=GLOBAL_FONT_FAMILY),
            align="right",
            borderpad=4
            )
        ]
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Data v tabulce")
    st.dataframe(final_df.round(2))

else:
    # Tato zpráva se zobrazí, pokud se nenačetla data pro ŽÁDNÝ vybraný stát.
    # Pokud se nenačetla data jen pro POUZE NĚKTERÉ státy, zobrazí se jen výše uvedený st.error.
    if not failed_countries: # Zabraňuje duplicitní zprávě, pokud už chyběly všechny státy
        st.warning("Žádná data nebyla nalezena pro vybraná kritéria. Zkuste jiný rozsah dat nebo jiné země.")
