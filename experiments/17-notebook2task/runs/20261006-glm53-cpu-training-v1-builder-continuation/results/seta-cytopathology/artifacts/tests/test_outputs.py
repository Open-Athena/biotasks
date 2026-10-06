"""Independent verifier for the fixed cytopathology model-comparison protocol.

The verifier loads the solver's artifacts from /app and regenerates every
published quantity (split, folds, model fits, metrics, EDA facts) from its own
trusted copy of the source data staged next to this file as ``data.csv``.
It never imports, parses, or executes solver code, never trusts solver-supplied
ground truth, fold assignments, metrics, or model names alone, and never relies
on an optional training-id file.
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20250607
TEST_SIZE = 0.2
N_SPLITS = 5
TOL = 1e-6

# Declared model identifiers; this list is also the declared tie-break order.
MODELS = ["logistic_regression", "random_forest", "gradient_boosting"]

APP = Path("/app")
RESULTS = APP / "results"
REPORT = APP / "report.md"
RUNNER = APP / "run_pipeline.py"

HERE = Path(__file__).resolve().parent
TRUSTED_CSV = HERE / "data.csv"

METRIC_FIELDS = {
    "cv_roc_auc_mean",
    "cv_roc_auc_per_fold",
    "cv_accuracy",
    "cv_precision",
    "cv_recall",
    "cv_f1",
    "test_roc_auc",
    "test_accuracy",
    "test_precision",
    "test_recall",
    "test_f1",
}

SELECTED_REPORT_FIELDS = {
    "selected_model",
    "cv_roc_auc_mean",
    "test_roc_auc",
    "test_accuracy",
    "label_mapping",
    "random_state",
    "n_train",
    "n_test",
    "feature_count",
    "excluded_columns",
}

EDA_FIELDS = {
    "class_counts",
    "missing_values",
    "high_correlation_pairs",
    "pca_two_component_variance",
}


def _make_model(name):
    """Declared native algorithms, exactly as published."""
    if name == "logistic_regression":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=1000, solver="lbfgs", random_state=SEED
                    ),
                ),
            ]
        )
    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=100, random_state=SEED, n_jobs=1
        )
    if name == "gradient_boosting":
        return HistGradientBoostingClassifier(random_state=SEED)
    raise ValueError("unknown model identifier: %s" % name)


def _binary_metrics(y_true, y_pred, y_proba):
    return {
        "roc_auc": float(roc_auc_score(y_true, y_proba)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


@pytest.fixture(scope="module")
def reference():
    """Regenerate the whole published protocol from the trusted data copy."""
    df = pd.read_csv(TRUSTED_CSV)
    empty_cols = [c for c in df.columns if df[c].isna().all()]
    feature_cols = [
        c
        for c in df.columns
        if c not in ("id", "diagnosis") and c not in empty_cols
    ]
    X = df[feature_cols].to_numpy(dtype=np.float64)
    y = df["diagnosis"].map({"B": 0, "M": 1}).to_numpy(dtype=np.int64)
    ids = df["id"].to_numpy(dtype=np.int64)

    n_samples = len(df)
    train_idx, test_idx = train_test_split(
        np.arange(n_samples),
        test_size=TEST_SIZE,
        random_state=SEED,
        shuffle=True,
        stratify=y,
    )
    X_train, y_train = X[train_idx], y[train_idx]
    X_test, y_test = X[test_idx], y[test_idx]
    ids_train, ids_test = ids[train_idx], ids[test_idx]

    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    fold_of_pos = np.full(len(train_idx), -1, dtype=int)
    oof = {m: np.zeros(len(train_idx), dtype=np.float64) for m in MODELS}
    for fold, (tr, te) in enumerate(skf.split(X_train, y_train)):
        fold_of_pos[te] = fold
        for m in MODELS:
            est = _make_model(m)
            est.fit(X_train[tr], y_train[tr])
            oof[m][te] = est.predict_proba(X_train[te])[:, 1]
    assert (fold_of_pos >= 0).all()

    test_prob = {}
    for m in MODELS:
        est = _make_model(m)
        est.fit(X_train, y_train)
        test_prob[m] = est.predict_proba(X_test)[:, 1]

    # Intentionally leaky variant: preprocessing (and the model) fit on the
    # full dataset before any splitting, i.e. trained on test rows too.
    leaky = _make_model("logistic_regression")
    leaky.fit(X, y)
    leaky_oof = leaky.predict_proba(X_train)[:, 1]
    leaky_test = leaky.predict_proba(X_test)[:, 1]

    # Descriptive EDA facts recomputed from the trusted copy.
    class_counts = {k: int(v) for k, v in df["diagnosis"].value_counts().items()}
    missing_values = {c: int(df[c].isna().sum()) for c in df.columns}
    corr = df[feature_cols].corr(method="pearson")
    high_corr_pairs = 0
    for i in range(len(feature_cols)):
        for j in range(i + 1, len(feature_cols)):
            if abs(float(corr.iloc[i, j])) > 0.9:
                high_corr_pairs += 1
    scaler = StandardScaler()
    Z = scaler.fit_transform(X)
    pca = PCA(n_components=2, svd_solver="full").fit(Z)
    pca_two_component_variance = float(pca.explained_variance_ratio_.sum())

    return {
        "df": df,
        "empty_cols": empty_cols,
        "feature_cols": feature_cols,
        "ids": ids,
        "y": y,
        "ids_train": ids_train,
        "ids_test": ids_test,
        "y_train": y_train,
        "y_test": y_test,
        "fold_of_pos": fold_of_pos,
        "oof": oof,
        "test_prob": test_prob,
        "leaky_oof": leaky_oof,
        "leaky_test": leaky_test,
        "class_counts": class_counts,
        "missing_values": missing_values,
        "high_corr_pairs": high_corr_pairs,
        "pca_two_component_variance": pca_two_component_variance,
    }


def _require(path):
    if not path.is_file():
        pytest.fail("required artifact %s does not exist" % path)
    return path


def _load_csv(path, columns):
    _require(path)
    frame = pd.read_csv(path)
    missing = [c for c in columns if c not in frame.columns]
    assert not missing, "%s is missing columns: %s" % (path, missing)
    return frame


def _load_json(path):
    _require(path)
    with open(path) as fh:
        return json.load(fh)


def _per_fold_aucs(frame, model):
    sub = frame[frame["model"] == model]
    aucs = []
    for fold in range(N_SPLITS):
        fsub = sub[sub["fold"] == fold]
        assert len(fsub) > 0, "no OOF rows for %s in fold %d" % (model, fold)
        aucs.append(float(roc_auc_score(fsub["y_true"], fsub["y_proba"])))
    return aucs


def test_artifacts_exist_and_schema(reference):
    oof = _load_csv(
        RESULTS / "oof_predictions.csv",
        ["id", "model", "fold", "y_true", "y_pred", "y_proba"],
    )
    tst = _load_csv(
        RESULTS / "test_predictions.csv",
        ["id", "model", "y_true", "y_pred", "y_proba"],
    )
    assert len(oof) == 1365, "expected 1365 OOF rows, found %d" % len(oof)
    assert len(tst) == 342, "expected 342 test rows, found %d" % len(tst)

    metrics = _load_json(RESULTS / "metrics.json")
    assert set(metrics.keys()) >= {"models", "selected_model", "selection_rule"}
    assert set(metrics["models"].keys()) == set(MODELS)
    for m in MODELS:
        assert set(metrics["models"][m].keys()) == METRIC_FIELDS, (
            "metrics.json[%s] field set mismatch" % m
        )
        assert len(metrics["models"][m]["cv_roc_auc_per_fold"]) == N_SPLITS

    selected_report = _load_json(RESULTS / "selected_model_report.json")
    assert set(selected_report.keys()) >= SELECTED_REPORT_FIELDS

    eda = _load_json(RESULTS / "eda.json")
    assert set(eda.keys()) >= EDA_FIELDS

    _require(REPORT)
    text = REPORT.read_text()
    assert len(text.strip()) > 0, "report.md is empty"

    # The pipeline entry point must be present as a real, parseable script.
    _require(RUNNER)
    assert RUNNER.stat().st_size > 0, "run_pipeline.py is empty"
    compile(RUNNER.read_text(), str(RUNNER), "exec")

    # folds.csv is optional per the published schema, but must conform if present.
    folds_path = RESULTS / "folds.csv"
    if folds_path.is_file():
        folds = pd.read_csv(folds_path)
        missing = [c for c in ("id", "fold") if c not in folds.columns]
        assert not missing, "folds.csv is missing columns: %s" % missing
        assert len(folds) == len(reference["ids_train"]) == 455


def test_row_key_integrity(reference):
    oof = _load_csv(
        RESULTS / "oof_predictions.csv",
        ["id", "model", "fold", "y_true", "y_pred", "y_proba"],
    )
    tst = _load_csv(
        RESULTS / "test_predictions.csv",
        ["id", "model", "y_true", "y_pred", "y_proba"],
    )

    raw_ids = set(int(i) for i in reference["ids"])
    label_by_id = {int(i): int(v) for i, v in zip(reference["ids"], reference["y"])}

    for frame, expected_rows, name in (
        (oof, len(reference["ids_train"]), "oof_predictions"),
        (tst, len(reference["ids_test"]), "test_predictions"),
    ):
        assert set(frame["model"].unique().tolist()) == set(MODELS), (
            "%s must contain exactly the three declared model identifiers" % name
        )
        for m in MODELS:
            sub = frame[frame["model"] == m]
            assert len(sub) == expected_rows, (
                "%s has %d rows for %s, expected %d"
                % (name, len(sub), m, expected_rows)
            )
            assert sub["id"].is_unique, "%s has duplicate ids for %s" % (name, m)
        assert set(int(i) for i in frame["id"]) <= raw_ids, (
            "%s contains ids outside the raw file" % name
        )
        mapped = np.array(
            [label_by_id[int(i)] for i in frame["id"]], dtype=float
        )
        assert np.array_equal(frame["y_true"].to_numpy(dtype=float), mapped), (
            "%s y_true does not match the raw labels under B=0/M=1" % name
        )
        proba = frame["y_proba"].to_numpy(dtype=float)
        assert np.all(np.isfinite(proba)), "%s has non-finite probabilities" % name
        assert np.all((proba >= 0.0) & (proba <= 1.0)), (
            "%s has probabilities outside [0, 1]" % name
        )
        expected_pred = (proba >= 0.5).astype(float)
        assert np.array_equal(
            frame["y_pred"].to_numpy(dtype=float), expected_pred
        ), "%s y_pred is not (y_proba >= 0.5)" % name

    folds = oof["fold"].to_numpy(dtype=int)
    assert set(np.unique(folds)).issubset(set(range(N_SPLITS))), (
        "OOF fold indices must be 0..%d" % (N_SPLITS - 1)
    )


def test_split_and_fold_membership(reference):
    oof = _load_csv(
        RESULTS / "oof_predictions.csv",
        ["id", "model", "fold", "y_true", "y_pred", "y_proba"],
    )
    tst = _load_csv(
        RESULTS / "test_predictions.csv",
        ["id", "model", "y_true", "y_pred", "y_proba"],
    )

    train_ids = set(int(i) for i in reference["ids_train"])
    test_ids = set(int(i) for i in reference["ids_test"])
    assert len(train_ids) == 455 and len(test_ids) == 114
    assert not (train_ids & test_ids)

    for m in MODELS:
        got_train = set(int(i) for i in oof[oof["model"] == m]["id"])
        got_test = set(int(i) for i in tst[tst["model"] == m]["id"])
        assert got_train == train_ids, (
            "OOF id set for %s does not match the regenerated training split" % m
        )
        assert got_test == test_ids, (
            "test id set for %s does not match the regenerated test split" % m
        )

    ref_fold_by_id = {
        int(i): int(f)
        for i, f in zip(reference["ids_train"], reference["fold_of_pos"])
    }
    for m in MODELS:
        sub = oof[oof["model"] == m]
        got = {int(i): int(f) for i, f in zip(sub["id"], sub["fold"])}
        assert got == ref_fold_by_id, (
            "fold assignment for %s does not match the regenerated "
            "StratifiedKFold(5, shuffle=True, random_state=%d)" % (m, SEED)
        )

    folds_path = RESULTS / "folds.csv"
    if folds_path.is_file():
        folds = pd.read_csv(folds_path)
        got = {int(i): int(f) for i, f in zip(folds["id"], folds["fold"])}
        assert got == ref_fold_by_id, "folds.csv disagrees with regenerated folds"


def test_probabilities_match_reference(reference):
    oof = _load_csv(
        RESULTS / "oof_predictions.csv",
        ["id", "model", "fold", "y_true", "y_pred", "y_proba"],
    )
    tst = _load_csv(
        RESULTS / "test_predictions.csv",
        ["id", "model", "y_true", "y_pred", "y_proba"],
    )

    # Discrimination guard: an intentionally leaky pipeline (preprocessing and
    # model fit on the full dataset before splitting) must fall outside the
    # tolerance, so a match below genuinely certifies the honest protocol.
    honest_oof = reference["oof"]["logistic_regression"]
    honest_test = reference["test_prob"]["logistic_regression"]
    leak_gap = max(
        float(np.max(np.abs(reference["leaky_oof"] - honest_oof))),
        float(np.max(np.abs(reference["leaky_test"] - honest_test))),
    )
    assert leak_gap > TOL, (
        "leaky reference variant is not distinguishable at tolerance %g "
        "(gap %g)" % (TOL, leak_gap)
    )

    ref_oof = {}
    for m in MODELS:
        for i, p in zip(reference["ids_train"], reference["oof"][m]):
            ref_oof[(int(i), m)] = float(p)
    ref_test = {}
    for m in MODELS:
        for i, p in zip(reference["ids_test"], reference["test_prob"][m]):
            ref_test[(int(i), m)] = float(p)

    for m in MODELS:
        sub = oof[oof["model"] == m]
        expected = np.array(
            [ref_oof[(int(i), m)] for i in sub["id"]], dtype=float
        )
        got = sub["y_proba"].to_numpy(dtype=float)
        diff = float(np.max(np.abs(got - expected)))
        assert diff <= TOL, (
            "OOF probabilities for %s deviate from the independent reference "
            "by %g (tolerance %g)" % (m, diff, TOL)
        )

    for m in MODELS:
        sub = tst[tst["model"] == m]
        expected = np.array(
            [ref_test[(int(i), m)] for i in sub["id"]], dtype=float
        )
        got = sub["y_proba"].to_numpy(dtype=float)
        diff = float(np.max(np.abs(got - expected)))
        assert diff <= TOL, (
            "test probabilities for %s deviate from the independent reference "
            "by %g (tolerance %g)" % (m, diff, TOL)
        )


def test_metrics_recomputed_consistent(reference):
    metrics = _load_json(RESULTS / "metrics.json")
    oof = _load_csv(
        RESULTS / "oof_predictions.csv",
        ["id", "model", "fold", "y_true", "y_pred", "y_proba"],
    )
    tst = _load_csv(
        RESULTS / "test_predictions.csv",
        ["id", "model", "y_true", "y_pred", "y_proba"],
    )

    for m in MODELS:
        reported = metrics["models"][m]
        sub = oof[oof["model"] == m]
        tsub = tst[tst["model"] == m]
        assert len(sub) == 455 and len(tsub) == 114

        per_fold = _per_fold_aucs(oof, m)
        reported_folds = reported["cv_roc_auc_per_fold"]
        assert len(reported_folds) == N_SPLITS
        for got, exp in zip(reported_folds, per_fold):
            assert abs(float(got) - exp) <= TOL, (
                "per-fold CV ROC-AUC mismatch for %s" % m
            )
        assert (
            abs(float(reported["cv_roc_auc_mean"]) - float(np.mean(per_fold)))
            <= TOL
        ), "cv_roc_auc_mean is not the mean of the five fold AUCs for %s" % m

        pooled = _binary_metrics(sub["y_true"], sub["y_pred"], sub["y_proba"])
        for key, value in (
            ("cv_accuracy", "accuracy"),
            ("cv_precision", "precision"),
            ("cv_recall", "recall"),
            ("cv_f1", "f1"),
        ):
            assert abs(float(reported[key]) - pooled[value]) <= TOL, (
                "%s for %s is not recomputed-consistent with oof_predictions.csv"
                % (key, m)
            )

        test_metrics = _binary_metrics(
            tsub["y_true"], tsub["y_pred"], tsub["y_proba"]
        )
        for key, value in (
            ("test_roc_auc", "roc_auc"),
            ("test_accuracy", "accuracy"),
            ("test_precision", "precision"),
            ("test_recall", "recall"),
            ("test_f1", "f1"),
        ):
            assert abs(float(reported[key]) - test_metrics[value]) <= TOL, (
                "%s for %s is not recomputed-consistent with "
                "test_predictions.csv" % (key, m)
            )


def test_selection_rule_consistent(reference):
    metrics = _load_json(RESULTS / "metrics.json")
    oof = _load_csv(
        RESULTS / "oof_predictions.csv",
        ["id", "model", "fold", "y_true", "y_pred", "y_proba"],
    )

    means = {}
    for m in MODELS:
        per_fold = _per_fold_aucs(oof, m)
        means[m] = float(np.mean(per_fold))
        assert (
            abs(means[m] - float(metrics["models"][m]["cv_roc_auc_mean"])) <= TOL
        ), "reported cv_roc_auc_mean for %s disagrees with its OOF rows" % m

    best_value = max(means.values())
    expected_selected = next(m for m in MODELS if means[m] == best_value)
    assert metrics["selected_model"] == expected_selected, (
        "selected_model must be the argmax of mean training-fold ROC-AUC "
        "under the LR -> RF -> GB tie-break"
    )

    rule = metrics["selection_rule"]
    assert isinstance(rule, str) and len(rule) >= 10, (
        "selection_rule must be a descriptive string"
    )
    assert "roc-auc" in rule.lower(), "selection_rule must name ROC-AUC"

    report = _load_json(RESULTS / "selected_model_report.json")
    assert report["selected_model"] == expected_selected
    sel_metrics = metrics["models"][expected_selected]
    assert (
        abs(float(report["cv_roc_auc_mean"]) - float(sel_metrics["cv_roc_auc_mean"]))
        <= TOL
    )
    assert abs(float(report["test_roc_auc"]) - float(sel_metrics["test_roc_auc"])) <= TOL
    assert (
        abs(float(report["test_accuracy"]) - float(sel_metrics["test_accuracy"]))
        <= TOL
    )
    assert int(report["n_train"]) == len(reference["ids_train"]) == 455
    assert int(report["n_test"]) == len(reference["ids_test"]) == 114
    assert int(report["feature_count"]) == 30 == len(reference["feature_cols"])
    assert int(report["random_state"]) == SEED
    assert report["label_mapping"] == {"B": 0, "M": 1}
    excluded = report["excluded_columns"]
    assert set(excluded) == {"id"} | set(reference["empty_cols"]) and len(
        excluded
    ) == 2, "excluded_columns must be id plus the spurious empty column"


def test_three_distinct_model_families(reference):
    metrics = _load_json(RESULTS / "metrics.json")
    oof = _load_csv(
        RESULTS / "oof_predictions.csv",
        ["id", "model", "fold", "y_true", "y_pred", "y_proba"],
    )
    tst = _load_csv(
        RESULTS / "test_predictions.csv",
        ["id", "model", "y_true", "y_pred", "y_proba"],
    )
    assert set(metrics["models"].keys()) == set(MODELS)

    vectors = {}
    for m in MODELS:
        sub = oof[oof["model"] == m].sort_values("id")
        assert len(sub) == 455
        vectors[m] = sub["y_proba"].to_numpy(dtype=float)
    pairs = [
        ("logistic_regression", "random_forest"),
        ("logistic_regression", "gradient_boosting"),
        ("random_forest", "gradient_boosting"),
    ]
    for a, b in pairs:
        gap = float(np.max(np.abs(vectors[a] - vectors[b])))
        assert gap > TOL, (
            "OOF probability vectors for %s and %s are indistinguishable "
            "(max abs difference %g); three distinct model families must be "
            "compared, not copies of one another" % (a, b, gap)
        )

    for m in MODELS:
        assert set(tst[tst["model"] == m]["id"]) == set(
            int(i) for i in reference["ids_test"]
        )


def test_eda_facts_match_trusted_data(reference):
    eda = _load_json(RESULTS / "eda.json")
    df = reference["df"]
    feature_cols = reference["feature_cols"]

    assert eda["class_counts"] == reference["class_counts"]
    assert reference["class_counts"] == {"B": 357, "M": 212}

    assert eda["missing_values"] == reference["missing_values"], (
        "missing_values must report per-raw-column missing counts, including "
        "the spurious all-empty column"
    )

    expected_pairs = reference["high_corr_pairs"]
    assert expected_pairs >= 30
    assert int(eda["high_correlation_pairs"]) == expected_pairs, (
        "high_correlation_pairs must count feature pairs with |Pearson r| > 0.9"
    )

    got_var = float(eda["pca_two_component_variance"])
    assert abs(got_var - reference["pca_two_component_variance"]) <= TOL, (
        "pca_two_component_variance must be the cumulative variance of the "
        "first two components of StandardScaler + PCA(svd_solver='full')"
    )


def test_report_content(reference):
    metrics = _load_json(RESULTS / "metrics.json")
    _require(REPORT)
    text = REPORT.read_text()

    assert len(text.split()) >= 300, "report.md must contain at least 300 words"
    for m in MODELS:
        assert m in text, "report.md must name %s" % m
    selected = metrics["selected_model"]
    assert selected in text, "report.md must name the selected model"
    assert str(SEED) in text, "report.md must state the random seed"

    sel_metrics = metrics["models"][selected]
    for value in (
        sel_metrics["cv_roc_auc_mean"],
        sel_metrics["test_roc_auc"],
        sel_metrics["test_accuracy"],
    ):
        formatted = "%.6f" % float(value)
        assert formatted in text, (
            "report.md must report the headline number %s to six decimal "
            "places" % formatted
        )

    lowered = text.lower()
    assert "limitation" in lowered, "report.md must discuss limitations"
    assert ("imbalance" in lowered) or re.search(
        r"false[- ]negativ", lowered
    ), "report.md must discuss class imbalance or false-negative cost"
    assert "b" in lowered and "m" in lowered, (
        "report.md must state the label mapping"
    )
