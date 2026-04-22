"""Rappi Competitive Intelligence Dashboard.

Run locally:   streamlit run dashboard/app.py
Deploy free:   push to GitHub → streamlit.io/cloud → connect repo → done.
"""
import sys
from pathlib import Path

# Ensure project root on sys.path so `analysis.core` imports cleanly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd

from analysis.core import (
    run_full_analysis,
    chart_price_comparison, chart_zone_heatmap, chart_eta_boxplot,
    chart_promo_rate, chart_coverage,
)

st.set_page_config(
    page_title="Rappi Competitive Intelligence",
    page_icon="🛵",
    layout="wide",
)

# ─── Cache the dataset ───
@st.cache_data
def _load():
    return run_full_analysis()


results = _load()
df, priced = results["df"], results["priced"]

# ─── Header ───
st.title("🛵 Rappi Competitive Intelligence")
st.caption("Análisis comparativo Rappi vs Uber Eats — McDonald's en CDMX, Guadalajara y Monterrey")
n_runs = priced["run_id"].nunique()
st.caption(
    f"Análisis comparativo Rappi vs Uber Eats — McDonald's en CDMX, Guadalajara y Monterrey  ·  "
    f"📊 **{len(priced)} observaciones** en **{n_runs} corridas** · "
    f"ventana temporal: madrugada + hora pico de lunch"
)
# ─── Top KPIs ───
i1 = results["insight1"]
i3 = results["insight3"]
i5 = results["insight5"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Observaciones con precio", f"{len(priced):,}")
col2.metric(
    "Δ% Rappi vs Uber Eats",
    f"{i1['overall_delta_pct']:+.1f}%" if i1.get("overall_delta_pct") is not None else "n/a",
    help="Positivo = Rappi más caro",
)
col3.metric("ETA Rappi (mediana)", f"{i3['rappi_median_min']:.0f} min")
col4.metric(
    "Ventaja ETA vs Uber",
    f"{i3['rappi_advantage_min']:+.0f} min",
    f"{i3['rappi_advantage_pct']:+.0f}%",
)

# ─── Tabs per insight ───
tabs = st.tabs([
    "📊 1 · Precios",
    "🗺️ 2 · Variabilidad geográfica",
    "⏱️ 3 · ETA",
    "🎁 4 · Promociones",
    "📍 5 · Cobertura",
    "🗃️ Dataset",
])

with tabs[0]:
    st.subheader("Posicionamiento de precios por producto")
    st.markdown(
        f"**Hallazgo:** Rappi vs Uber Eats tienen un delta promedio de "
        f"**{i1['overall_delta_pct']:+.1f}%**. Rappi es más barato en "
        f"**{i1['rappi_cheaper_pct']:.0f}%** de los pares comparables "
        f"y el precio es idéntico (±1%) en **{i1['rappi_equal_pct']:.0f}%**."
    )
    st.plotly_chart(chart_price_comparison(priced), use_container_width=True)
    st.caption("Δ por producto")
    st.dataframe(pd.DataFrame(i1["by_product"]).T)

with tabs[1]:
    st.subheader("Δ% Rappi vs Uber Eats por ciudad y zona")
    st.markdown(
    "**Patrón observado:** Rappi es más caro en zonas premium (≈ +2.7%) "
    "y más barato en zonas periféricas (≈ -2.5%) — un gradiente inverso al que "
    "se esperaría si el objetivo es capturar customers de alto valor. "
    "Verde = Rappi más barato; rojo = Rappi más caro."
)
    i2 = results["insight2"]
    if i2.get("error"):
        st.warning("Datos insuficientes para comparación geográfica")
    else:
        st.plotly_chart(chart_zone_heatmap(i2), use_container_width=True)
        c1, c2 = st.columns(2)
        c1.markdown("**Top direcciones donde Rappi es MÁS CARO**")
        c1.dataframe(pd.DataFrame(i2["worst_for_rappi"]))
        c2.markdown("**Top direcciones donde Rappi es MÁS BARATO**")
        c2.dataframe(pd.DataFrame(i2["best_for_rappi"]))

with tabs[2]:
    st.subheader("Distribución de tiempo de entrega estimado")
    st.markdown(
        f"Rappi mediana **{i3['rappi_median_min']:.0f} min** vs Uber Eats "
        f"**{i3['uber_median_min']:.0f} min** → ventaja Rappi: "
        f"**{i3['rappi_advantage_min']:+.0f} min** "
        f"({i3['rappi_advantage_pct']:+.0f}%)."
    )
    st.plotly_chart(chart_eta_boxplot(priced), use_container_width=True)
    st.dataframe(i3["by_city_df"])

with tabs[3]:
    st.subheader("Intensidad promocional")
    i4 = results["insight4"]

    # Headline
    rappi_rate = priced[priced["platform"]=="rappi"]["promo_present"].mean() * 100
    uber_rate = priced[priced["platform"]=="ubereats"]["promo_present"].mean() * 100
    col1, col2, col3 = st.columns(3)
    col1.metric("Rappi — observaciones con promo", f"{rappi_rate:.0f}%")
    col2.metric("Uber Eats — observaciones con promo", f"{uber_rate:.0f}%")
    ratio = rappi_rate / uber_rate if uber_rate > 0 else float("inf")
    col3.metric("Ratio Rappi : Uber", f"{ratio:.1f}×")

    st.plotly_chart(chart_promo_rate(i4), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Top descripciones de promo en Rappi**")
        if i4["top_rappi_promos"]:
            for promo, count in i4["top_rappi_promos"].items():
                st.markdown(f"- `{count}×` {promo}")
        else:
            st.caption("Ninguna promo visible en este run")
    with c2:
        st.markdown("**Top descripciones de promo en Uber Eats**")
        if i4["top_uber_promos"]:
            for promo, count in i4["top_uber_promos"].items():
                st.markdown(f"- `{count}×` {promo}")
        else:
            st.caption("Uber Eats no expone descripciones de promo en el flujo anónimo de la API")

with tabs[4]:
    st.subheader("Cobertura efectiva por ciudad × zona")
    st.markdown(
        "Ambas plataformas tienen cobertura completa (100%) en las 24 direcciones "
        "muestreadas. **El hallazgo clave está en la disponibilidad del Big Mac:** "
        "en Monterrey, Uber Eats capturó Big Mac sólo 2 veces en 16 intentos (12.5%) "
        "mientras que Rappi lo capturó 13 veces (81%). Esto confirma restricciones "
        "del menú 'McNoches' en Uber Eats MTY que no aplican en Rappi — un *moat* "
        "operacional en la categoría fast-food nocturna."
    )
    st.plotly_chart(chart_coverage(i5), use_container_width=True)
    st.markdown("**Observaciones de Big Mac por plataforma × ciudad**")
    st.dataframe(i5["big_mac_df"])
    if i5["asymmetric_coverage"]:
        st.markdown("**Direcciones con cobertura asimétrica**")
        st.dataframe(pd.DataFrame(i5["asymmetric_coverage"]))

with tabs[5]:
    st.subheader("Dataset completo")
    f1, f2, f3 = st.columns(3)
    plats = f1.multiselect("Plataforma", sorted(priced["platform"].unique()), default=list(priced["platform"].unique()))
    cities = f2.multiselect("Ciudad", sorted(priced["city"].unique()), default=list(priced["city"].unique()))
    zones = f3.multiselect("Zona", sorted(priced["zone_type"].unique()), default=list(priced["zone_type"].unique()))
    filtered = priced[
        priced["platform"].isin(plats)
        & priced["city"].isin(cities)
        & priced["zone_type"].isin(zones)
    ]
    st.caption(f"{len(filtered)} observaciones")
    st.dataframe(
        filtered[[
            "platform", "city", "zone_type", "address_id", "store_name",
            "product_canonical", "product_price_final", "eta_min", "eta_max",
            "promo_present", "promo_description",
        ]]
    )
    st.download_button(
        "⬇️ Descargar CSV filtrado",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="rappi_competitive_data.csv",
        mime="text/csv",
    )
