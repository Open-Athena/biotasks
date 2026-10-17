import hashlib,json,random
from pathlib import Path
from repo2rlenv.pipelines.recipes.terminal.runner import load_seeds
root=Path('experiments/21-repo2rlenv/seeds/seta-genomic-intervals')
manifest=json.loads((root/'manifest.json').read_text());seeds=load_seeds(root/'seeds.json')
assert len(seeds)==3 and len({x['id'] for x in seeds})==3
assert hashlib.sha256((root/'seeds.json').read_bytes()).hexdigest()==manifest['seed_file_sha256']
assert {x['id']:hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest() for x in seeds}==manifest['native_seed_sha256']
# Independent bounded coordinate arithmetic for the examples, not bedtools execution.
target=set(range(10,20));covered=set().union(*(set(range(a,b)) for a,b in [(8,13),(12,17),(19,22)]))
assert len(target & covered)==8
query=(10,15);gap=lambda feature:max(0,feature[0]-query[1],query[0]-feature[1])
assert [gap(x) for x in [(0,8),(17,20),(15,16)]]==[2,2,0]
replicates=[set(range(0,10)),set(range(5,15)),set(range(8,12))]
consensus={x for x in range(20) if sum(x in r for r in replicates)>=2}
assert consensus==set(range(5,12))
random.Random(24).shuffle(seeds)
result={'stage':'native_seed_loading_and_example_arithmetic','loaded_count':len(seeds),'native_seed24_order':[x['id'] for x in seeds],'seed_hashes_verified':True,'example_arithmetic':{'union_covered_bases':8,'nearest_gap_distances':[2,2,0],'consensus_half_open':[5,12]},'bedtools_executed':False,'model_calls':0,'remote_workers':0,'generated_tasks':0}
(root/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
manifest['pending'].remove('native loader check');manifest['stage']='native_loaded_inputs_generation_pending';(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(result))
