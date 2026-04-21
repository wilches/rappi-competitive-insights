"""Run the full analysis pipeline and print a text summary.
Can be converted to a Jupyter notebook via `# %%` cell markers.
"""
# %%
from pathlib import Path
import json

from analysis.core import (
    run_full_analysis,
    chart_price_comparison, chart_zone_heatmap, chart_eta_boxplot,
    chart_promo_rate, chart_coverage,
)

OUT_DIR = Path("analysis/output")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# %%
results = run_full_analysis()
df, priced = results["df"], results["priced"]
print(f"Dataset: {len(df)} total observations, {len(priced)} with prices")
print(f"Platforms: {priced['platform'].unique()}")
print(f"Cities: {priced['city'].unique()}")
print(f"Runs: {priced['run_id'].unique()}")

# %% Insight 1
i1 = results["insight1"]
print("\n=== INSIGHT 1: PRICE POSITIONING ===")
print(f"Comparable pairs: {i1['pair_count']}")
print(f"Rappi vs Uber overall delta: {i1['overall_delta_pct']:+.2f}%")
print(f"Rappi cheaper in: {i1['rappi_cheaper_pct']:.0f}% of pairs")
print(f"Identical (±1%) in: {i1['rappi_equal_pct']:.0f}% of pairs")
print(f"By product:")
for prod, stats in i1["by_product"].items():
    print(f"  {prod}: mean Δ={stats['mean']:+.2f}% (n={int(stats['count'])})")

fig1 = chart_price_comparison(priced)
fig1.write_html(OUT_DIR / "insight1_price.html")
fig1.show()

# %% Insight 2
i2 = results["insight2"]
print("\n=== INSIGHT 2: GEOGRAPHIC VARIABILITY ===")
for zone, stats in i2["by_zone"].items():
    print(f"  {zone}: mean Δ={stats['mean']:+.2f}% (n={int(stats['count'])})")
print("Worst for Rappi:", i2["worst_for_rappi"][:3])
print("Best  for Rappi:", i2["best_for_rappi"][:3])

fig2 = chart_zone_heatmap(i2)
fig2.write_html(OUT_DIR / "insight2_heatmap.html")
fig2.show()

# %% Insight 3
i3 = results["insight3"]
print("\n=== INSIGHT 3: ETA ===")
print(f"Rappi median ETA: {i3['rappi_median_min']:.0f} min")
print(f"Uber  median ETA: {i3['uber_median_min']:.0f} min")
print(f"Rappi advantage: {i3['rappi_advantage_min']:+.0f} min ({i3['rappi_advantage_pct']:+.0f}%)")

fig3 = chart_eta_boxplot(priced)
fig3.write_html(OUT_DIR / "insight3_eta.html")
fig3.show()

# %% Insight 4
i4 = results["insight4"]
print("\n=== INSIGHT 4: PROMOTIONS ===")
print(i4["by_platform_city_df"].to_string(index=False))
print("\nTop Rappi promo strings:")
for p, c in i4["top_rappi_promos"].items():
    print(f"  ({c}x) {p}")
print("Top Uber promo strings:", i4["top_uber_promos"] or "(none visible)")

fig4 = chart_promo_rate(i4)
fig4.write_html(OUT_DIR / "insight4_promos.html")
fig4.show()

# %% Insight 5
i5 = results["insight5"]
print("\n=== INSIGHT 5: COVERAGE ===")
print(i5["summary_df"].to_string(index=False))
print("\nBig Mac observation counts (platform × city):")
print(i5["big_mac_df"])

fig5 = chart_coverage(i5)
fig5.write_html(OUT_DIR / "insight5_coverage.html")
fig5.show()

# %% Export JSON summary
def _drop_df(d):
    return {k: v for k, v in d.items() if not hasattr(v, "to_dict")}

summary = {
    "insight1": _drop_df(results["insight1"]),
    "insight2": _drop_df(results["insight2"]),
    "insight3": _drop_df(results["insight3"]),
    "insight4": {k: v for k, v in results["insight4"].items() if k != "by_platform_city_df"},
    "insight5": {k: v for k, v in results["insight5"].items() if k != "summary_df"},
}
with open(OUT_DIR / "insights_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
print(f"\n✅ Summary → {OUT_DIR / 'insights_summary.json'}")
