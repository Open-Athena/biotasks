import os as _export_os
import pandas as _export_pd

_export_dir = "/work/outputs"
_export_os.makedirs(_export_dir, exist_ok=True)


def _format_knockout_ids(knockout_ids):
    if isinstance(knockout_ids, (set, frozenset, list, tuple)):
        return ";".join(sorted(str(identifier) for identifier in knockout_ids))
    return str(knockout_ids)


def _write_deletion_results(frame, filename):
    export_frame = frame.copy()
    if "ids" in export_frame.columns:
        labels = [
            _format_knockout_ids(value)
            for value in export_frame["ids"].tolist()
        ]
        export_frame = export_frame.drop(columns="ids")
    else:
        labels = [
            _format_knockout_ids(value)
            for value in export_frame.index.tolist()
        ]
    export_frame.index = _export_pd.Index(labels, name="knockouts")
    export_frame.to_csv(_export_os.path.join(_export_dir, filename))


_write_deletion_results(deletion_results, "single_gene_deletions.csv")
_write_deletion_results(single, "single_reaction_deletions.csv")
_write_deletion_results(double, "double_reaction_deletions.csv")