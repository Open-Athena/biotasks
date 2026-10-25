import os

_export_dir = "/work/outputs"
os.makedirs(_export_dir, exist_ok=True)

with open(os.path.join(_export_dir, "LuxC.hmm"), "wb") as _hmm_export_file:
    hmm.write(_hmm_export_file)

with open(os.path.join(_export_dir, "LuxC.domtbl"), "wb") as _domtbl_export_file:
    hits.write(_domtbl_export_file, format="domains")