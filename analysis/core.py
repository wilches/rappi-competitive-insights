"""Pure computation + chart builders for the Rappi vs UberEats analysis.
Used by both the Jupyter notebook and the Streamlit dashboard.
"""
import glob
from pathlib import Path

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ─────────────────────────────────────────────
# Labels — used for presentation-ready output
# ─────────────────────────────────────────────
PLATFORM_LABELS = {"rappi": "Rappi", "ubereats": "Uber Eats"}
CITY_LABELS = {"cdmx": "CDMX", "gdl": "Guadalajara", "mty": "Monterrey"}
ZONE_LABELS = {"premium": "Premium", "middle": "Media", "peripheral": "Periférica"}
PRODUCT_LABELS = {"big_mac": "Big Mac", "mcnuggets_10": "McNuggets 10pz", "happy_meal": "Cajita Feliz"}
COLORS = {"Rappi": "#FF441F", "Uber Eats": "#06C167"}


# ─────────────────────────────────────────────
# 1. Load & prep
# ─────────────────────────────────────────────
def load_dataset(data_dir: str = "data/processed") -> pd.DataFrame:
    """Load and merge all observation CSVs, deduplicating keeping latest."""
    files = sorted(glob.glob(f"{data_dir}/observations_*.csv"))
    if not files:
        raise FileNotFoundError(f"No observation CSVs found in {data_dir}")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df = df.drop_duplicates(
        subset=["run_id", "platform", "address_id", "product_canonical"],
        keep="last",
    )
    return df


