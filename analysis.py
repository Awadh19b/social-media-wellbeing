"""Social media use and student wellbeing: analysis + data-quality audit.
Run:  python analysis.py
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FILE = "data/Students_Social_Media_Addiction.csv"
USAGE = "Avg_Daily_Usage_Hours"
SLEEP = "Sleep_Hours_Per_Night"
MENTAL = "Mental_Health_Score"
ADDICT = "Addicted_Score"
GENDER = "Gender"
LEVEL = "Academic_Level"
COUNTRY = "Country"
AGE = "Age"

out = []


def say(text=""):
    print(text)
    out.append(str(text))


def partial_corr(d, x, y, z):
    """Spearman correlation of x and y after removing the effect of z."""
    c = d[[x, y, z]].corr(method="spearman")
    r_xy, r_xz, r_yz = c.loc[x, y], c.loc[x, z], c.loc[y, z]
    return (r_xy - r_xz * r_yz) / (((1 - r_xz**2) * (1 - r_yz**2)) ** 0.5)


def bootstrap_ci(d, func, n=1000, seed=0):
    """95% bootstrap confidence interval for any statistic func(dataframe)."""
    rng = np.random.default_rng(seed)
    vals = [func(d.sample(len(d), replace=True, random_state=int(rng.integers(1e9))))
            for _ in range(n)]
    return np.percentile(vals, [2.5, 97.5])


# 1. Load
df = pd.read_csv(FILE)
needed = [USAGE, SLEEP, MENTAL, ADDICT, GENDER, LEVEL, COUNTRY, AGE]
missing = [c for c in needed if c not in df.columns]
if missing:
    raise SystemExit(f"Columns not found: {missing}\nYour columns: {list(df.columns)}")

# 2. Data-quality audit
say("=== 1. DATA-QUALITY AUDIT ===")
say(f"Rows: {len(df)}")
say(f"Duplicate rows: {df.duplicated().sum()}")
say(f"Missing values (total): {int(df[needed].isna().sum().sum())}")
say(f"Usage hours: {df[USAGE].min()} to {df[USAGE].max()} | "
    f"Sleep hours: {df[SLEEP].min()} to {df[SLEEP].max()}")
say(f"Mental health score: {df[MENTAL].min()} to {df[MENTAL].max()} | "
    f"Addicted score: {df[ADDICT].min()} to {df[ADDICT].max()}")

total = df[MENTAL] + df[ADDICT]
say("\nCheck A: are the mental health and addiction scores near-mirror images?")
say(f"  Spearman correlation: {df[[MENTAL, ADDICT]].corr(method='spearman').iloc[0, 1]:.2f}")
say(f"  Mental + Addicted always falls between {total.min()} and {total.max()}.")
say("  Distribution of the sum (value: share of students):")
for k, v in total.value_counts(normalize=True).sort_index().items():
    say(f"    {k}: {v:.1%}")
say("  -> Real, independent survey answers rarely line up this tightly.")

say("\nCheck B: sample structure")
say(f"  Gender counts: {df[GENDER].value_counts().to_dict()}")
vc = df[COUNTRY].value_counts()
say(f"  Countries: {len(vc)}; countries with 5 or fewer students: {(vc <= 5).sum()}")
hs_ages = sorted(int(a) for a in df.loc[df[LEVEL] == 'High School', AGE].unique())
say(f"  'High School' students' ages: {hs_ages}")
say(f"  Group sizes by academic level: {df[LEVEL].value_counts().to_dict()}")

df = df[df[USAGE].between(0, 24) & df[SLEEP].between(0, 24)].dropna(subset=needed)

# 3. Descriptives
say("\n=== 2. DESCRIPTIVE STATISTICS ===")
say(df[[USAGE, SLEEP, MENTAL, ADDICT]].describe().round(2).to_string())

# 4. RQ1
say("\n=== 3. RQ1: CORRELATIONS (Spearman) ===")
corr = df[[USAGE, SLEEP, MENTAL, ADDICT]].corr(method="spearman").round(2)
say(corr.to_string())
ci = bootstrap_ci(df, lambda d: d[[USAGE, MENTAL]].corr(method="spearman").iloc[0, 1])
say(f"Usage vs mental health: {corr.loc[USAGE, MENTAL]:.2f}  (95% CI {ci[0]:.2f} to {ci[1]:.2f})")

#5. RQ2
say("\n=== 4. RQ2: DOES SLEEP EXPLAIN PART OF THE LINK? ===")
p = partial_corr(df, USAGE, MENTAL, SLEEP)
ci_p = bootstrap_ci(df, lambda d: partial_corr(d, USAGE, MENTAL, SLEEP))
say(f"Usage vs mental health, controlling for sleep: {p:.2f}  (95% CI {ci_p[0]:.2f} to {ci_p[1]:.2f})")
say("Note: the addiction score is NOT used as a separate predictor (see Check A).")

#6. RQ3
say("\n=== 5. RQ3: AVERAGES BY GROUP ===")
for col in [GENDER, LEVEL]:
    say(f"\nBy {col}:")
    say(df.groupby(col)[[USAGE, SLEEP, MENTAL]].agg(["mean", "count"]).round(2).to_string())

# 7. Charts
rng = np.random.default_rng(1)
plt.figure(figsize=(6, 4))
plt.scatter(df[USAGE] + rng.normal(0, .05, len(df)),
            df[MENTAL] + rng.normal(0, .08, len(df)), alpha=0.4)
plt.xlabel("Daily social media use (hours)")
plt.ylabel("Mental health score (jittered)")
plt.title("Usage vs mental health")
plt.tight_layout(); plt.savefig("results/usage_vs_mental_health.png", dpi=150); plt.close()

plt.figure(figsize=(6, 4))
df.groupby(df[USAGE].round())[SLEEP].mean().plot(marker="o")
plt.xlabel("Daily social media use (hours, rounded)")
plt.ylabel("Average sleep (hours)")
plt.title("Sleep by level of use")
plt.tight_layout(); plt.savefig("results/usage_vs_sleep.png", dpi=150); plt.close()

g = df.groupby(LEVEL)[MENTAL].agg(["mean", "count"])
plt.figure(figsize=(6, 4))
plt.bar(g.index, g["mean"])
for i, (m, n) in enumerate(zip(g["mean"], g["count"])):
    plt.text(i, m + 0.05, f"n={n}", ha="center")
plt.ylabel("Average mental health score")
plt.title("Mental health by academic level")
plt.tight_layout(); plt.savefig("results/mental_health_by_level.png", dpi=150); plt.close()

plt.figure(figsize=(6, 4))
(total.value_counts().sort_index()).plot(kind="bar")
plt.xlabel("Mental health score + addiction score")
plt.ylabel("Number of students")
plt.title("Audit: the two scores almost always sum to 12-13")
plt.tight_layout(); plt.savefig("results/audit_score_sum.png", dpi=150); plt.close()

with open("results/summary.txt", "w") as f:
    f.write("\n".join(out))
say("\nDone. Charts and summary.txt are in the results/ folder.")
