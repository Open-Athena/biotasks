The draft specification has been written to `/app/work/seta-cytopathology/draft_spec.md`.

**Summary of the analysis and design:**

**Viability check (passed)**: The seed is a classic tabular ML problem — Wisconsin Breast Cancer diagnostic data (569 rows × 33 columns, 122 KB), CPU-only, seconds of compute, and the original R Markdown compares four model families. No deep learning, no GPU, no oversized data.

**What the seed notebook does**: EDA → correlation analysis → PCA (PC1+PC2 = 63.3% variance) → t-SNE → 70/30 split (seed 314) → RandomForest / GBM / LightGBM / XGBoost with 5-fold CV → confusion matrix + AUC → RF variable importance → weighted ensemble, concluding GBM was best with ~0.95–0.99 AUC.

**How I evolved it into a terminal task**:
- **Preserved the core**: evidence-driven diagnostic classification with multi-model comparison.
- **Added discoverable wrinkles from the real data**: the CSV header ends with a trailing comma (creating a spurious all-NaN column in pandas), an `id` column that's a leakage trap, strong multicollinearity (radius/perimeter/area triads), and a 63/37 class imbalance — none of which are called out in the agent-visible brief.
- **Required exploration over replication**: the agent must decide preprocessing, feature strategy (keep all 30 vs. prune redundant), and model selection, with ≥3 model families, 5-fold CV, and thresholds (AUC ≥ 0.95, accuracy ≥ 0.93) calibrated to the notebook's reported results.
- **Concrete artifacts**: `results/metrics.json`, `predictions.csv`, `feature_importance.csv`, `eda.json`, and `report.md`, with 10 pytest tests that independently recompute ground truth from the raw CSV to catch fabrication (metric consistency, test-set integrity, correct class counts, PCA variance range, plausible top features overlapping the notebook's reference set).
- **22 reasoning steps → medium difficulty**, comfortably within the 1-CPU / <30-minute / 50-turn constraints.