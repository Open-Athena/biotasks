"""Pinned SAMtools result helpers on synthetic outcomes, not biological execution."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parent
source=ROOT/'inputs-private/samtools-1605-test.pl'
text=source.read_text();make=(ROOT/'inputs-private/samtools-1605-Makefile').read_text()
helpers=text[text.index('sub failed\n'):text.index('sub is_file_newer\n')]
summary=text[text.index('print "\\nNumber of tests:'):text.index('#--------------------',text.index('print "\\nNumber of tests:'))]
assert 'sub passed\n' in helpers and 'exit (' in summary
# Use the original counter/report functions. Synthetic labels and commands simulate
# two distinct invocations inside one test_sort function; no samtools binary runs.
program='use strict; use warnings; use IO::Handle;\n'+helpers+'''
my $opts = {nok=>0,nfailed=>0,nxfail=>0,nxpass=>0};
print "test_sort:\\n\\tsamtools sort fixture-a\\n";
failed($opts, reason=>"synthetic failure");
print "test_sort:\\n\\tsamtools sort -@ 2 fixture-b\\n";
passed($opts);
print "test_expected:\\n\\tsamtools fixture-c\\n";
failed($opts, expect_fail=>1);
print "test_unexpected:\\n\\tsamtools fixture-d\\n";
passed($opts, expect_fail=>1);
'''+summary
result=subprocess.run(['perl','-'],input=program,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5)
assert result.returncode==1
log=result.stdout
assert log.count('test_sort:\n')==2 and '.. failed ...' in log and '.. ok' in log
assert '.. expected failure' in log and '.. unexpected pass' in log
for label,value in [('total',4),('passed',1),('failed',1),('expected failure',1),('unexpected pass',1)]:
    assert re.search(r'^\s*'+label+r'\s+\.\. '+str(value)+r'$',log,re.M)
node=next(n for n in ast.parse((ROOT/'upstream/log_parsers/__init__.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_detect_runner')
ns={'re':re};exec(compile(ast.Module(body=[node],type_ignores=[]),'pinned_runner_detection','exec'),ns)
detection={cmd:ns['_detect_runner']([cmd]) for cmd in ['make test','make check','perl test/test.pl','test/test.pl --exec bgzip=bgzip']}
assert set(detection.values())=={'unknown'}
assert 'test_sort($opts);' in text and 'test_sort($opts, threads=>2);' in text
assert 'REF_PATH=: test/test.pl' in make and '../regression.sh' in make and 'test/split/test_count_rg' in make
(ROOT/'samtools-contract-fixture.log').write_text(log)
out={'scope':'Actual pinned passed/failed/summary Perl helpers on four synthetic outcomes; no repository builds or biological tests',
     'repo':'samtools/samtools','pr':1605,'head':'735c9c39fcffc22bc4085f5071bbb9cab70d16bd',
     'source_files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [source,ROOT/'inputs-private/samtools-1605-Makefile']},
     'helpers_sha256':hashlib.sha256(helpers.encode()).hexdigest(),'summary_sha256':hashlib.sha256(summary.encode()).hexdigest(),
     'synthetic_runner_exit':result.returncode,'synthetic_counts':{'total':4,'passed':1,'failed':1,'expected_failure':1,'unexpected_pass':1},
     'repeated_label':'test_sort','repeated_label_count':2,'pinned_runner_detection':detection,
     'log_sha256':hashlib.sha256(log.encode()).hexdigest(),'model_calls':0,'remote_jobs':0,
     'limits':['Not full test.pl execution','Repeated-label fixture illustrates source-level identity ambiguity, not a live lost-test count','No parser/recognizer modification or task yield claim']}
(ROOT/'samtools-contract-results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
