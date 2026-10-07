import pandas as pd
import numpy as np
import os


def test_predictions_file_exists_and_correct_size():
    """Test 1: predictions.csv exists with correct row count (~30% of 569)."""
    path = "/results/predictions.csv"
    assert os.path.exists(path), "results/predictions.csv does not exist"
    df = pd.read_csv(path)
    assert len(df) > 0, "predictions.csv is empty"
    assert 165 <= len(df) <= 175, (
        f"Expected ~171 rows (30% of 569), got {len(df)}"
    )


def test_predictions_format_and_values():
    """Test 2: predictions.csv has required columns and valid values."""
    df = pd.read_csv("/results/predictions.csv")
    required_cols = ["id", "true_label", "predicted_label", "predicted_proba"]
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"
    assert set(df["predicted_label"].unique()).issubset({0, 1}), (
        "predicted_label must contain only 0 and 1"
    )
    assert df["predicted_proba"].between(0.0, 1.0).all(), (
        "predicted_proba values must be between 0 and 1"
    )
    assert 0 in df["true_label"].values and 1 in df["true_label"].values, (
        "true_label must contain both 0 and 1"
    )


def test_model_comparison_at_least_3_models():
    """Test 3: model_comparison.csv has at least 3 distinct models."""
    path = "/results/model_comparison.csv"
    assert os.path.exists(path), "results/model_comparison.csv does not exist"
    df = pd.read_csv(path)
    required_cols = ["model_name", "accuracy", "auc", "cv_mean_auc", "cv_std_auc"]
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"
    assert len(df) >= 3, f"Expected at least 3 models, got {len(df)}"
    assert df["model_name"].nunique() >= 3, "Model names must be distinct"


def test_model_metrics_realistic_ranges():
    """Test 4: All model metrics are in realistic ranges."""
    df = pd.read_csv("/results/model_comparison.csv")
    for _, row in df.iterrows():
        name = row["model_name"]
        assert 0.85 <= row["accuracy"] <= 1.0, (
            f"{name}: accuracy {row['accuracy']} not in [0.85, 1.0]"
        )
        assert 0.90 <= row["auc"] <= 1.0, (
            f"{name}: auc {row['auc']} not in [0.90, 1.0]"
        )
        assert 0.90 <= row["cv_mean_auc"] <= 1.0, (
            f"{name}: cv_mean_auc {row['cv_mean_auc']} not in [0.90, 1.0]"
        )
        assert row["cv_std_auc"] > 0.001, (
            f"{name}: cv_std_auc {row['cv_std_auc']} too small — CV variance expected"
        )


def test_cross_validation_genuine():
    """Test 5: Cross-validation was genuinely performed (values differ across models)."""
    df = pd.read_csv("/results/model_comparison.csv")
    cv_stds = df["cv_std_auc"].values
    assert not np.all(cv_stds == cv_stds[0]), (
        "All cv_std_auc values are identical — likely fabricated"
    )
    cv_means = df["cv_mean_auc"].values
    assert not np.all(cv_means == cv_means[0]), (
        "All cv_mean_auc values are identical — different models should differ"
    )


def test_feature_importance_plausible():
    """Test 6: Feature importance has correct format and plausible top features."""
    path = "/results/feature_importance.csv"
    assert os.path.exists(path), "results/feature_importance.csv does not exist"
    df = pd.read_csv(path)
    assert "feature" in df.columns, "Missing column: feature"
    assert "importance" in df.columns, "Missing column: importance"
    assert len(df) >= 5, f"Expected at least 5 features, got {len(df)}"
    assert pd.to_numeric(df["importance"], errors="coerce").notna().all(), (
        "importance values must be numeric"
    )
    assert not (df["importance"] == 0).all(), "All importance values are zero"
    known_top = {
        "concave points_worst", "perimeter_worst", "area_worst",
        "radius_worst", "concavity_mean"
    }
    top10 = set(df.head(10)["feature"].values)
    overlap = known_top & top10
    assert len(overlap) >= 1, (
        f"None of the known top features found in top 10: {top10}"
    )


def test_ensemble_predictions_and_auc():
    """Test 7: Ensemble predictions exist and achieve AUC >= 0.93."""
    from sklearn.metrics import roc_auc_score

    pred_path = "/results/predictions.csv"
    ens_path = "/results/ensemble_predictions.csv"
    assert os.path.exists(ens_path), "results/ensemble_predictions.csv does not exist"
    ens = pd.read_csv(ens_path)
    pred = pd.read_csv(pred_path)
    assert len(ens) == len(pred), (
        f"Ensemble row count ({len(ens)}) != predictions row count ({len(pred)})"
    )
    required_cols = ["id", "true_label", "predicted_label", "predicted_proba"]
    for col in required_cols:
        assert col in ens.columns, f"Ensemble missing column: {col}"

    auc = roc_auc_score(ens["true_label"], ens["predicted_proba"])
    assert auc >= 0.93, f"Ensemble AUC {auc:.4f} < 0.93"

    # Ensure ensemble is actually combined, not identical to single model
    ens_proba = ens["predicted_proba"].values
    pred_proba = pred["predicted_proba"].values
    assert not np.allclose(ens_proba, pred_proba, atol=1e-6), (
        "Ensemble probabilities are identical to single model — not a real ensemble"
    )


def test_analysis_report_substantive():
    """Test 8: Analysis report has substantive content covering key topics."""
    path = "/results/analysis_report.md"
    assert os.path.exists(path), "results/analysis_report.md does not exist"
    content = open(path).read()
    assert len(content) >= 500, (
        f"Report too short: {len(content)} chars, expected >= 500"
    )
    content_lower = content.lower()
    assert "correlation" in content_lower or "multicollinearity" in content_lower, (
        "Report must discuss correlation or multicollinearity"
    )
    assert "feature" in content_lower, "Report must discuss features"
    assert "ensemble" in content_lower or "weighted" in content_lower, (
        "Report must discuss ensemble or weighted combination"
    )
    # Check at least two model names mentioned
    model_keywords = ["random forest", "gradient", "xgboost", "logistic", "svm", "lightgbm"]
    found = [kw for kw in model_keywords if kw in content_lower]
    assert len(found) >= 2, (
        f"Report should mention at least 2 model types, found: {found}"
    )


def test_predictions_mathematically_consistent():
    """Test 9: Predictions accuracy is consistent with model_comparison metrics."""
    pred = pd.read_csv("/results/predictions.csv")
    comp = pd.read_csv("/results/model_comparison.csv")
    actual_acc = (pred["predicted_label"] == pred["true_label"]).mean()
    # The predictions should come from one of the reported models
    # Check that computed accuracy is close to at least one model's reported accuracy
    accuracies = comp["accuracy"].values
    min_diff = min(abs(actual_acc - a) for a in accuracies)
    assert min_diff < 0.02, (
        f"Computed accuracy {actual_acc:.4f} doesn't match any reported model accuracy within 0.02"
    )


def test_no_nan_or_inf_in_outputs():
    """Test 10: No NaN or infinite values in any output CSV."""
    files = [
        "/results/predictions.csv",
        "/results/model_comparison.csv",
        "/results/feature_importance.csv",
        "/results/ensemble_predictions.csv",
    ]
    for fpath in files:
        assert os.path.exists(fpath), f"{fpath} does not exist"
        df = pd.read_csv(fpath)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert not df[col].isna().any(), f"NaN found in {fpath} column {col}"
            assert not np.isinf(df[col].values).any(), (
                f"Inf found in {fpath} column {col}"
            )
