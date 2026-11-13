#!/usr/bin/env python3
"""
BlazeDemo Performance Analysis Script
Εργασία Μαθήματος: Απόδοση Συστημάτων 2025

Αναλύει τα αποτελέσματα από τα JMeter tests και παράγει:
- Στατιστικές περιγραφές
- Null hypothesis testing (κανονική κατανομή)
- Confidence intervals
- Γραφήματα
- 2^k Factorial analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from pathlib import Path
import glob
import warnings
warnings.filterwarnings('ignore')

# Configuration
RESULTS_DIR = Path(__file__).resolve().parents[1] / 'data' / 'results'
OUTPUT_DIR = Path(__file__).resolve().parents[1] / 'generated'
OUTPUT_DIR.mkdir(exist_ok=True)

# Greek font support (optional - αν θέλεις ελληνικά στα graphs)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['figure.figsize'] = (12, 6)
sns.set_style("whitegrid")


def load_all_results():
    """Φορτώνει όλα τα CSV αρχεία αποτελεσμάτων"""
    results = []
    csv_files = glob.glob(str(RESULTS_DIR / 'results_*.csv'))

    print(f"Loading {len(csv_files)} result files...")

    for csv_file in csv_files:
        # Extract parameters from filename
        # Format: results_t{threads}_ia{interarrival}_mix{A}-{B}.csv
        filename = Path(csv_file).stem
        parts = filename.replace('results_', '').split('_')

        threads = int(parts[0].replace('t', ''))
        interarrival = int(parts[1].replace('ia', ''))
        mix = parts[2].replace('mix', '')
        scenario_a_pct, scenario_b_pct = map(int, mix.split('-'))

        # Load CSV
        df = pd.read_csv(csv_file)

        # Add metadata
        df['threads'] = threads
        df['interarrival'] = interarrival
        df['scenario_a_pct'] = scenario_a_pct
        df['scenario_b_pct'] = scenario_b_pct
        df['test_id'] = f"T{threads}_I{interarrival}_M{scenario_a_pct}-{scenario_b_pct}"

        results.append(df)
        print(f"  ✓ Loaded: {filename} ({len(df)} samples)")

    combined = pd.concat(results, ignore_index=True)
    print(f"\nTotal samples loaded: {len(combined)}")
    return combined


def descriptive_statistics(df):
    """Υπολογίζει και εμφανίζει περιγραφικές στατιστικές"""
    print("\n" + "="*80)
    print("DESCRIPTIVE STATISTICS")
    print("="*80)

    # Group by test configuration
    grouped = df.groupby(['threads', 'interarrival', 'scenario_a_pct'])['elapsed'].agg([
        ('count', 'count'),
        ('mean', 'mean'),
        ('median', 'median'),
        ('std', 'std'),
        ('min', 'min'),
        ('max', 'max'),
        ('p95', lambda x: np.percentile(x, 95)),
        ('p99', lambda x: np.percentile(x, 99))
    ]).round(2)

    print(grouped)

    # Save to CSV
    output_file = OUTPUT_DIR / 'descriptive_statistics.csv'
    grouped.to_csv(output_file)
    print(f"\n✓ Saved to: {output_file}")

    return grouped


def test_normality(df, test_config=None):
    """
    Null Hypothesis Testing για κανονική κατανομή
    Χρησιμοποιεί Shapiro-Wilk test και Kolmogorov-Smirnov test
    """
    print("\n" + "="*80)
    print("NULL HYPOTHESIS TESTING - NORMALITY")
    print("="*80)

    if test_config is None:
        # Use first configuration as example (0-100, 10 users, 0.5s as requested)
        test_config = {
            'threads': 10,
            'interarrival': 500,
            'scenario_a_pct': 0,
            'scenario_b_pct': 100
        }

    # Filter data
    mask = (
        (df['threads'] == test_config['threads']) &
        (df['interarrival'] == test_config['interarrival']) &
        (df['scenario_a_pct'] == test_config['scenario_a_pct'])
    )
    data = df[mask]['elapsed'].values

    print(f"\nTest Configuration: {test_config}")
    print(f"Sample size: {len(data)}")
    print(f"Mean: {np.mean(data):.2f} ms")
    print(f"Std Dev: {np.std(data):.2f} ms")

    # Shapiro-Wilk Test
    if len(data) > 3:
        shapiro_stat, shapiro_p = stats.shapiro(data[:5000])  # Max 5000 samples
        print(f"\nShapiro-Wilk Test:")
        print(f"  Statistic: {shapiro_stat:.6f}")
        print(f"  p-value: {shapiro_p:.6f}")

        if shapiro_p > 0.05:
            print(f"  ✓ Fail to reject H0: Data appears normally distributed (p > 0.05)")
        else:
            print(f"  ✗ Reject H0: Data does NOT appear normally distributed (p <= 0.05)")

    # Kolmogorov-Smirnov Test
    mean, std = np.mean(data), np.std(data)
    ks_stat, ks_p = stats.kstest(data, lambda x: stats.norm.cdf(x, mean, std))
    print(f"\nKolmogorov-Smirnov Test (vs normal with same mean/std):")
    print(f"  Statistic: {ks_stat:.6f}")
    print(f"  p-value: {ks_p:.6f}")

    if ks_p > 0.05:
        print(f"  ✓ Fail to reject H0: Data appears normally distributed (p > 0.05)")
    else:
        print(f"  ✗ Reject H0: Data does NOT appear normally distributed (p <= 0.05)")

    # Q-Q Plot
    plt.figure(figsize=(10, 6))
    stats.probplot(data, dist="norm", plot=plt)
    plt.title(f"Q-Q Plot - {test_config}")
    plt.grid(True, alpha=0.3)
    output_file = OUTPUT_DIR / 'qq_plot_normality.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Q-Q Plot saved to: {output_file}")
    plt.close()

    # Distribution plot
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.hist(data, bins=50, density=True, alpha=0.7, edgecolor='black')
    xmin, xmax = plt.xlim()
    x = np.linspace(xmin, xmax, 100)
    p = stats.norm.pdf(x, mean, std)
    plt.plot(x, p, 'r-', linewidth=2, label='Normal Distribution')
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Density')
    plt.title('Response Time Distribution vs Normal')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.hist(data, bins=50, cumulative=True, density=True, alpha=0.7, edgecolor='black')
    plt.plot(x, stats.norm.cdf(x, mean, std), 'r-', linewidth=2, label='Normal CDF')
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Cumulative Probability')
    plt.title('Cumulative Distribution')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = OUTPUT_DIR / 'distribution_normality.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Distribution plots saved to: {output_file}")
    plt.close()

    return data, mean, std


def confidence_interval(data, confidence=0.95):
    """Υπολογίζει confidence interval και required sample size"""
    print("\n" + "="*80)
    print(f"CONFIDENCE INTERVAL ({confidence*100}%)")
    print("="*80)

    n = len(data)
    mean = np.mean(data)
    std = np.std(data, ddof=1)  # Sample std
    se = std / np.sqrt(n)

    # t-distribution για confidence interval
    alpha = 1 - confidence
    t_critical = stats.t.ppf(1 - alpha/2, df=n-1)
    margin_error = t_critical * se

    ci_lower = mean - margin_error
    ci_upper = mean + margin_error

    print(f"\nSample Statistics:")
    print(f"  n = {n}")
    print(f"  Mean = {mean:.2f} ms")
    print(f"  Std Dev = {std:.2f} ms")
    print(f"  Std Error = {se:.2f} ms")

    print(f"\n{confidence*100}% Confidence Interval:")
    print(f"  [{ci_lower:.2f}, {ci_upper:.2f}] ms")
    print(f"  Margin of Error: ±{margin_error:.2f} ms ({margin_error/mean*100:.2f}% of mean)")

    # Required sample size for 5% margin of error
    desired_error_pct = 0.05
    desired_error = desired_error_pct * mean
    z_score = stats.norm.ppf(1 - alpha/2)  # For large samples, use z instead of t
    required_n = ((z_score * std) / desired_error) ** 2

    print(f"\nRequired Sample Size:")
    print(f"  For ±{desired_error_pct*100}% margin of error: {int(np.ceil(required_n))} samples")
    print(f"  Current samples: {n}")

    if n >= required_n:
        print(f"  ✓ Sufficient samples collected")
    else:
        print(f"  ⚠ Need {int(np.ceil(required_n - n))} more samples")

    return ci_lower, ci_upper, required_n


def plot_response_times(df):
    """Δημιουργεί γραφήματα response times"""
    print("\n" + "="*80)
    print("GENERATING RESPONSE TIME PLOTS")
    print("="*80)

    # 1. Response time vs Threads (for each inter-arrival)
    plt.figure(figsize=(15, 10))

    for idx, interarrival in enumerate([500, 1000], 1):
        for jdx, (scenario_a, scenario_b) in enumerate([(100, 0), (50, 50), (0, 100)], 1):
            subplot_idx = (idx - 1) * 3 + jdx
            plt.subplot(2, 3, subplot_idx)

            mask = (
                (df['interarrival'] == interarrival) &
                (df['scenario_a_pct'] == scenario_a)
            )
            subset = df[mask]

            # Group by threads and calculate mean
            grouped = subset.groupby('threads')['elapsed'].agg(['mean', 'std', 'median'])

            plt.errorbar(grouped.index, grouped['mean'], yerr=grouped['std'],
                        marker='o', capsize=5, capthick=2, label='Mean ± Std')
            plt.plot(grouped.index, grouped['median'], marker='s',
                    linestyle='--', label='Median')

            plt.xlabel('Number of Threads')
            plt.ylabel('Response Time (ms)')
            plt.title(f'Inter-arrival: {interarrival}ms, Mix: {scenario_a}-{scenario_b}%')
            plt.grid(True, alpha=0.3)
            plt.legend()

    plt.tight_layout()
    output_file = OUTPUT_DIR / 'response_time_vs_threads.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()

    # 2. Box plots for each configuration
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    for idx, threads in enumerate([10, 50, 100, 200]):
        mask = df['threads'] == threads
        subset = df[mask]

        # Create labels for each combination
        subset['config'] = (
            'IA' + subset['interarrival'].astype(str) +
            '_M' + subset['scenario_a_pct'].astype(str)
        )

        subset.boxplot(column='elapsed', by='config', ax=axes[idx])
        axes[idx].set_title(f'{threads} Threads')
        axes[idx].set_xlabel('Configuration (InterArrival_Mix)')
        axes[idx].set_ylabel('Response Time (ms)')
        axes[idx].grid(True, alpha=0.3)

    plt.suptitle('Response Time Distributions by Configuration', fontsize=16)
    plt.tight_layout()
    output_file = OUTPUT_DIR / 'boxplots_by_threads.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def factorial_2k_analysis(df):
    """2^k Factorial Design Analysis"""
    print("\n" + "="*80)
    print("2^k FACTORIAL DESIGN ANALYSIS")
    print("="*80)

    # Παράγοντες (k=3):
    # Factor A: Threads (Low=10, High=200)
    # Factor B: Inter-arrival (Low=500, High=1000)
    # Factor C: Load Mix (Low=100%-0%, High=0%-100%)

    print("\nFactors:")
    print("  A: Number of Threads (Low=10, High=200)")
    print("  B: Inter-arrival Time (Low=500ms, High=1000ms)")
    print("  C: Load Mix (Low=100%-0%, High=0%-100%)")

    # Design matrix
    design = [
        # Run | A | B | C |
        (1,  -1, -1, -1),  # 10, 500, 100-0
        (2,  +1, -1, -1),  # 200, 500, 100-0
        (3,  -1, +1, -1),  # 10, 1000, 100-0
        (4,  +1, +1, -1),  # 200, 1000, 100-0
        (5,  -1, -1, +1),  # 10, 500, 0-100
        (6,  +1, -1, +1),  # 200, 500, 0-100
        (7,  -1, +1, +1),  # 10, 1000, 0-100
        (8,  +1, +1, +1),  # 200, 1000, 0-100
    ]

    # Map coded values to actual values
    factor_map = {
        'A': {-1: 10, +1: 200},
        'B': {-1: 500, +1: 1000},
        'C': {-1: 100, +1: 0}  # scenario_a_pct
    }

    # Extract average response times for each run
    responses = []

    print("\nDesign Matrix and Responses:")
    print("Run | A  | B  | C  | Threads | IA   | Mix    | Mean RT (ms)")
    print("-" * 70)

    for run, a, b, c in design:
        threads = factor_map['A'][a]
        interarrival = factor_map['B'][b]
        scenario_a = factor_map['C'][c]

        mask = (
            (df['threads'] == threads) &
            (df['interarrival'] == interarrival) &
            (df['scenario_a_pct'] == scenario_a)
        )

        mean_rt = df[mask]['elapsed'].mean()
        responses.append(mean_rt)

        print(f"{run:3d} | {a:+2d} | {b:+2d} | {c:+2d} | {threads:7d} | {interarrival:4d} | {scenario_a:3d}-{100-scenario_a:3d} | {mean_rt:10.2f}")

    Y = np.array(responses)

    # Calculate effects
    # Main effects
    effect_A = (Y[1] + Y[3] + Y[5] + Y[7] - Y[0] - Y[2] - Y[4] - Y[6]) / 4
    effect_B = (Y[2] + Y[3] + Y[6] + Y[7] - Y[0] - Y[1] - Y[4] - Y[5]) / 4
    effect_C = (Y[4] + Y[5] + Y[6] + Y[7] - Y[0] - Y[1] - Y[2] - Y[3]) / 4

    # Interaction effects
    effect_AB = (Y[0] - Y[1] - Y[2] + Y[3] - Y[4] + Y[5] + Y[6] - Y[7]) / 4
    effect_AC = (Y[0] - Y[1] + Y[2] - Y[3] - Y[4] + Y[5] - Y[6] + Y[7]) / 4
    effect_BC = (Y[0] + Y[1] - Y[2] - Y[3] - Y[4] - Y[5] + Y[6] + Y[7]) / 4
    effect_ABC = (-Y[0] + Y[1] + Y[2] - Y[3] + Y[4] - Y[5] - Y[6] + Y[7]) / 4

    print("\n" + "="*70)
    print("EFFECTS SUMMARY")
    print("="*70)
    print(f"\nMain Effects:")
    print(f"  A (Threads):        {effect_A:+10.2f} ms")
    print(f"  B (Inter-arrival):  {effect_B:+10.2f} ms")
    print(f"  C (Load Mix):       {effect_C:+10.2f} ms")

    print(f"\nTwo-Factor Interactions:")
    print(f"  AB:                 {effect_AB:+10.2f} ms")
    print(f"  AC:                 {effect_AC:+10.2f} ms")
    print(f"  BC:                 {effect_BC:+10.2f} ms")

    print(f"\nThree-Factor Interaction:")
    print(f"  ABC:                {effect_ABC:+10.2f} ms")

    # Plot effects
    effects_dict = {
        'A\n(Threads)': effect_A,
        'B\n(Inter-arr)': effect_B,
        'C\n(Load Mix)': effect_C,
        'AB': effect_AB,
        'AC': effect_AC,
        'BC': effect_BC,
        'ABC': effect_ABC
    }

    plt.figure(figsize=(12, 6))
    colors = ['red' if abs(v) == max(abs(e) for e in effects_dict.values()) else 'steelblue'
              for v in effects_dict.values()]
    bars = plt.bar(effects_dict.keys(), effects_dict.values(), color=colors, edgecolor='black')
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    plt.xlabel('Factor / Interaction', fontsize=12)
    plt.ylabel('Effect on Response Time (ms)', fontsize=12)
    plt.title('2^k Factorial Analysis - Main Effects and Interactions', fontsize=14)
    plt.grid(True, axis='y', alpha=0.3)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:+.1f}',
                ha='center', va='bottom' if height > 0 else 'top',
                fontsize=10, fontweight='bold')

    plt.tight_layout()
    output_file = OUTPUT_DIR / 'factorial_2k_effects.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Effects plot saved to: {output_file}")
    plt.close()

    # Save to CSV
    effects_df = pd.DataFrame({
        'Factor': list(effects_dict.keys()),
        'Effect (ms)': list(effects_dict.values())
    })
    output_file = OUTPUT_DIR / 'factorial_2k_effects.csv'
    effects_df.to_csv(output_file, index=False)
    print(f"✓ Effects data saved to: {output_file}")


def generate_summary_report(df):
    """Δημιουργεί συνοπτική αναφορά"""
    print("\n" + "="*80)
    print("GENERATING SUMMARY REPORT")
    print("="*80)

    report_lines = []
    report_lines.append("="*80)
    report_lines.append("BLAZEDEMO PERFORMANCE TESTING - SUMMARY REPORT")
    report_lines.append("Εργασία Μαθήματος: Απόδοση Συστημάτων 2025")
    report_lines.append("="*80)
    report_lines.append("")

    # Overall statistics
    report_lines.append("OVERALL STATISTICS")
    report_lines.append("-" * 80)
    report_lines.append(f"Total experiments: {df['test_id'].nunique()}")
    report_lines.append(f"Total samples: {len(df)}")
    report_lines.append(f"Overall mean response time: {df['elapsed'].mean():.2f} ms")
    report_lines.append(f"Overall median response time: {df['elapsed'].median():.2f} ms")
    report_lines.append(f"Overall std dev: {df['elapsed'].std():.2f} ms")
    report_lines.append(f"Min response time: {df['elapsed'].min():.2f} ms")
    report_lines.append(f"Max response time: {df['elapsed'].max():.2f} ms")
    report_lines.append(f"95th percentile: {df['elapsed'].quantile(0.95):.2f} ms")
    report_lines.append(f"99th percentile: {df['elapsed'].quantile(0.99):.2f} ms")
    report_lines.append("")

    # Best and worst configurations
    grouped = df.groupby('test_id')['elapsed'].mean().sort_values()
    report_lines.append("BEST PERFORMING CONFIGURATIONS (lowest avg response time)")
    report_lines.append("-" * 80)
    for config, rt in grouped.head(3).items():
        report_lines.append(f"  {config}: {rt:.2f} ms")
    report_lines.append("")

    report_lines.append("WORST PERFORMING CONFIGURATIONS (highest avg response time)")
    report_lines.append("-" * 80)
    for config, rt in grouped.tail(3).items():
        report_lines.append(f"  {config}: {rt:.2f} ms")
    report_lines.append("")

    # Save report
    report_text = "\n".join(report_lines)
    output_file = OUTPUT_DIR / 'summary_report.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(report_text)
    print(f"\n✓ Summary report saved to: {output_file}")


def main():
    """Main execution"""
    print("="*80)
    print("BLAZEDEMO PERFORMANCE ANALYSIS")
    print("Εργασία Μαθήματος: Απόδοση Συστημάτων 2025")
    print("="*80)

    # Load all results
    df = load_all_results()

    # Descriptive statistics
    stats_summary = descriptive_statistics(df)

    # Test normality
    data, mean, std = test_normality(df)

    # Confidence interval
    ci_lower, ci_upper, required_n = confidence_interval(data)

    # Plot response times
    plot_response_times(df)

    # 2^k Factorial analysis
    factorial_2k_analysis(df)

    # Summary report
    generate_summary_report(df)

    print("\n" + "="*80)
    print("✓ ANALYSIS COMPLETE!")
    print("="*80)
    print(f"\nAll outputs saved to: {OUTPUT_DIR}/")
    print("\nGenerated files:")
    for file in sorted(OUTPUT_DIR.glob('*')):
        print(f"  - {file.name}")
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