def prepare_priced(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to rows with valid prices, add display labels, compute eta_mid."""
    priced = df[df["product_price"].notna()].copy()
    priced["product_price_final"] = priced["product_price_final"].fillna(priced["product_price"])
    priced["platform_label"] = priced["platform"].map(PLATFORM_LABELS)
    priced["city_label"] = priced["city"].map(CITY_LABELS)
    priced["zone_label"] = priced["zone_type"].map(ZONE_LABELS)
    priced["product_label"] = priced["product_canonical"].map(PRODUCT_LABELS)
    priced["eta_mid"] = priced[["eta_min", "eta_max"]].mean(axis=1)
    return priced


# ─────────────────────────────────────────────
# 2. Metrics — every insight gets a compute fn
# ─────────────────────────────────────────────
def compute_price_positioning(priced: pd.DataFrame) -> dict:
    """Insight 1: Rappi vs UberEats price positioning."""
    pivot = priced.pivot_table(
        index=["address_id", "product_canonical"],
        columns="platform",
        values="product_price_final",
        aggfunc="mean",
    ).dropna()
    if pivot.empty or not {"rappi", "ubereats"}.issubset(pivot.columns):
        return {"error": "insufficient_data"}

    pivot["delta_pct"] = (pivot["rappi"] - pivot["ubereats"]) / pivot["ubereats"] * 100

    return {
        "pair_count": len(pivot),
        "overall_delta_pct": float(pivot["delta_pct"].mean()),
        "rappi_cheaper_pct": float((pivot["delta_pct"] < 0).mean() * 100),
        "rappi_equal_pct": float((pivot["delta_pct"].abs() < 1).mean() * 100),
        "by_product": pivot.reset_index().groupby("product_canonical")["delta_pct"].agg(
            ["mean", "median", "std", "count"]
        ).round(2).to_dict("index"),
        "pivot_df": pivot.reset_index(),
    }


def compute_geographic_variability(priced: pd.DataFrame) -> dict:
    """Insight 2: Where does Rappi win/lose by zone."""
    pv = priced.pivot_table(
        index=["address_id", "zone_type", "city", "product_canonical"],
        columns="platform",
        values="product_price_final",
    ).dropna().reset_index()
    if pv.empty or not {"rappi", "ubereats"}.issubset(pv.columns):
        return {"error": "insufficient_data"}

    pv["delta_pct"] = (pv["rappi"] - pv["ubereats"]) / pv["ubereats"] * 100
    by_zone = pv.groupby("zone_type")["delta_pct"].agg(["mean", "median", "count"]).round(2)
    addr_agg = pv.groupby(["address_id", "zone_type", "city"])["delta_pct"].mean().round(2).reset_index()
    return {
        "by_zone": by_zone.to_dict("index"),
        "worst_for_rappi": addr_agg.nlargest(5, "delta_pct").to_dict("records"),
        "best_for_rappi": addr_agg.nsmallest(5, "delta_pct").to_dict("records"),
        "addr_agg_df": addr_agg,
        "heatmap_df": pv.groupby(["city", "zone_type"])["delta_pct"].mean().reset_index(),
    }


def compute_eta(priced: pd.DataFrame) -> dict:
    """Insight 3: Speed advantage."""
    by_city = priced.groupby(["platform_label", "city_label"])["eta_mid"].agg(
        ["mean", "median", "std", "count"]
    ).round(1).reset_index()
    rappi_med = float(priced.loc[priced["platform"] == "rappi", "eta_mid"].median())
    uber_med = float(priced.loc[priced["platform"] == "ubereats", "eta_mid"].median())
    return {
        "rappi_median_min": rappi_med,
        "uber_median_min": uber_med,
        "rappi_advantage_min": uber_med - rappi_med,
        "rappi_advantage_pct": (uber_med - rappi_med) / uber_med * 100 if uber_med else 0,
        "by_city_df": by_city,
    }


def compute_promotions(priced: pd.DataFrame) -> dict:
    """Insight 4: Promotional intensity."""
    stats = priced.groupby(["platform_label", "city_label"])["promo_present"].agg(
        promo_rate="mean", n="count"
    ).reset_index()
    stats["promo_rate_pct"] = (stats["promo_rate"] * 100).round(1)
    rappi_promos = (
        priced[(priced["platform"] == "rappi") & priced["promo_description"].notna()]
        ["promo_description"].value_counts().head(5)
    )
    uber_promos = (
        priced[(priced["platform"] == "ubereats") & priced["promo_description"].notna()]
        ["promo_description"].value_counts().head(5)
    )
    return {
        "by_platform_city_df": stats,
        "top_rappi_promos": rappi_promos.to_dict(),
        "top_uber_promos": uber_promos.to_dict(),
    }


def compute_coverage(df: pd.DataFrame) -> dict:
    """Insight 5: Effective coverage by city × zone + Big Mac late-night finding."""
    cov = df.groupby(["address_id", "zone_type", "city", "platform"])["product_canonical"].apply(
        lambda s: s.notna().sum()
    ).unstack(fill_value=0)
    cov["rappi_ok"] = cov.get("rappi", 0) > 0
    cov["uber_ok"] = cov.get("ubereats", 0) > 0

    summary = cov.reset_index().groupby(["city", "zone_type"]).agg(
        total=("address_id", "count"),
        rappi_covers=("rappi_ok", "sum"),
        uber_covers=("uber_ok", "sum"),
    ).reset_index()
    summary["rappi_coverage_pct"] = (summary["rappi_covers"] / summary["total"] * 100).round(0)
    summary["uber_coverage_pct"] = (summary["uber_covers"] / summary["total"] * 100).round(0)

    big_mac_cov = df[df["product_canonical"] == "big_mac"].groupby(
        ["platform", "city"]
    ).size().unstack(fill_value=0)

    asym = cov[cov["rappi_ok"] != cov["uber_ok"]].reset_index()

    return {
        "summary_df": summary,
        "big_mac_df": big_mac_cov,
        "asymmetric_coverage": asym.to_dict("records"),
    }


# ─────────────────────────────────────────────
# 3. Chart builders (return plotly figures)
# ─────────────────────────────────────────────
def chart_price_comparison(priced: pd.DataFrame) -> go.Figure:
    avg = priced.groupby(["product_label", "platform_label"])["product_price_final"].agg(
        ["mean", "std"]
    ).reset_index()
    fig = px.bar(
        avg, x="product_label", y="mean", color="platform_label",
        error_y="std", barmode="group", color_discrete_map=COLORS,
        title="Precio promedio por producto — Rappi vs Uber Eats",
        labels={"mean": "MXN", "product_label": "", "platform_label": ""},
    )
    fig.update_layout(template="plotly_white", height=420, legend_title_text="")
    return fig


def chart_zone_heatmap(geo: dict) -> go.Figure:
    if geo.get("error"):
        return go.Figure()
    hm = geo["heatmap_df"].pivot(index="zone_type", columns="city", values="delta_pct")
    hm.index = [ZONE_LABELS.get(z, z) for z in hm.index]
    hm.columns = [CITY_LABELS.get(c, c) for c in hm.columns]
    fig = go.Figure(data=go.Heatmap(
        z=hm.values, x=hm.columns, y=hm.index,
        colorscale="RdYlGn_r", zmid=0,
        text=np.round(hm.values, 1),
        texttemplate="%{text}%",
        colorbar=dict(title="Δ%"),
    ))
    fig.update_layout(
        title="Δ% de precio: Rappi vs Uber Eats (verde = Rappi más barato)",
        template="plotly_white", height=380,
    )
    return fig


def chart_eta_boxplot(priced: pd.DataFrame) -> go.Figure:
    fig = px.box(
        priced, x="city_label", y="eta_mid", color="platform_label",
        color_discrete_map=COLORS,
        title="Distribución de ETA (minutos) por ciudad",
        labels={"eta_mid": "ETA (min)", "city_label": "", "platform_label": ""},
    )
    fig.update_layout(template="plotly_white", height=420, legend_title_text="")
    return fig


def chart_promo_rate(promos: dict) -> go.Figure:
    df = promos["by_platform_city_df"]
    fig = px.bar(
        df, x="city_label", y="promo_rate_pct", color="platform_label",
        barmode="group", color_discrete_map=COLORS,
        title="% de observaciones con promoción visible",
        labels={"promo_rate_pct": "% con promo", "city_label": "", "platform_label": ""},
    )
    fig.update_layout(template="plotly_white", height=400, legend_title_text="")
    return fig


def chart_coverage(cov: dict) -> go.Figure:
    df = cov["summary_df"].copy()
    df["city_label"] = df["city"].map(CITY_LABELS)
    df["zone_label"] = df["zone_type"].map(ZONE_LABELS)
    melt = df.melt(
        id_vars=["city_label", "zone_label"],
        value_vars=["rappi_coverage_pct", "uber_coverage_pct"],
        var_name="platform", value_name="coverage_pct",
    )
    melt["platform"] = melt["platform"].replace({
        "rappi_coverage_pct": "Rappi", "uber_coverage_pct": "Uber Eats"
    })
    fig = px.bar(
        melt, x="zone_label", y="coverage_pct", color="platform",
        barmode="group", facet_col="city_label", color_discrete_map=COLORS,
        title="Cobertura efectiva (% direcciones con al menos 1 producto capturado)",
        labels={"coverage_pct": "% cobertura", "zone_label": ""},
    )
    fig.update_layout(template="plotly_white", height=420, legend_title_text="")
    return fig


# ─────────────────────────────────────────────
# 4. One-shot API — compute everything
# ─────────────────────────────────────────────
def run_full_analysis(data_dir: str = "data/processed") -> dict:
    df = load_dataset(data_dir)
    priced = prepare_priced(df)
    return {
        "df": df, "priced": priced,
        "insight1": compute_price_positioning(priced),
        "insight2": compute_geographic_variability(priced),
        "insight3": compute_eta(priced),
        "insight4": compute_promotions(priced),
        "insight5": compute_coverage(df),
    }
