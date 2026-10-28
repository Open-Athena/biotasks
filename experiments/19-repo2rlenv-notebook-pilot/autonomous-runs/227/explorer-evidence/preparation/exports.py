import os

_export_output_dir = "/work/outputs"
os.makedirs(_export_output_dir, exist_ok=True)

with open(os.path.join(_export_output_dir, "LuxC.hmm"), "wb") as _export_file:
    hmm.write(_export_file)

with open(os.path.join(_export_output_dir, "LuxC.domtbl"), "wb") as _export_file:
    hits.write(_export_file, format="domains")
