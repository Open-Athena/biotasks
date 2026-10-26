"""Read-only reserved-worker compatibility and headroom diagnosis."""
import json
from collections import Counter
from pathlib import Path
from biotasks.validation import iris_client
root=Path(__file__).resolve().parent
val=root/'inputs-private/run-002/nibabel-handoff/validation';plan=json.loads((val/'plan.json').read_text())
group=next(g for g in plan['tasks'] if g['task']['task']=='nipy__nibabel-1291')
receipt=json.loads((val/'runs'/group['id']/'submission.json').read_text());target=receipt['worker_id']
assert iris_client.fingerprint()==plan['client_profile']
with iris_client.connect(plan['backend']['config']) as client:
    workers=client.list_workers(query=iris_client.module('iris.rpc.controller_pb2').Controller.WorkerQuery(limit=500))
    reserved=[w for w in workers if 'v4-reserved' in w.scale_group]
    names=iris_client.module('iris.cluster.types').JobName
    match=[w for w in reserved if w.worker_id==target]
    rows=[]
    for w in match:
        allocations=[client.describe_task(names.from_string(t)).resources for t in w.running_job_ids]
        rows.append({'worker_id':w.worker_id,'healthy':w.healthy,'dirty':w.metadata.provenance.dirty,
                     'base_commit':w.metadata.provenance.base_commit,'tpu_name':w.metadata.tpu_name,
                     'running_jobs':len(allocations),'available_cpu':(w.metadata.cpu_count*1000-sum(r.cpu_millicores for r in allocations))/1000,
                     'available_memory_gib':(w.metadata.memory_bytes-sum(r.memory_bytes for r in allocations))/1024**3,
                     'available_disk_gib':(w.metadata.disk_bytes-sum(r.disk_bytes for r in allocations))/1024**3})
    out={'target':rows,'healthy_reserved_by_base':dict(Counter(w.metadata.provenance.base_commit for w in reserved if w.healthy)),'read_only':True,'jobs_submitted':0}
    (root/'worker-compatibility-20261026.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
