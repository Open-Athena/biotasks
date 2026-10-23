import os

os.makedirs("/work/outputs", exist_ok=True)

with open("/work/outputs/LuxC.hmm", "wb") as _export_hmm_file:
    hmm.write(_export_hmm_file)

with open("/work/outputs/LuxC.domtbl", "wb") as _export_hits_file:
    hits.write(_export_hits_file, format="domains")
