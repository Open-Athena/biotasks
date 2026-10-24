#!/usr/bin/env python3
"""Acceptance grader for the rat-tumor hierarchical Bayes task.

Compares parsed scientific content of the three declared outputs against the
reference. Row order in the grid CSV is free; rows are identified by their
nominal (X, Z) grid coordinates (rounded to the nearest 0.01).

Usage:
    python grade.py --reference-dir PATH --submission-dir PATH --report PATH
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

GRID_FILE = "analytic_marginal_posterior_grid.csv"
SUMMARY_FILE = "analytic_summary.json"
MCMC_FILE = "mcmc_posterior_means.json"

GRID_COLUMNS = ["X", "Z", "alpha", "beta", "normed_exp_trans"]

REL_TOL_ALPHA_BETA = 1e-9      # per-cell back-transformed parameters
REL_TOL_WEIGHT = 1e-8          # per-cell normalized posterior weights
WEIGHT_SUM_TOL = 1e-9          # |sum(w) - 1|
REL_TOL_MEANS = 1e-7           # analytic_summary mean_alpha / mean_beta
MODE_CELL_TOL = 0.005          # half a grid step: identifies the mode cell
REL_TOL_MCMC = 0.10            # Monte-Carlo window for pooled MCMC means
CONFIG_TOL = 1e-9              # target_accept exactness window

_CHECK_IDS = [
    "grid_structure",
    "grid_alpha_beta",
    "grid_weights",
    "analytic_summary_schema",
    "analytic_means",
    "analytic_mode",
    "mcmc_config",
    "mcmc_means",
]

# Required nominal grid: 100 x-values and 400 z-values in steps of 0.01
# with half-open semantics (endpoints -1.30 and 5.00 excluded).
_X_MIN, _X_MAX, _Z_MIN, _Z_MAX = -230, -131, 100, 499


class Fail(Exception):
    pass


# ---------------------------------------------------------------- loading

def read_json_file(path):
    if not os.path.isfile(path):
        raise Fail("file is missing")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Fail:
        raise
    except Exception as exc:
        raise Fail("file is not valid JSON: %s" % exc)


def read_grid(path):
    """Return (DataFrame, canonical_key_list) or raise Fail."""
    if not os.path.isfile(path):
        raise Fail("file is missing")
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception as exc:
        raise Fail("file is not a parseable CSV: %s" % exc)
    if list(df.columns) != GRID_COLUMNS:
        raise Fail("header must be exactly %s (in this order); got %s"
                   % (",".join(GRID_COLUMNS), list(df.columns)))
    if len(df) == 0:
        raise Fail("CSV contains no data rows")
    for col in GRID_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[col]):
            try:
                df[col] = df[col].astype(float)
            except Exception:
                raise Fail("column %r contains non-numeric values" % col)
    vals = df[GRID_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(vals).all():
        raise Fail("CSV contains missing or non-finite values")
    if np.any(vals[:, 2] <= 0) or np.any(vals[:, 3] <= 0) or np.any(vals[:, 4] <= 0):
        raise Fail("alpha, beta and normed_exp_trans must be strictly positive")
    # canonical nominal grid coordinates: round to nearest 0.01
    cx = np.rint(df["X"].to_numpy(dtype=float) * 100.0).astype(np.int64)
    cz = np.rint(df["Z"].to_numpy(dtype=float) * 100.0).astype(np.int64)
    keys = list(zip(cx.tolist(), cz.tolist()))
    return df, keys


def canonical_set(keys):
    return set(keys)


def as_number(obj, name):
    """Finite JSON number (bools are not numbers)."""
    if isinstance(obj, bool) or not isinstance(obj, (int, float)):
        raise Fail("%s must be a JSON number" % name)
    v = float(obj)
    if not math.isfinite(v):
        raise Fail("%s must be finite" % name)
    return v


def rel_err(sub, ref):
    denom = abs(ref) if ref != 0 else float(np.finfo(float).tiny)
    return abs(sub - ref) / denom


# ---------------------------------------------------------------- checks

_shared = {}


def load_both_grids(ref_dir, sub_dir):
    if "grid" not in _shared:
        rdf, rkeys = read_grid(os.path.join(ref_dir, GRID_FILE))
        rset = canonical_set(rkeys)
        if len(rkeys) != len(rset):
            raise Fail("reference grid has duplicate cells (internal)")
        try:
            sdf, skeys = read_grid(os.path.join(sub_dir, GRID_FILE))
        except Fail as exc:
            sdf, skeys, serr = None, None, str(exc)
        else:
            serr = None
        _shared["grid"] = (rdf, rkeys, rset, sdf, skeys, serr)
    return _shared["grid"]


def check_grid_structure(ref_dir, sub_dir):
    try:
        rdf, rkeys, rset, sdf, skeys, serr = load_both_grids(ref_dir, sub_dir)
    except Fail as exc:
        return False, "reference grid could not be read (%s)" % exc
    if sdf is None:
        return False, "submission grid CSV rejected: %s" % serr
    sset = canonical_set(skeys)
    if len(skeys) != len(sset):
        return False, ("grid has duplicate (X, Z) cells: %d rows map to %d "
                      "distinct cells" % (len(skeys), len(sset)))
    cx = [k[0] for k in skeys]
    cz = [k[1] for k in skeys]
    if min(cx) < _X_MIN or max(cx) > _X_MAX or min(cz) < _Z_MIN or max(cz) > _Z_MAX:
        return False, ("grid coordinates fall outside the required ranges "
                      "(nominal x in [-2.30, -1.31], z in [1.00, 4.99])")
    if sset != rset:
        missing = len(rset - sset)
        extra = len(sset - rset)
        return False, ("grid cell coverage mismatch: %d cells missing from the "
                       "required 100x400 nominal grid, %d unexpected cells"
                       % (missing, extra))
    return True, ("header, %d rows, full 100x400 nominal cell coverage with no "
                  "duplicates; all values finite and positive"
                  % len(skeys))


def _cell_maps(sdf, skeys, rdf, rkeys):
    """Align submission and reference rows by canonical cell."""
    ridx = {}
    for i, k in enumerate(rkeys):
        ridx[k] = i
    sub_alpha = np.full(len(rkeys), np.nan)
    sub_beta = np.full(len(rkeys), np.nan)
    sub_w = np.full(len(rkeys), np.nan)
    sa = sdf["alpha"].to_numpy(dtype=float)
    sb = sdf["beta"].to_numpy(dtype=float)
    sw = sdf["normed_exp_trans"].to_numpy(dtype=float)
    for j, k in enumerate(skeys):
        i = ridx[k]
        sub_alpha[i] = sa[j]
        sub_beta[i] = sb[j]
        sub_w[i] = sw[j]
    return sub_alpha, sub_beta, sub_w


def check_grid_alpha_beta(ref_dir, sub_dir):
    rdf, rkeys, rset, sdf, skeys, serr = load_both_grids(ref_dir, sub_dir)
    if sdf is None:
        return False, "grid values cannot be compared: %s" % serr
    if canonical_set(skeys) != rset or len(skeys) != len(rset):
        return False, "grid cells do not cover the required grid exactly once"
    sub_a, sub_b, _ = _cell_maps(sdf, skeys, rdf, rkeys)
    ref_a = rdf["alpha"].to_numpy(dtype=float)
    ref_b = rdf["beta"].to_numpy(dtype=float)
    ea = np.max(np.abs(sub_a - ref_a) / np.maximum(np.abs(ref_a),
                                                   np.finfo(float).tiny))
    eb = np.max(np.abs(sub_b - ref_b) / np.maximum(np.abs(ref_b),
                                                    np.finfo(float).tiny))
    ok = bool(ea <= REL_TOL_ALPHA_BETA and eb <= REL_TOL_ALPHA_BETA)
    return ok, ("max relative deviation from reference: alpha %.3e, beta %.3e "
                "(tolerance %.1e)" % (ea, eb, REL_TOL_ALPHA_BETA))


def check_grid_weights(ref_dir, sub_dir):
    rdf, rkeys, rset, sdf, skeys, serr = load_both_grids(ref_dir, sub_dir)
    if sdf is None:
        return False, "grid weights cannot be compared: %s" % serr
    if canonical_set(skeys) != rset or len(skeys) != len(rset):
        return False, "grid cells do not cover the required grid exactly once"
    _, _, sub_w = _cell_maps(sdf, skeys, rdf, rkeys)
    ref_w = rdf["normed_exp_trans"].to_numpy(dtype=float)
    ew = np.max(np.abs(sub_w - ref_w) / np.maximum(np.abs(ref_w),
                                                   np.finfo(float).tiny))
    total = float(np.sum(sdf["normed_exp_trans"].to_numpy(dtype=float)))
    sum_ok = abs(total - 1.0) <= WEIGHT_SUM_TOL
    ok = bool(ew <= REL_TOL_WEIGHT and sum_ok)
    return ok, ("max relative deviation of normed_exp_trans: %.3e (tolerance "
                "%.1e); weights sum to %.15f (must be 1 within %.1e)"
                % (ew, REL_TOL_WEIGHT, total, WEIGHT_SUM_TOL))


def _summary_objects(ref_dir, sub_dir):
    if "summary" not in _shared:
        robj = read_json_file(os.path.join(ref_dir, SUMMARY_FILE))
        if not isinstance(robj, dict):
            raise Fail("reference summary is not a JSON object")
        try:
            sobj = read_json_file(os.path.join(sub_dir, SUMMARY_FILE))
        except Fail as exc:
            sobj, serr = None, str(exc)
        else:
            serr = None
        _shared["summary"] = (robj, sobj, serr)
    return _shared["summary"]


def check_summary_schema(ref_dir, sub_dir):
    try:
        robj, sobj, serr = _summary_objects(ref_dir, sub_dir)
    except Fail as exc:
        return False, "reference summary could not be read (%s)" % exc
    if sobj is None:
        return False, "submission summary JSON rejected: %s" % serr
    if not isinstance(sobj, dict):
        return False, "analytic_summary.json must be a JSON object"
    required = {"mean_alpha", "mean_beta", "mode_x", "mode_z"}
    keys = set(sobj.keys())
    if keys != required:
        return False, ("keys must be exactly %s; got %s (missing: %s, extra: %s)"
                       % (sorted(required), sorted(keys),
                          sorted(required - keys), sorted(keys - required)))
    for k in sorted(required):
        try:
            as_number(sobj[k], k)
        except Fail as exc:
            return False, str(exc)
    return True, "exact key set with four finite numeric values"


def check_analytic_means(ref_dir, sub_dir):
    try:
        robj, sobj, serr = _summary_objects(ref_dir, sub_dir)
    except Fail as exc:
        return False, "reference summary could not be read (%s)" % exc
    if sobj is None or not isinstance(sobj, dict):
        return False, "analytic means cannot be compared: no valid summary JSON"
    msgs = []
    ok = True
    for key in ("mean_alpha", "mean_beta"):
        if key not in sobj or key not in robj:
            return False, "missing key %s" % key
        try:
            sub = as_number(sobj[key], key)
            ref = as_number(robj[key], key)
        except Fail as exc:
            return False, str(exc)
        e = rel_err(sub, ref)
        good = e <= REL_TOL_MEANS
        ok = ok and good
        msgs.append("%s: relative deviation %.3e (tolerance %.1e)"
                    % (key, e, REL_TOL_MEANS))
    return ok, "; ".join(msgs)


def check_analytic_mode(ref_dir, sub_dir):
    try:
        robj, sobj, serr = _summary_objects(ref_dir, sub_dir)
    except Fail as exc:
        return False, "reference summary could not be read (%s)" % exc
    if sobj is None:
        return False, "mode cannot be compared: %s" % serr
    if not isinstance(sobj, dict):
        return False, "mode check requires a JSON object summary"
    for key in ("mode_x", "mode_z"):
        if key not in sobj or key not in robj:
            return False, "missing key %s" % key
    try:
        sx = as_number(sobj["mode_x"], "mode_x")
        sz = as_number(sobj["mode_z"], "mode_z")
        rx = as_number(robj["mode_x"], "mode_x")
        rz = as_number(robj["mode_z"], "mode_z")
    except Fail as exc:
        return False, str(exc)
    dx, dz = abs(sx - rx), abs(sz - rz)
    same_cell = dx <= MODE_CELL_TOL and dz <= MODE_CELL_TOL
    if not same_cell:
        return False, ("mode cell (%.6f, %.6f) does not match the reference "
                       "mode cell (%.6f, %.6f); deviations (%.2e, %.2e) exceed "
                       "half a grid step %.3f"
                       % (sx, sz, rx, rz, dx, dz, MODE_CELL_TOL))
    # the reported mode must be a coordinate appearing in the submission grid
    try:
        _, _, _, sdf, skeys, _ = load_both_grids(ref_dir, sub_dir)
    except Fail as exc:
        return False, "reference grid could not be read (%s)" % exc
    if sdf is None:
        return False, "mode cannot be verified against the submission grid: %s" % serr
    kx = int(round(sx * 100.0))
    kz = int(round(sz * 100.0))
    if (kx, kz) not in canonical_set(skeys):
        return False, ("reported mode (%.6f, %.6f) is not a grid coordinate "
                       "present in the submission's Output 1" % (sx, sz))
    return True, ("mode identifies the reference mode cell "
                  "(within half a 0.01 step) and appears in Output 1")


def _mcmc_objects(ref_dir, sub_dir):
    if "mcmc" not in _shared:
        robj = read_json_file(os.path.join(ref_dir, MCMC_FILE))
        if not isinstance(robj, dict):
            raise Fail("reference MCMC summary is not a JSON object")
        try:
            sobj = read_json_file(os.path.join(sub_dir, MCMC_FILE))
        except Fail as exc:
            sobj, serr = None, str(exc)
        else:
            serr = None
        _shared["mcmc"] = (robj, sobj, serr)
    return _shared["mcmc"]


def check_mcmc_config(ref_dir, sub_dir):
    try:
        robj, sobj, serr = _mcmc_objects(ref_dir, sub_dir)
    except Fail as exc:
        return False, "reference MCMC summary could not be read (%s)" % exc
    if sobj is None:
        return False, "mcmc_posterior_means.json rejected: %s" % serr
    if not isinstance(sobj, dict):
        return False, "mcmc_posterior_means.json must be a JSON object"
    required = {"mean_alpha", "mean_beta", "n_chains", "draws_per_chain",
                "target_accept", "sampler"}
    keys = set(sobj.keys())
    if keys != required:
        return False, ("keys must be exactly %s; got %s (missing: %s, extra: %s)"
                       % (sorted(required), sorted(keys),
                          sorted(required - keys), sorted(keys - required)))
    # fixed sampling configuration
    for key, expected in (("n_chains", 2), ("draws_per_chain", 2000)):
        v = sobj[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != expected:
            return False, "%s must equal %s (got %r)" % (key, expected, v)
    ta = sobj["target_accept"]
    if isinstance(ta, bool) or not isinstance(ta, (int, float)) \
            or abs(float(ta) - 0.95) > CONFIG_TOL:
        return False, "target_accept must be 0.95 (got %r)" % (ta,)
    smp = sobj["sampler"]
    if not isinstance(smp, str) or not smp.strip():
        return False, "sampler must be a non-empty string (got %r)" % (smp,)
    for key in ("mean_alpha", "mean_beta"):
        try:
            as_number(sobj[key], key)
        except Fail as exc:
            return False, str(exc)
    return True, ("exact key set; n_chains=2, draws_per_chain=2000, "
                  "target_accept=0.95, sampler recorded as a non-empty string")


def check_mcmc_means(ref_dir, sub_dir):
    try:
        robj, sobj, serr = _mcmc_objects(ref_dir, sub_dir)
    except Fail as exc:
        return False, "reference MCMC summary could not be read (%s)" % exc
    if sobj is None or not isinstance(sobj, dict):
        return False, "MCMC means cannot be compared: no valid summary JSON"
    msgs = []
    ok = True
    for key in ("mean_alpha", "mean_beta"):
        if key not in sobj or key not in robj:
            return False, "missing key %s" % key
        try:
            sub = as_number(sobj[key], key)
            ref = as_number(robj[key], key)
        except Fail as exc:
            return False, str(exc)
        e = rel_err(sub, ref)
        good = e <= REL_TOL_MCMC
        ok = ok and good
        msgs.append("%s: relative deviation %.4f (tolerance %.2f)"
                    % (key, e, REL_TOL_MCMC))
    return ok, "; ".join(msgs)


CHECK_FUNCS = {
    "grid_structure": check_grid_structure,
    "grid_alpha_beta": check_grid_alpha_beta,
    "grid_weights": check_grid_weights,
    "analytic_summary_schema": check_summary_schema,
    "analytic_means": check_analytic_means,
    "analytic_mode": check_analytic_mode,
    "mcmc_config": check_mcmc_config,
    "mcmc_means": check_mcmc_means,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    results = []
    for cid in _CHECK_IDS:
        try:
            ok, msg = CHECK_FUNCS[cid](args.reference_dir, args.submission_dir)
        except Exception as exc:  # never crash on malformed submissions
            ok, msg = False, "check could not be completed: %s" % exc
        results.append({"id": cid, "passed": bool(ok), "message": str(msg)})

    report = {"passed": all(r["passed"] for r in results), "checks": results}
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

