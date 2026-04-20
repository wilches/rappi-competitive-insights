# analysis/competitive_analysis.py
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
import numpy as np
from pathlib import Path
import json

# Style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

COLORS = {
    'rappi': '#FF441F',
    'ubereats': '#06C167',
    'didifood': '#FF8C00'
}


class CompetitiveAnalyzer:

    def __init__(self, data_path=None):
        """Initialize with scraped data."""
        if data_path:
            self.df = pd.read_csv(data_path)
        else:
            # Find most recent data file
            raw_files = sorted(Path('data/raw').glob('all_platforms_*.csv'))
            if raw_files:
                self.df = pd.read_csv(raw_files[-1])
            else:
                raise FileNotFoundError("No scraped data found in data/raw/")

        self.output_dir = Path('reports/figures')
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Clean data
        self._clean_data()

    def _clean_data(self):
        """Basic data cleaning."""
        # Convert numeric columns
        numeric_cols = ['product_price', 'delivery_fee', 'service_fee',
                       'total_price', 'estimated_delivery_time_min',
                       'estimated_delivery_time_max']
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

        # Calculate average delivery time
        if 'estimated_delivery_time_min' in self.df.columns:
            self.df['avg_delivery_time'] = (
                self.df['estimated_delivery_time_min'] +
                self.df['estimated_delivery_time_max']
            ) / 2

        # Recalculate total if missing
        mask = self.df['total_price'].isna() & self.df['product_price'].notna()
        self.df.loc[mask, 'total_price'] = (
            self.df.loc[mask, 'product_price'].fillna(0) +
            self.df.loc[mask, 'delivery_fee'].fillna(0) +
            self.df.loc[mask, 'service_fee'].fillna(0)
        )

    def generate_full_report(self):
        """Generate all analyses and visualizations."""
        print("📊 Generating competitive analysis report...")

        insights = []

        # 1. Price Comparison
        insights.extend(self.analyze_prices())

        # 2. Delivery Fee Comparison
        insights.extend(self.analyze_delivery_fees())

        # 3. Delivery Time Comparison
        insights.extend(self.analyze_delivery_times())

        # 4. Geographic Analysis
        insights.extend(self.analyze_geographic_variation())

        # 5. Total Cost Analysis
        insights.extend(self.analyze_total_cost())

        # 6. Create visualizations
        self.plot_price_comparison()
        self.plot_delivery_fees_by_zone()
        self.plot_delivery_time_comparison()
        self.plot_total_cost_heatmap()
        self.plot_geographic_competitiveness()

        # 7. Generate summary
        self.generate_summary_report(insights)

        return insights

    def analyze_prices(self):
        """Analyze product prices across platforms."""
        insights = []

        price_data = self.df[self.df['product_price'].notna()]
        if price_data.empty:
            return insights

        # Average prices per platform per product
        avg_prices = price_data.groupby(['platform', 'product_name'])['product_price'].mean()

        print("\n📦 PRODUCT PRICE COMPARISON")
        print("=" * 50)

        pivot = price_data.pivot_table(
            values='product_price',
            index='product_name',
            columns='platform',
            aggfunc='mean'
        )
        print(pivot.round(2).to_string())

        # Find where Rappi is most/least competitive
        if 'rappi' in pivot.columns:
            for product in pivot.index:
                rappi_price = pivot.loc[product, 'rappi'] if 'rappi' in pivot.columns else None
                if pd.isna(rappi_price):
                    continue

                other_prices = pivot.loc[product].drop('rappi', errors='ignore').dropna()
                if other_prices.empty:
                    continue

                min_competitor = other_prices.idxmin()
                min_price = other_prices.min()

                if rappi_price > min_price:
                    diff_pct = ((rappi_price - min_price) / min_price) * 100
                    if diff_pct > 10:
                        insights.append({
                            'category': 'pricing',
                            'finding': f"Rappi's {product} is {diff_pct:.1f}% more expensive than {min_competitor} (${rappi_price:.0f} vs ${min_price:.0f})",
                            'impact': f"Price-sensitive customers may prefer {min_competitor} for this item",
                            'recommendation': f"Review pricing for {product} - consider matching or getting within 5% of {min_competitor}"
                        })
                elif rappi_price < min_price:
                    diff_pct = ((min_price - rappi_price) / rappi_price) * 100
                    insights.append({
                        'category': 'pricing',
                        'finding': f"Rappi's {product} is {diff_pct:.1f}% cheaper than {min_competitor}",
                        'impact': 'Competitive advantage on this product',
                        'recommendation': 'Leverage this in marketing for price-conscious segments'
                    })

        return insights

    def analyze_delivery_fees(self):
        """Analyze delivery fees across platforms."""
        insights = []

        fee_data = self.df[self.df['delivery_fee'].notna()]
        if fee_data.empty:
            return insights

        print("\n🚚 DELIVERY FEE COMPARISON")
        print("=" * 50)

        avg_fees = fee_data.groupby('platform')['delivery_fee'].agg(['mean', 'median', 'min', 'max'])
        print(avg_fees.round(2).to_string())

        # Compare by zone type
        zone_fees = fee_data.groupby(['platform', 'zone_type'])['delivery_fee'].mean().unstack(0)
        print("\nDelivery Fees by Zone Type:")
        print(zone_fees.round(2).to_string())

        # Check if Rappi has higher fees in peripheral zones
        if 'rappi' in zone_fees.columns and 'peripheral' in zone_fees.index:
            rappi_peripheral = zone_fees.loc['peripheral', 'rappi'] if not pd.isna(zone_fees.loc['peripheral'].get('rappi')) else None

            if rappi_peripheral is not None:
                for comp in zone_fees.columns:
                    if comp == 'rappi':
                        continue
                    comp_peripheral = zone_fees.loc['peripheral'].get(comp)
                    if comp_peripheral is not None and not pd.isna(comp_peripheral):
                        if rappi_peripheral > comp_peripheral * 1.2:
                            diff_pct = ((rappi_peripheral - comp_peripheral) / comp_peripheral) * 100
                            insights.append({
                                'category': 'delivery_fees',
                                'finding': f"Rappi delivery fees are {diff_pct:.0f}% higher than {comp} in peripheral zones (${rappi_peripheral:.0f} vs ${comp_peripheral:.0f})",
                                'impact': 'Losing competitiveness in expansion zones where fee sensitivity is highest',
                                'recommendation': f'Consider subsidizing delivery fees in peripheral zones to match {comp}'
                            })

        return insights

    def analyze_delivery_times(self):
        """Analyze estimated delivery times."""
        insights = []

        time_data = self.df[self.df['avg_delivery_time'].notna()] if 'avg_delivery_time' in self.df.columns else pd.DataFrame()
        if time_data.empty:
            return insights

        print("\n⏱️ DELIVERY TIME COMPARISON")
        print("=" * 50)

        avg_times = time_data.groupby('platform')['avg_delivery_time'].agg(['mean', 'median', 'min', 'max'])
        print(avg_times.round(1).to_string())

        # Compare by zone
        zone_times = time_data.groupby(['platform', 'zone_type'])['avg_delivery_time'].mean().unstack(0)
        print("\nDelivery Times by Zone Type:")
        print(zone_times.round(1).to_string())

        if 'rappi' in avg_times.index:
            rappi_avg = avg_times.loc['rappi', 'mean']
            for comp in avg_times.index:
                if comp == 'rappi':
                    continue
                comp_avg = avg_times.loc[comp, 'mean']
                diff = rappi_avg - comp_avg
                if diff > 5:  # More than 5 min slower
                    insights.append({
                        'category': 'delivery_time',
                        'finding': f"Rappi is on average {diff:.0f} minutes slower than {comp} ({rappi_avg:.0f} vs {comp_avg:.0f} min)",
                        'impact': 'Delivery speed directly impacts reorder rates and customer satisfaction',
                        'recommendation': 'Investigate driver allocation and dispatch algorithms in slower zones'
                    })
                elif diff < -5:
                    insights.append({
                        'category': 'delivery_time',
                        'finding': f"Rappi is {abs(diff):.0f} minutes faster than {comp}",
                        'impact': 'Speed advantage can be a key differentiator',
                        'recommendation': 'Highlight fast delivery in marketing campaigns'
                    })

        return insights

    def analyze_geographic_variation(self):
        """Analyze how competitiveness varies by geography."""
        insights = []

        geo_data = self.df[self.df['total_price'].notna()]
        if geo_data.empty:
            return insights

        print("\n🗺️ GEOGRAPHIC ANALYSIS")
        print("=" * 50)

        # Total cost by zone and platform
        geo_pivot = geo_data.groupby(['zone_name', 'platform'])['total_price'].mean().unstack(0)
        print("\nAverage Total Price by Zone:")
        print(geo_pivot.round(2).to_string())

        # Find zones where Rappi is least competitive
        if 'rappi' in geo_data['platform'].values:
            rappi_by_zone = geo_data[geo_data['platform'] == 'rappi'].groupby('zone_name')['total_price'].mean()
            competitors_by_zone = geo_data[geo_data['platform'] != 'rappi'].groupby('zone_name')['total_price'].mean()

            worst_zones = []
            for zone in rappi_by_zone.index:
                if zone in competitors_by_zone.index:
                    rappi_price = rappi_by_zone[zone]
                    comp_price = competitors_by_zone[zone]
                    diff_pct = ((rappi_price - comp_price) / comp_price) * 100
                    worst_zones.append((zone, diff_pct, rappi_price, comp_price))

            worst_zones.sort(key=lambda x: x[1], reverse=True)

            if worst_zones and worst_zones[0][1] > 5:
                top_worst = worst_zones[:3]
                zone_names = ', '.join([z[0] for z in top_worst])
                avg_diff = np.mean([z[1] for z in top_worst])
                insights.append({
                    'category': 'geographic',
                    'finding': f"Rappi is least competitive in: {zone_names} (avg {avg_diff:.0f}% more expensive)",
                    'impact': 'These zones represent potential customer churn risk',
                    'recommendation': f'Prioritize fee optimization in {zone_names} zones'
                })

        return insights

    def analyze_total_cost(self):
        """Analyze total cost to consumer (product + fees)."""
        insights = []

        cost_data = self.df[self.df['total_price'].notna()]
        if cost_data.empty:
            return insights

        print("\n💰 TOTAL COST ANALYSIS (Product + Fees)")
        print("=" * 50)

        total_by_platform = cost_data.groupby('platform')['total_price'].agg(['mean', 'median'])
        print(total_by_platform.round(2).to_string())

        # Fee as percentage of product price
        fee_pct = cost_data.copy()
        fee_pct['fee_ratio'] = (
            (fee_pct['delivery_fee'].fillna(0) + fee_pct['service_fee'].fillna(0)) /
            fee_pct['product_price']
        ) * 100

        fee_ratio_by_platform = fee_pct.groupby('platform')['fee_ratio'].mean()
        print("\nFees as % of Product Price:")
        print(fee_ratio_by_platform.round(1).to_string())

        if 'rappi' in fee_ratio_by_platform.index:
            rappi_ratio = fee_ratio_by_platform['rappi']
            for comp in fee_ratio_by_platform.index:
                if comp == 'rappi':
                    continue
                comp_ratio = fee_ratio_by_platform[comp]
                if rappi_ratio > comp_ratio + 5:
                    insights.append({
                        'category': 'total_cost',
                        'finding': f"Rappi's fee-to-price ratio ({rappi_ratio:.0f}%) is higher than {comp}'s ({comp_ratio:.0f}%)",
                        'impact': 'Higher fee load makes orders feel more expensive even if product prices are similar',
                        'recommendation': 'Consider restructuring fee display or absorbing part of service fee for high-frequency users'
                    })

        return insights

    # ========== VISUALIZATIONS ==========

    def plot_price_comparison(self):
        """Bar chart: product prices across platforms."""
        price_data = self.df[self.df['product_price'].notna()]
        if price_data.empty:
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        pivot = price_data.pivot_table(
            values='product_price',
            index='product_name',
            columns='platform',
            aggfunc='mean'
        )

        x = np.arange(len(pivot.index))
        width = 0.25

        for i, platform in enumerate(pivot.columns):
            color = COLORS.get(platform, f'C{i}')
            bars = ax.bar(x + i * width, pivot[platform].values, width,
                         label=platform.capitalize(), color=color, alpha=0.85)
            # Add value labels
            for bar, val in zip(bars, pivot[platform].values):
                if not np.isnan(val):
                    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                           f'${val:.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

        ax.set_xlabel('Product', fontsize=12)
        ax.set_ylabel('Price (MXN)', fontsize=12)
        ax.set_title('Product Price Comparison Across Platforms', fontsize=14, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels(pivot.index, rotation=15, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'price_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("✅ Saved: price_comparison.png")

    def plot_delivery_fees_by_zone(self):
        """Grouped bar chart: delivery fees by zone type."""
        fee_data = self.df[self.df['delivery_fee'].notna()]
        if fee_data.empty:
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        pivot = fee_data.pivot_table(
            values='delivery_fee',
            index='zone_type',
            columns='platform',
            aggfunc='mean'
        )

        pivot.plot(kind='bar', ax=ax, color=[COLORS.get(c, 'gray') for c in pivot.columns], alpha=0.85)

        ax.set_xlabel('Zone Type', fontsize=12)
        ax.set_ylabel('Delivery Fee (MXN)', fontsize=12)
        ax.set_title('Delivery Fees by Zone Type', fontsize=14, fontweight='bold')
        ax.legend(title='Platform')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha='right')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'delivery_fees_by_zone.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("✅ Saved: delivery_fees_by_zone.png")

    def plot_delivery_time_comparison(self):
        """Box plot: delivery times by platform."""
        if 'avg_delivery_time' not in self.df.columns:
            return

        time_data = self.df[self.df['avg_delivery_time'].notna()]
        if time_data.empty:
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        platforms = time_data['platform'].unique()
        data_to_plot = [time_data[time_data['platform'] == p]['avg_delivery_time'].values for p in platforms]
        colors_list = [COLORS.get(p, 'gray') for p in platforms]

        bp = ax.boxplot(data_to_plot, labels=[p.capitalize() for p in platforms],
                       patch_artist=True, widths=0.5)

        for patch, color in zip(bp['boxes'], colors_list):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        ax.set_ylabel('Estimated Delivery Time (min)', fontsize=12)
        ax.set_title('Delivery Time Distribution by Platform', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'delivery_times.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("✅ Saved: delivery_times.png")

    def plot_total_cost_heatmap(self):
        """Heatmap: total cost by zone and platform."""
        cost_data = self.df[self.df['total_price'].notna()]
        if cost_data.empty:
            return

        fig, ax = plt.subplots(figsize=(10, 8))

        pivot = cost_data.pivot_table(
            values='total_price',
            index='zone_name',
            columns='platform',
            aggfunc='mean'
        )

        sns.heatmap(pivot, annot=True, fmt='.0f', cmap='RdYlGn_r', ax=ax,
                   linewidths=0.5, cbar_kws={'label': 'Total Price (MXN)'})

        ax.set_title('Total Cost Heatmap: Zone × Platform', fontsize=14, fontweight='bold')
        ax.set_ylabel('Zone')
        ax.set_xlabel('Platform')

        plt.tight_layout()
        plt.savefig(self.output_dir / 'total_cost_heatmap.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("✅ Saved: total_cost_heatmap.png")

    def plot_geographic_competitiveness(self):
        """Scatter/bar chart showing Rappi's price premium/discount by zone."""
        cost_data = self.df[self.df['total_price'].notna()]
        if cost_data.empty or 'rappi' not in cost_data['platform'].values:
            return

        rappi_avg = cost_data[cost_data['platform'] == 'rappi'].groupby('zone_name')['total_price'].mean()
        comp_avg = cost_data[cost_data['platform'] != 'rappi'].groupby('zone_name')['total_price'].mean()

        common_zones = rappi_avg.index.intersection(comp_avg.index)
        if common_zones.empty:
            return

        diff_pct = ((rappi_avg[common_zones] - comp_avg[common_zones]) / comp_avg[common_zones]) * 100
        diff_pct = diff_pct.sort_values()

        fig, ax = plt.subplots(figsize=(12, 6))

        colors_bar = ['#06C167' if v < 0 else '#FF441F' for v in diff_pct.values]
        bars = ax.barh(range(len(diff_pct)), diff_pct.values, color=colors_bar, alpha=0.8)

        ax.set_yticks(range(len(diff_pct)))
        ax.set_yticklabels(diff_pct.index)
        ax.axvline(x=0, color='black', linewidth=0.8)
        ax.set_xlabel('Rappi Price Premium vs Competition (%)', fontsize=12)
        ax.set_title('Rappi Price Competitiveness by Zone', fontsize=14, fontweight='bold')

        # Add annotations
        for i, (val, bar) in enumerate(zip(diff_pct.values, bars)):
            label = f'+{val:.1f}%' if val > 0 else f'{val:.1f}%'
            ax.text(val + (1 if val >= 0 else -1), i, label,
                   va='center', ha='left' if val >= 0 else 'right',
                   fontsize=9, fontweight='bold')

        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#06C167', alpha=0.8, label='Rappi is cheaper'),
            Patch(facecolor='#FF441F', alpha=0.8, label='Rappi is more expensive')
        ]
        ax.legend(handles=legend_elements, loc='lower right')

        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        plt.savefig(self.output_dir / 'geographic_competitiveness.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("✅ Saved: geographic_competitiveness.png")

    def generate_summary_report(self, insights):
        """Generate a text/HTML summary report."""
        report_path = Path('reports/competitive_report.md')

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 🔍 Competitive Intelligence Report\n\n")
            f.write(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"**Data Points:** {len(self.df)}\n")
            f.write(f"**Platforms:** {', '.join(self.df['platform'].unique())}\n")
            f.write(f"**Zones Covered:** {self.df['zone_name'].nunique()}\n")
            f.write(f"**Products Tracked:** {self.df['product_name'].nunique()}\n\n")

            f.write("---\n\n")
            f.write("## 📊 Executive Summary\n\n")

            # Quick stats
            if 'rappi' in self.df['platform'].values:
                rappi_data = self.df[self.df['platform'] == 'rappi']
                comp_data = self.df[self.df['platform'] != 'rappi']

                rappi_avg_price = rappi_data['product_price'].mean()
                comp_avg_price = comp_data['product_price'].mean()

                if not pd.isna(rappi_avg_price) and not pd.isna(comp_avg_price):
                    diff = ((rappi_avg_price - comp_avg_price) / comp_avg_price) * 100
                    direction = "more expensive" if diff > 0 else "cheaper"
                    f.write(f"- **Price Positioning:** Rappi is **{abs(diff):.1f}% {direction}** than the competition on average\n")

                rappi_avg_fee = rappi_data['delivery_fee'].mean()
                comp_avg_fee = comp_data['delivery_fee'].mean()

                if not pd.isna(rappi_avg_fee) and not pd.isna(comp_avg_fee):
                    diff = ((rappi_avg_fee - comp_avg_fee) / comp_avg_fee) * 100
                    direction = "higher" if diff > 0 else "lower"
                    f.write(f"- **Delivery Fees:** Rappi fees are **{abs(diff):.1f}% {direction}** than competitors\n")

                if 'avg_delivery_time' in self.df.columns:
                    rappi_avg_time = rappi_data['avg_delivery_time'].mean()
                    comp_avg_time = comp_data['avg_delivery_time'].mean()
                    if not pd.isna(rappi_avg_time) and not pd.isna(comp_avg_time):
                        diff = rappi_avg_time - comp_avg_time
                        direction = "slower" if diff > 0 else "faster"
                        f.write(f"- **Delivery Speed:** Rappi is **{abs(diff):.0f} min {direction}** on average\n")

            f.write("\n---\n\n")

            # Top 5 Insights
            f.write("## 🎯 Top 5 Actionable Insights\n\n")

            top_insights = insights[:5] if len(insights) >= 5 else insights

            for i, insight in enumerate(top_insights, 1):
                f.write(f"### Insight {i}: {insight['category'].replace('_', ' ').title()}\n\n")
                f.write(f"**🔎 Finding:** {insight['finding']}\n\n")
                f.write(f"**💥 Impact:** {insight['impact']}\n\n")
                f.write(f"**✅ Recommendation:** {insight['recommendation']}\n\n")
                f.write("---\n\n")

            # Visualizations references
            f.write("## 📈 Supporting Visualizations\n\n")
            f.write("1. Product Price Comparison (`reports/figures/price_comparison.png`)\n")
            f.write("2. Delivery Fees by Zone (`reports/figures/delivery_fees_by_zone.png`)\n")
            f.write("3. Delivery Time Distribution (`reports/figures/delivery_times.png`)\n")
            f.write("4. Total Cost Heatmap (`reports/figures/total_cost_heatmap.png`)\n")
            f.write("5. Geographic Competitiveness (`reports/figures/geographic_competitiveness.png`)\n\n")

            # Methodology
            f.write("---\n\n")
            f.write("## 📝 Methodology\n\n")
            f.write("- **Data Collection:** Automated web scraping using Playwright\n")
            f.write("- **Platforms:** Rappi, Uber Eats, DiDi Food\n")
            f.write("- **Market:** Mexico City Metropolitan Area\n")
            f.write("- **Reference Products:** Standardized fast-food items (McDonald's)\n")
            f.write("- **Ethics:** Rate-limited requests, respectful scraping practices\n\n")

            # Limitations
            f.write("## ⚠️ Limitations\n\n")
            f.write("- Point-in-time snapshot (prices vary by hour/day)\n")
            f.write("- Surge pricing not fully captured\n")
            f.write("- Some addresses may not have coverage on all platforms\n")
            f.write("- Promotions/coupons may be user-specific and not captured\n")

        print(f"✅ Report saved to: {report_path}")
        return report_path


# ========== RUN ANALYSIS ==========

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate Competitive Analysis')
    parser.add_argument('--data', type=str, help='Path to CSV data file')
    args = parser.parse_args()

    analyzer = CompetitiveAnalyzer(data_path=args.data)
    insights = analyzer.generate_full_report()

    print(f"\n🎉 Analysis complete! {len(insights)} insights generated.")
