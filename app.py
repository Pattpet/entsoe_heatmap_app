import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from entsoe import EntsoePandasClient
import plotly.graph_objects as go
import plotly.express as px # Added for completeness, though not directly used in the final plot

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
    """
    client_local = EntsoePandasClient(api_key=api_token) # Nová instance klienta pro cachovanou funkci
    final_df_cached = pd.DataFrame()

    # Převedeme datetime.date objekt na Pandas Timestamp s časovou zónou
    # Start bude začátek vybraného dne
    start_ts = pd.Timestamp(selected_day_dt, tz='Europe/Brussels')
    # End bude začátek NÁSLEDUJÍCÍHO dne, aby se načetl celý vybraný den (00:00 - 23:00)
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
                continue # Přeskočíme na další stát

            final_df_cached[country] = price_series

        except Exception as e:
            st.error(f"Chyba při stahování dat pro stát: **{country}** – {e}")
            # Můžeme se rozhodnout buď pokračovat nebo zastavit aplikaci
            # Pro tuto ukázku pokračujeme, ale s chybovou zprávou
    return final_df_cached

# --- Nastavení parametrů v postranním panelu (Sidebar) ---
with st.sidebar:
    st.header("Parametry dotazu")

    today = datetime.now().date()
    # Výchozí den: zítřek, aby byly k dispozici ceny Day-Ahead
    default_selected_day = today + timedelta(days=0)

    # Uživatel vybírá pouze jeden den
    selected_day_input = st.date_input("Vyberte den", default_selected_day)
    
    # Rozšířený seznam zemí pro výběr
    all_countries = ["CZ", "PL", "DE_LU", "FR", "SK", "DK_1", "SE_4", "ES", "AT", "IT_NORD", "NO_3", "HU", "HR", "SI", "BE", "NL", "PT", "IE_SEM", "LT", "LV", "EE", "GR", "FI", "BG", "RO", "CH", "LU"] # Přidáno pár dalších pro ukázku

    selected_countries = st.multiselect(
        "Vyberte země",
        options=all_countries,
        default=["CZ", "DE_LU", "FR", "SK", "PL", "AT"] # Výchozí výběr
    )

    if not selected_countries:
        st.info("Prosím, vyberte alespoň jednu zemi pro zobrazení dat.")
        st.stop()

# --- Stahování a zobrazení dat ---
# Použijeme st.spinner pro indikaci načítání dat
with st.spinner(f"Stahování dat z ENTSOE pro {selected_day_input.strftime('%Y-%m-%d')}..."):
    # Předáme jen jeden vybraný den funkci get_entsoe_data
    final_df = get_entsoe_data(selected_day_input, selected_countries, token)

if not final_df.empty:
    st.subheader(f"Ceny elektřiny Day-Ahead pro {selected_day_input.strftime('%Y-%m-%d')}")

    # --- Příprava dat pro heatmapu (stejně jako v originálním kódu) ---
    # 1) Spočítáme spread
    spreads = (final_df.max() - final_df.min()).round(1)

    # 2) Připravíme nové popisky pro osu X (názvy států + spread pod nimi)
    new_labels = [f"{country}<br>{spread}" for country, spread in zip(final_df.columns, spreads)]

    # 3) Připravíme textová data do heatmapy
    text_labels = final_df.round(1).astype(str).values

    # 4) Připravíme formátování osy Y
    hour_labels = [f"{h:02d}:00" for h in range(24)]

    # --- Nastavení globálního fontu a velikosti ---
    # Zde si nastavíš preferovaný font a velikost
    GLOBAL_FONT_FAMILY = "Arial" # Nebo "Times New Roman", "Consolas", "Roboto", atd.
    GLOBAL_FONT_SIZE = 18       # Základní velikost písma
    GLOBAL_FONT_COLOR = "black"

    # 5) Heatmapa
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
                title_font=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE, family=GLOBAL_FONT_FAMILY), # Barva, velikost a font titulku colorbaru
                tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 0.9, family=GLOBAL_FONT_FAMILY) # Barva, velikost a font číslic na colorbaru (mírně menší)
            ),
            text=text_labels,
            texttemplate="%{text}",
            textfont=dict(size=GLOBAL_FONT_SIZE * 0.9, family=GLOBAL_FONT_FAMILY), # DŮLEŽITÉ: Nastavení fontu pro text v buňkách heatmapy
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
            'font': dict(size=GLOBAL_FONT_SIZE * 1.3, family=GLOBAL_FONT_FAMILY, color=GLOBAL_FONT_COLOR) # Titulek grafu (větší než globální)
        },
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=800,
        xaxis=dict(
            tickmode='array',
            tickvals=final_df.columns,
            ticktext=new_labels,
            title="Země (zóna) / Spread [€/MWh]",
            title_font=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 1.1, family=GLOBAL_FONT_FAMILY), # Popisek osy X (mírně větší)
            tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE, family=GLOBAL_FONT_FAMILY),       # Popisky ticků na ose X
            linecolor=GLOBAL_FONT_COLOR,
            gridcolor="lightgray"
        ),
        yaxis=dict(
            autorange="reversed",
            tickmode='array',
            tickvals=final_df.index.strftime('%H:%M'),
            ticktext=hour_labels,
            ticklabelposition="outside right",
            
            title_standoff=5,
            title_font=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 1.1, family=GLOBAL_FONT_FAMILY), # Popisek osy Y (mírně větší)
            tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE, family=GLOBAL_FONT_FAMILY),       # Popisky ticků na ose Y
            linecolor=GLOBAL_FONT_COLOR,
            gridcolor="lightgray"
        ),
        # DŮLEŽITÉ: Toto je globální nastavení fontu pro celý layout grafu
        font=dict(family=GLOBAL_FONT_FAMILY, size=GLOBAL_FONT_SIZE, color=GLOBAL_FONT_COLOR),
        annotations=[dict(
            x=1,
            y=1.05,
            xref="paper",
            yref="paper",
            text="Pat Pet",
            showarrow=False,
            font=dict(size=GLOBAL_FONT_SIZE * 0.9, color=GLOBAL_FONT_COLOR, family=GLOBAL_FONT_FAMILY), # Copyright text (mírně menší)
            align="right",
            borderpad=4
            )
        ]
    )


# ... (zbytek kódu aplikace zůstává stejný) ...
    
    # --- Zobrazení grafu ve Streamlit ---
    st.plotly_chart(fig, use_container_width=True) # use_container_width zajistí, že se graf roztáhne
    
    # Volitelně můžete zobrazit i samotná data
    st.subheader("Data v tabulce")
    st.dataframe(final_df.round(2))

else:
    st.warning("Žádná data nebyla nalezena pro vybraná kritéria. Zkuste jiný rozsah dat nebo jiné země.")