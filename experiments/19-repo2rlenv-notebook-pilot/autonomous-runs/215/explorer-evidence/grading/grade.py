#!/usr/bin/env python3
"""Acceptance grader for the rat-tumor hierarchical-Bayesian analysis task.

Compares the three declared output CSVs against:
  * a deterministic recomputation of the Part-1 analytical grid posterior and
    the Part-2 exact posterior (numerical integration), both derived from the
    original task input counts (read from BIOTASKS_TRUSTED_INPUT_DIR);
  * internal cross-file consistency of the submitted summary file.

No submission code is imported or executed; no answer values are embedded.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy.special import gammaln

# ---------------------------------------------------------------- constants
GRID_X0, GRID_X1 = -230, -131          # integer hundredths, inclusive
GRID_Z0, GRID_Z1 = 100, 499           # integer hundredths, inclusive
GRID_NX = GRID_X1 - GRID_X0 + 1       # 100
GRID_NZ = GRID_Z1 - GRID_Z0 + 1      # 400
GRID_N = GRID_NX * GRID_NZ           # 40000

TOL_TOKEN = 1e-6        # |X*100 - round(X*100)| bound (grid-coordinate identity)
TOL_AB_REL = 1e-9       # alpha/beta vs deterministic recomputation (relative)
TOL_AB_ABS = 1e-15
TOL_W_REL = 1e-8        # normalized weight vs recomputation (relative)
TOL_W_ABS = 1e-30
TOL_SUM1 = 1e-9         # |sum(w) - 1|

CHAINS = (1, 2, 3, 4)
DRAWS_PER_CHAIN = 2000

MEAN_REL = 0.025        # pooled draw mean vs exact posterior mean (relative)
SD_REL = 0.20           # pooled draw sd vs exact posterior sd (relative)
CORR_ABS = 0.15         # alpha-beta Pearson correlation vs exact (absolute)
CHAIN_MEAN_SD = 0.50     # |chain mean - pooled mean| in exact posterior sds

TOL_AN_REL = 1e-10      # analytic_grid summary vs submitted grid (relative)
TOL_AN_ABS = 1e-12
TOL_MC_REL = 1e-8       # pymc_mcmc summary vs submitted draws (relative)
TOL_MC_ABS = 1e-10

EXPECTED_GRID_COLS = ["X", "Z", "alpha", "beta", "normed_exp_trans"]
EXPECTED_DRAWS_COLS = ["chain", "draw", "alpha", "beta"]
SUMMARY_COLS = ["method", "parameter", "estimate"]
SUMMARY_LABELS = {
    ("analytic_grid", "alpha"),
    ("analytic_grid", "beta"),
    ("pymc_mcmc", "alpha"),
    ("pymc_mcmc", "beta"),
}


# ------------------------------------------------------------------ helpers
def load_counts():
    """Return (y, n) float arrays from the original-hash-checked task input."""
    env = os.environ.get("BIOTASKS_TRUSTED_INPUT_DIR")
    if not env:
        return None, "BIOTASKS_TRUSTED_INPUT_DIR is not set"
    path = os.path.join(env, "rat_tumor_counts.csv")
    if not os.path.isfile(path):
        return None, "trusted input %s is missing" % "rat_tumor_counts.csv"
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - defensive
        return None, "cannot parse trusted counts: %s" % exc
    if list(df.columns) != ["y", "n"]:
        return None, "trusted counts must have columns y,n"
    y = pd.to_numeric(df["y"], errors="coerce").to_numpy(dtype=float)
    n = pd.to_numeric(df["n"], errors="coerce").to_numpy(dtype=float)
    if not (np.all(np.isfinite(y)) and np.all(np.isfinite(n))):
        return None, "trusted counts contain nonfinite values"
    if not (np.all(y >= 0) and np.all(n >= y)):
        return None, "trusted counts violate 0 <= y <= n"
    return (y, n), None


def read_submission_csv(path, expected_cols):
    """Parse a submission CSV; return (df, None) or (None, reason)."""
    if not os.path.isfile(path):
        return None, "file is missing"
    try:
        raw = pd.read_csv(path, header=None, nrows=1)
    except Exception as exc:
        return None, "cannot parse CSV (%s)" % type(exc).__name__
    header = [str(c) for c in raw.iloc[0].tolist()]
    if header != expected_cols:
        return None, "columns are %s, expected %s" % (header, expected_cols)
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return None, "cannot parse CSV rows (%s)" % type(exc).__name__
    if list(df.columns) != expected_cols:
        return None, "unexpected column names after parse"
    if len(df) == 0:
        return None, "file contains no data rows"
    return df, None


def numeric_column(df, col):
    """Return float array or (None, reason)."""
    try:
        vals = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
    except Exception:
        return None, "column %s is not numeric" % col
    if not np.all(np.isfinite(vals)):
        bad = int(np.sum(~np.isfinite(vals)))
        return None, "column %s has %d missing/nonfinite values" % (col, bad)
    return vals, None


def recompute_grid(y, n):
    """Deterministic Part-1 recomputation on the declared 100 x 400 grid.

    Returns (ix, iz, alpha, beta, w) flattened arrays; ix/iz are integer
    hundredth indices (cell identity).
    """
    ixs = np.arange(GRID_X0, GRID_X1 + 1)
    izs = np.arange(GRID_Z0, GRID_Z1 + 1)
    ix = np.tile(ixs, GRID_NZ)
    iz = np.repeat(izs, GRID_NX)
    x = ix / 100.0
    z = iz / 100.0
    ex = np.exp(x)
    ez = np.exp(z)
    beta = ez / (ex + 1.0)
    alpha = ex * beta
    n_exp = len(y)
    ll = n_exp * (gammaln(alpha + beta) - gammaln(alpha) - gammaln(beta))
    for Y, N in zip(y, n):
        ll += (
            gammaln(alpha + Y)
            + gammaln(beta + N - Y)
            - gammaln(alpha + beta + N)
        )
    lp = -2.5 * np.log(alpha + beta) + ll + np.log(alpha) + np.log(beta)
    lp = lp - lp.max()
    e = np.exp(lp)
    w = e / e.sum()
    return ix, iz, alpha, beta, w


def compute_exact_part2(y, n):
    """Exact moments of the Part-2 (alpha, beta) marginal posterior.

    The joint posterior density of (alpha, beta) under the specified Part-2
    model (HalfNormal(10) priors multiplied by the (alpha+beta)^(-5/2) factor,
    theta marginalized analytically) is integrated numerically in the
    transformed coordinates u = log(alpha/beta), v = log(alpha+beta).
    """
    u = np.linspace(-5.0, 1.0, 801)
    v = np.linspace(-1.5, 7.0, 1081)
    U, V = np.meshgrid(u, v, indexing="ij")
    ez = np.exp(V)
    ex = np.exp(U)
    b = ez / (ex + 1.0)
    a = ex * b
    n_exp = len(y)
    ll = n_exp * (gammaln(a + b) - gammaln(a) - gammaln(b))
    for Y, N in zip(y, n):
        ll += (
            gammaln(a + Y)
            + gammaln(b + N - Y)
            - gammaln(a + b + N)
        )
    lp = (
        -2.5 * np.log(a + b)
        - 0.5 * (a / 10.0) ** 2
        - 0.5 * (b / 10.0) ** 2
        + ll
        + np.log(a)
        + np.log(b)
    )
    lp = lp - lp.max()
    w = np.exp(lp)
    du = u[1] - u[0]
    dv = v[1] - v[0]
    z_norm = w.sum() * du * dv
    ea = float((w * a).sum() * du * dv / z_norm)
    eb = float((w * b).sum() * du * dv / z_norm)
    va = float((w * a * a).sum() * du * dv / z_norm) - ea * ea
    vb = float((w * b * b).sum() * du * dv / z_norm) - eb * eb
    cov = float((w * (a - ea) * (b - eb)).sum() * du * dv / z_norm)
    corr = cov / math.sqrt(va * vb)
    return {
        "mean_alpha": ea,
        "mean_beta": eb,
        "sd_alpha": math.sqrt(max(va, 0.0)),
        "sd_beta": math.sqrt(max(vb, 0.0)),
        "corr": corr,
    }


# ------------------------------------------------------------------- checks
def check_grid_structure(sub_dir):
    df, err = read_submission_csv(
        os.path.join(sub_dir, "analytic_posterior_grid.csv"), EXPECTED_GRID_COLS
    )
    if err:
        return False, err
    if len(df) != GRID_N:
        return False, "expected %d data rows, found %d" % (GRID_N, len(df))
    cols = {}
    for c in EXPECTED_GRID_COLS:
        vals, err = numeric_column(df, c)
        if err:
            return False, err
        cols[c] = vals
    x = cols["X"]
    z = cols["Z"]
    ix = np.rint(x * 100.0)
    iz = np.rint(z * 100.0)
    if np.max(np.abs(x * 100.0 - ix)) > TOL_TOKEN or np.max(
        np.abs(z * 100.0 - iz)
    ) > TOL_TOKEN:
        return False, "X/Z values are not on the declared 0.01 grid"
    ix = ix.astype(np.int64)
    iz = iz.astype(np.int64)
    in_x = (ix >= GRID_X0) & (ix <= GRID_X1)
    in_z = (iz >= GRID_Z0) & (iz <= GRID_Z1)
    if not (np.all(in_x) and np.all(in_z)):
        return False, "X/Z coordinates fall outside the declared grid ranges"
    key = (iz - GRID_Z0) * GRID_NX + (ix - GRID_X0)
    counts = np.bincount(key, minlength=GRID_N)
    if len(counts) != GRID_N or np.count_nonzero(counts != 1) > 0:
        bad = int(np.sum(counts != 1))
        return (
            False,
            "grid cells are not covered exactly once (%d cells with wrong "
            "multiplicity)" % bad,
        )
    if np.any(cols["alpha"] <= 0) or np.any(cols["beta"] <= 0):
        return False, "alpha/beta must be strictly positive"
    if np.any(cols["normed_exp_trans"] < 0):
        return False, "normed_exp_trans must be nonnegative"
    wsum = float(cols["normed_exp_trans"].sum())
    if abs(wsum - 1.0) > TOL_SUM1:
        return False, "weights sum to %.17g, expected 1 (tolerance %g)" % (
            wsum,
            TOL_SUM1,
        )
    return True, (
        "structure ok: %d rows, declared grid covered exactly once, weights "
        "sum to 1" % GRID_N
    )


def check_grid_values(sub_dir, counts):
    y, n = counts
    df, err = read_submission_csv(
        os.path.join(sub_dir, "analytic_posterior_grid.csv"), EXPECTED_GRID_COLS
    )
    if err:
        return False, err
    if len(df) != GRID_N:
        return False, "expected %d data rows, found %d" % (GRID_N, len(df))
    vals = {}
    for c in EXPECTED_GRID_COLS:
        arr, err = numeric_column(df, c)
        if err:
            return False, err
        vals[c] = arr
    x, z = vals["X"], vals["Z"]
    ix = np.rint(x * 100.0)
    iz = np.rint(z * 100.0)
    if (
        np.max(np.abs(x * 100.0 - ix)) > TOL_TOKEN
        or np.max(np.abs(z * 100.0 - iz)) > TOL_TOKEN
    ):
        return False, "X/Z values are not on the declared 0.01 grid"
    ix = ix.astype(np.int64)
    iz = iz.astype(np.int64)
    key = (iz - GRID_Z0) * GRID_NX + (ix - GRID_X0)
    if np.any(key < 0) or np.any(key >= GRID_N) or len(np.unique(key)) != GRID_N:
        return False, "grid cells do not cover the declared grid exactly once"

    r_ix, r_iz, r_alpha, r_beta, r_w = recompute_grid(y, n)
    r_key = (r_iz - GRID_Z0) * GRID_NX + (r_ix - GRID_X0)
    order = np.argsort(r_key)
    r_alpha = r_alpha[order]
    r_beta = r_beta[order]
    r_w = r_w[order]
    sub_order = np.argsort(key, kind="stable")
    s_alpha = vals["alpha"][sub_order]
    s_beta = vals["beta"][sub_order]
    s_w = vals["normed_exp_trans"][sub_order]

    d_a = np.abs(s_alpha - r_alpha)
    t_a = TOL_AB_REL * np.abs(r_alpha) + TOL_AB_ABS
    n_bad_a = int(np.sum(d_a > t_a))
    if n_bad_a:
        i = int(np.argmax(d_a - t_a))
        return False, (
            "alpha mismatch at %d of %d cells (worst relative difference "
            "%.3g exceeds %g)"
            % (n_bad_a, GRID_N, d_a[i] / max(abs(r_alpha[i]), 1e-300), TOL_AB_REL)
        )
    d_b = np.abs(s_beta - r_beta)
    t_b = TOL_AB_REL * np.abs(r_beta) + TOL_AB_ABS
    n_bad_b = int(np.sum(d_b > t_b))
    if n_bad_b:
        i = int(np.argmax(d_b - t_b))
        return False, (
            "beta mismatch at %d of %d cells (worst relative difference "
            "%.3g exceeds %g)"
            % (n_bad_b, GRID_N, d_b[i] / max(abs(r_beta[i]), 1e-300), TOL_AB_REL)
        )
    d_w = np.abs(s_w - r_w)
    t_w = TOL_W_REL * np.abs(r_w) + TOL_W_ABS
    n_bad_w = int(np.sum(d_w > t_w))
    if n_bad_w:
        i = int(np.argmax(d_w - t_w))
        return False, (
            "normed_exp_trans mismatch at %d of %d cells (worst relative "
            "difference %.3g exceeds %g)"
            % (n_bad_w, GRID_N, d_w[i] / max(abs(r_w[i]), 1e-300), TOL_W_REL)
        )
    wsum = float(vals["normed_exp_trans"].sum())
    if abs(wsum - 1.0) > TOL_SUM1:
        return False, "weights sum to %.17g, expected 1" % wsum
    return True, (
        "grid matches the deterministic recomputation (max relative "
        "differences: alpha %.2g, beta %.2g, weight %.2g)"
        % (
            float(np.max(d_a / np.abs(r_alpha))),
            float(np.max(d_b / np.abs(r_beta))),
            float(np.max(d_w / np.maximum(np.abs(r_w), 1e-300))),
        )
    )


def check_draws_structure(sub_dir):
    df, err = read_submission_csv(
        os.path.join(sub_dir, "pymc_ab_posterior_draws.csv"), EXPECTED_DRAWS_COLS
    )
    if err:
        return False, err
    total = 4 * DRAWS_PER_CHAIN
    if len(df) != total:
        return False, "expected %d data rows, found %d" % (total, len(df))
    alpha, err = numeric_column(df, "alpha")
    if err:
        return False, err
    beta, err = numeric_column(df, "beta")
    if err:
        return False, err
    if np.any(alpha <= 0) or np.any(beta <= 0):
        return False, "alpha/beta draws must be strictly positive"
    chain = pd.to_numeric(df["chain"], errors="coerce")
    draw = pd.to_numeric(df["draw"], errors="coerce")
    if chain.isna().any() or draw.isna().any():
        return False, "chain/draw labels contain missing values"
    chain = chain.to_numpy(dtype=np.int64)
    draw = draw.to_numpy(dtype=np.int64)
    labels = set(chain.tolist())
    if labels != set(CHAINS):
        return False, "chain labels are %s, expected exactly {1,2,3,4}" % (
            sorted(labels),
        )
    for c in CHAINS:
        d = draw[chain == c]
        if len(d) != DRAWS_PER_CHAIN:
            return (
                False,
                "chain %d has %d draws, expected %d"
                % (c, len(d), DRAWS_PER_CHAIN),
            )
        if len(np.unique(d)) != DRAWS_PER_CHAIN:
            return False, "chain %d draw labels are not 0..%d exactly once" % (
                c,
                DRAWS_PER_CHAIN - 1,
            )
    pairs = set(zip(alpha.tolist(), beta.tolist()))
    if len(pairs) != total:
        return (
            False,
            "%d duplicate (alpha, beta) rows among %d retained draws"
            % (total - len(pairs), total),
        )
    return (
        True,
        "structure ok: %d rows, chains 1-4 with draws 0..1999, positive values"
        % total,
    )


def check_draws_distribution(sub_dir, counts, exact):
    df, err = read_submission_csv(
        os.path.join(sub_dir, "pymc_ab_posterior_draws.csv"), EXPECTED_DRAWS_COLS
    )
    if err:
        return False, err
    total = 4 * DRAWS_PER_CHAIN
    if len(df) != total:
        return False, "expected %d data rows, found %d" % (total, len(df))
    alpha, err = numeric_column(df, "alpha")
    if err:
        return False, err
    beta, err = numeric_column(df, "beta")
    if err:
        return False, err
    chain = pd.to_numeric(df["chain"], errors="coerce").to_numpy(dtype=np.int64)
    problems = []
    ma = float(alpha.mean())
    mb = float(beta.mean())
    if abs(ma - exact["mean_alpha"]) > MEAN_REL * abs(exact["mean_alpha"]):
        problems.append(
            "mean alpha %.6g deviates from the exact posterior mean by %.3g "
            "(limit %g relative)"
            % (ma, abs(ma - exact["mean_alpha"]) / abs(exact["mean_alpha"]), MEAN_REL)
        )
    if abs(mb - exact["mean_beta"]) > MEAN_REL * abs(exact["mean_beta"]):
        problems.append(
            "mean beta %.6g deviates from the exact posterior mean by %.3g "
            "(limit %g relative)"
            % (mb, abs(mb - exact["mean_beta"]) / abs(exact["mean_beta"]), MEAN_REL)
        )
    sa = float(alpha.std(ddof=1))
    sb = float(beta.std(ddof=1))
    if abs(sa - exact["sd_alpha"]) > SD_REL * exact["sd_alpha"]:
        problems.append(
            "sd alpha %.6g deviates from the exact posterior sd by %.3g "
            "(limit %g relative)"
            % (sa, abs(sa - exact["sd_alpha"]) / exact["sd_alpha"], SD_REL)
        )
    if abs(sb - exact["sd_beta"]) > SD_REL * exact["sd_beta"]:
        problems.append(
            "sd beta %.6g deviates from the exact posterior sd by %.3g "
            "(limit %g relative)"
            % (sb, abs(sb - exact["sd_beta"]) / exact["sd_beta"], SD_REL)
        )
    if len(alpha) > 1:
        corr = float(np.corrcoef(alpha, beta)[0, 1])
        if abs(corr - exact["corr"]) > CORR_ABS:
            problems.append(
                "alpha-beta correlation %.4g deviates from the exact "
                "posterior correlation by %.3g (limit %g)"
                % (corr, abs(corr - exact["corr"]), CORR_ABS)
            )
    for c in CHAINS:
        ca = alpha[chain == c]
        if len(ca) == 0:
            problems.append("chain %d missing" % c)
            continue
        if abs(float(ca.mean()) - ma) > CHAIN_MEAN_SD * exact["sd_alpha"]:
            problems.append(
                "chain %d mean alpha deviates from the pooled mean by %.3g "
                "posterior sds (limit %g)"
                % (
                    c,
                    abs(float(ca.mean()) - ma) / exact["sd_alpha"],
                    CHAIN_MEAN_SD,
                )
            )
            break
    for c in CHAINS:
        cb = beta[chain == c]
        if len(cb) == 0:
            continue
        if abs(float(cb.mean()) - mb) > CHAIN_MEAN_SD * exact["sd_beta"]:
            problems.append(
                "chain %d mean beta deviates from the pooled mean by %.3g "
                "posterior sds (limit %g)"
                % (
                    c,
                    abs(float(cb.mean()) - mb) / exact["sd_beta"],
                    CHAIN_MEAN_SD,
                )
            )
            break
    if problems:
        return False, "; ".join(problems)
    return True, (
        "draw distribution consistent with the exact Part-2 posterior "
        "(mean alpha %.4g, mean beta %.4g, correlation %.3f)"
        % (ma, mb, float(np.corrcoef(alpha, beta)[0, 1]))
    )


def check_summary_structure(sub_dir):
    path = os.path.join(sub_dir, "posterior_mean_estimates.csv")
    if not os.path.isfile(path):
        return False, "file is missing"
    try:
        header = pd.read_csv(path, header=None, nrows=1).iloc[0].tolist()
    except Exception as exc:
        return False, "cannot parse CSV (%s)" % type(exc).__name__
    header = [str(c) for c in header]
    if header != SUMMARY_COLS:
        return False, "columns are %s, expected %s" % (header, SUMMARY_COLS)
    try:
        df = pd.read_csv(path, dtype=str)
    except Exception as exc:
        return False, "cannot parse CSV rows (%s)" % type(exc).__name__
    if len(df) != 4:
        return False, "expected 4 data rows, found %d" % len(df)
    for col in SUMMARY_COLS:
        if df[col].isna().any() or (df[col].astype(str).str.strip() == "").any():
            return False, "column %s contains missing values" % col
    labels = list(zip(df["method"], df["parameter"]))
    if len(set(labels)) != 4 or set(labels) != SUMMARY_LABELS:
        return (
            False,
            "labels are %s, expected the four (method, parameter) pairs once "
            "each" % (labels,),
        )
    est = pd.to_numeric(df["estimate"], errors="coerce").to_numpy(dtype=float)
    if not np.all(np.isfinite(est)):
        return False, "estimate column contains missing/nonfinite values"
    return True, "structure ok: 4 rows with the required method/parameter labels"


def check_summary_consistency(sub_dir):
    grid, gerr = read_submission_csv(
        os.path.join(sub_dir, "analytic_posterior_grid.csv"), EXPECTED_GRID_COLS
    )
    if gerr:
        return False, "analytic grid unavailable: %s" % gerr
    draws, derr = read_submission_csv(
        os.path.join(sub_dir, "pymc_ab_posterior_draws.csv"), EXPECTED_DRAWS_COLS
    )
    if derr:
        return False, "posterior draws unavailable: %s" % derr
    sdf, serr = read_submission_csv(
        os.path.join(sub_dir, "posterior_mean_estimates.csv"),
        SUMMARY_COLS,
    )
    if serr:
        return False, "summary unavailable: %s" % serr
    if len(sdf) != 4:
        return False, "expected 4 summary rows, found %d" % len(sdf)
    est = {}
    for _, row in sdf.iterrows():
        key = (str(row["method"]), str(row["parameter"]))
        if key not in SUMMARY_LABELS:
            return False, "unexpected summary label %s" % (key,)
        if key in est:
            return False, "duplicate summary label %s" % (key,)
        try:
            val = float(row["estimate"])
        except (TypeError, ValueError):
            return False, "estimate for %s is not numeric" % (key,)
        if not math.isfinite(val):
            return False, "estimate for %s is not finite" % (key,)
        est[key] = val

    a, err = numeric_column(grid, "alpha")
    if err:
        return False, "grid alpha: %s" % err
    b, err = numeric_column(grid, "beta")
    if err:
        return False, "grid beta: %s" % err
    w, err = numeric_column(grid, "normed_exp_trans")
    if err:
        return False, "grid weight: %s" % err
    grid_mean_a = float((a * w).sum())
    grid_mean_b = float((b * w).sum())

    da, err = numeric_column(draws, "alpha")
    if err:
        return False, "draws alpha: %s" % err
    db, err = numeric_column(draws, "beta")
    if err:
        return False, "draws beta: %s" % err
    draws_mean_a = float(da.mean())
    draws_mean_b = float(db.mean())

    problems = []
    for key, value, ref in (
        (("analytic_grid", "alpha"), est[("analytic_grid", "alpha")], grid_mean_a),
        (("analytic_grid", "beta"), est[("analytic_grid", "beta")], grid_mean_b),
        (("pymc_mcmc", "alpha"), est[("pymc_mcmc", "alpha")], draws_mean_a),
        (("pymc_mcmc", "beta"), est[("pymc_mcmc", "beta")], draws_mean_b),
    ):
        tol_rel = TOL_AN_REL if key[0] == "analytic_grid" else TOL_MC_REL
        tol_abs = TOL_AN_ABS if key[0] == "analytic_grid" else TOL_MC_ABS
        if abs(value - ref) > tol_rel * abs(ref) + tol_abs:
            problems.append(
                "%s/%s estimate %.10g does not match the value derived from "
                "the submitted %s (%.10g)"
                % (key[0], key[1], value, "grid" if key[0] == "analytic_grid"
                   else "draws", ref)
            )
    if problems:
        return False, "; ".join(problems)
    return True, (
        "summary estimates reproduce the submitted grid and draw means "
        "within tolerance"
    )


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    sub = args.submission_dir
    checks = []

    def run(check_id, kind, fn, *fn_args):
        try:
            ok, msg = fn(*fn_args)
        except Exception as exc:  # defensive: never crash the verification
            ok, msg = False, "check could not be evaluated (%s: %s)" % (
                type(exc).__name__,
                exc,
            )
        checks.append({"id": check_id, "kind": kind, "passed": bool(ok),
                       "message": str(msg)})

    run("analytic_grid_structure", "structural", check_grid_structure, sub)

    counts, counts_err = load_counts()
    if counts_err is None:
        run("analytic_grid_values", "scientific", check_grid_values, sub, counts)
        exact = compute_exact_part2(counts[0], counts[1])
        run("mcmc_draws_distribution", "scientific",
            check_draws_distribution, sub, counts, exact)
    else:
        run(
            "analytic_grid_values",
            "scientific",
            lambda s: (False, "original counts input unavailable: %s"
                       % counts_err),
            sub,
        )
        run(
            "mcmc_draws_distribution",
            "scientific",
            lambda s: (False, "original counts input unavailable: %s"
                       % counts_err),
            sub,
        )

    run("mcmc_draws_structure", "structural", check_draws_structure, sub)
    run("summary_estimates_structure", "structural", check_summary_structure, sub)
    run("summary_estimates_consistency", "scientific",
        check_summary_consistency, sub)

    report = {"passed": all(c["passed"] for c in checks), "checks": [
        {"id": c["id"], "passed": c["passed"], "message": c["message"]}
        for c in checks
    ]}
    with open(args.report, "w") as fh:
        json.dump(report, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

