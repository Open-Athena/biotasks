import importlib.util,json,tempfile,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("proposed_profile", sys.argv[1]);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory(prefix="biotasks19-profile-regression-") as folder:
 path=Path(folder)/"generic.csv";total=1_000_001
 with path.open("w") as stream:
  stream.write("value,tag\n")
  for i in range(total):stream.write(str(i%7)+",a\n")
 result=mod.csv_profile(path,distinct_limit=3)
 assert result["row_count"]==total and result["ragged_rows"]==0
 numeric=result["columns"][0];assert numeric["finite_numeric"]==total and numeric["minimum"]==0 and numeric["maximum"]==6
 assert numeric["distinct_capped"] is True and numeric["distinct_nonempty"]==3
 assert result["columns"][1]["other"]==total
 print(json.dumps({"synthetic_rows":total,"streaming_profile_passed":True,"biological_data_used":False}))
