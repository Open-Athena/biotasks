import os as _export_os
import pandas as _export_pd

_export_dir = "/work/outputs"
_export_os.makedirs(_export_dir, exist_ok=True)


def _write_deletion_results(frame, filename):
    export_frame = frame.copy()
    export_frame.index = _export_pd.Index(
        [";".join(sorted(str(identifier) for identifier in knockout_ids))
         for knockout_ids in export_frame.index],
        name="knockouts",
    )
    export_frame.to_csv(_export_os.path.join(_export_dir, filename))


_write_deletion_results(deletion_results, "single_gene_deletions.csv")
_write_deletion_results(single, "single_reaction_deletions.csv")
_write_deletion_results(double, "double_reaction_deletions.csv")