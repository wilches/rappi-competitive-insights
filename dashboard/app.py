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
        "Cuando Rappi es competitivo por zona, podemos ver en qué tipos de barrios "
        "está perdiendo vs Uber Eats. Verde = Rappi más barato; rojo = Rappi más caro."
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
    st.subheader("Intensidad promocional (flujo anónimo)")
    i4 = results["insight4"]
    st.plotly_chart(chart_promo_rate(i4), use_container_width=True)
    c1, c2 = st.columns(2)
    c1.markdown("**Top promos Rappi**")
    c1.write(i4["top_rappi_promos"] or "Sin promociones visibles")
    c2.markdown("**Top promos Uber Eats**")
    c2.write(i4["top_uber_promos"] or "Sin promociones visibles en el flujo anónimo")

with tabs[4]:
    st.subheader("Cobertura efectiva por ciudad × zona")
    st.markdown(
        "Porcentaje de direcciones sampleadas donde cada plataforma logró retornar "
        "al menos un producto capturado. Las brechas de cobertura en zonas periféricas "
        "representan oportunidad (o vulnerabilidad) estratégica."
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
