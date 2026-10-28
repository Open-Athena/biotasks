import argparse
import math
import os


def _format_growth(value):
    if value is None:
        return ""
    value = float(value)
    if math.isnan(value):
        return ""
    return repr(value)


def _format_knockouts(ids):
    return ";".join(sorted(str(identifier) for identifier in ids))


def _frame_rows(frame):
    if "ids" in frame.columns:
        ids_series = frame["ids"].tolist()
    else:
        ids_series = frame.index.tolist()
    growth_series = frame["growth"].tolist()
    status_series = frame["status"].tolist()
    rows = []
    for ids, growth, status in zip(ids_series, growth_series, status_series):
        rows.append(
            (_format_knockouts(ids), _format_growth(growth), str(status))
        )
    rows.sort(key=lambda row: row[0])
    return rows


def _write_csv(path, header, rows):
    with open(path, "w", newline="") as handle:
        handle.write(header + "\n")
        for row in rows:
            handle.write(",".join(row) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    from cobra.io import read_sbml_model
    from cobra.flux_analysis import (
        single_gene_deletion,
        single_reaction_deletion,
        double_reaction_deletion,
    )

    model = read_sbml_model(os.path.join(args.input_dir, "e_coli_core.xml"))
    os.makedirs(args.output_dir, exist_ok=True)

    gene_frame = single_gene_deletion(model)
    reaction_frame = single_reaction_deletion(model)
    double_frame = double_reaction_deletion(model)

    header = "knockouts,growth,status"
    _write_csv(
        os.path.join(args.output_dir, "single_gene_deletions.csv"),
        header,
        _frame_rows(gene_frame),
    )
    _write_csv(
        os.path.join(args.output_dir, "single_reaction_deletions.csv"),
        header,
        _frame_rows(reaction_frame),
    )
    _write_csv(
        os.path.join(args.output_dir, "double_reaction_deletions.csv"),
        header,
        _frame_rows(double_frame),
    )

    # Phosphofructokinase redundancy scenarios, mirroring the defined semantics:
    # wild type, PFK reaction knockout, pfkA gene knockout, and the
    # simultaneous pfkA + pfkB double gene knockout (sequential knockouts of
    # both genes on the same model within one context).
    rows = []
    solution = model.optimize()
    rows.append(("", _format_growth(solution.objective_value), solution.status))
    with model:
        model.reactions.PFK.knock_out()
        solution = model.optimize()
        rows.append(("PFK", _format_growth(solution.objective_value), solution.status))
    with model:
        model.genes.b1723.knock_out()
        solution = model.optimize()
        rows.append(("b1723", _format_growth(solution.objective_value), solution.status))
        model.genes.b3916.knock_out()
        solution = model.optimize()
        rows.append(
            ("b1723;b3916", _format_growth(solution.objective_value), solution.status)
        )
    _write_csv(os.path.join(args.output_dir, "pfk_knockout_optima.csv"), header, rows)


if __name__ == "__main__":
    main()

