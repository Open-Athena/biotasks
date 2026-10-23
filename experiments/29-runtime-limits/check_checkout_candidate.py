"""Check timeout/config plumbing against exact upstream clone AST, no network."""
import ast
import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Literal
from collections.abc import Callable
from pydantic import BaseModel, Field, ValidationError
from replay_scanpy import load_functions

ROOT=Path(__file__).resolve().parent
REF='5edf83948816aee51225949dd0e613bd40f69c47'
class MissingDestination:
    def exists(self):return False
    def __str__(self):return '/fixture/OpenMS'

def exercise(path, timeout=None, fail_checkout=False):
    calls=[]
    def run(args, **kwargs):
        calls.append({'args':args,'timeout':kwargs['timeout']})
        code=1 if '--branch' in args else (2 if 'checkout' in args and fail_checkout else 0)
        return SimpleNamespace(returncode=code,stdout='',stderr='fixture failure' if code else '')
    namespace={'subprocess':SimpleNamespace(run=run),'logger':logging.getLogger('checkout-check'),
               'Callable':Callable,'Path':Path,'auth_clone_url':lambda url,token:url}
    load_functions(path,{'BootstrapError','_scrub_token','_run_git_streaming','_shallow_clone_at_ref'},namespace)
    kwargs={} if timeout is None else {'checkout_timeout':timeout}
    error=None
    try:namespace['_shallow_clone_at_ref']('https://github.com/OpenMS/OpenMS.git',REF,None,MissingDestination(),**kwargs)
    except namespace['BootstrapError'] as exc:error=str(exc)
    return calls,error

original,error=exercise(ROOT/'upstream/bootstrap/runner.py')
assert not error and [c['timeout'] for c in original]==[300,300,120,60]
default,error=exercise(ROOT/'candidate-checkout/runner.py')
assert not error and default==original
increased,error=exercise(ROOT/'candidate-checkout/runner.py',300)
assert not error and [c['args'] for c in increased]==[c['args'] for c in original]
assert [c['timeout'] for c in increased]==[300,300,120,300]
failed,error=exercise(ROOT/'candidate-checkout/runner.py',300,True)
assert error and failed==increased
ns=dict(BaseModel=BaseModel,Field=Field,Path=Path,os=os,Literal=Literal)
load_functions(ROOT/'candidate-checkout/input.py',{'BootstrapSpec'},ns)
Model=ns['BootstrapSpec'];Model.model_rebuild(_types_namespace=ns)
assert Model().checkout_timeout_seconds==60 and Model(checkout_timeout_seconds=300).checkout_timeout_seconds==300
invalid=[]
for value in (0,-1,True,1.5,'300'):
    try:Model(checkout_timeout_seconds=value)
    except ValidationError:invalid.append(repr(value))
assert len(invalid)==5
# Both production callsites must forward the declared option.
tree=ast.parse((ROOT/'candidate-checkout/runner.py').read_text())
calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_shallow_clone_at_ref']
assert len(calls)==2
for call in calls:
    arg=next(k.value for k in call.keywords if k.arg=='checkout_timeout')
    assert ast.dump(arg)==ast.dump(ast.parse('spec.checkout_timeout_seconds',mode='eval').body)
report={'status':'passed','scope':'Synthetic subprocess responses through pinned clone function; AST config forwarding and actual Pydantic config validation. No real checkout or speed claim.',
        'default_command_timeout_parity':True,'comparison_changes_only_checkout_timeout':True,'checkout_failure_propagates':True,'both_production_calls_forward_option':True,'invalid_config_values_rejected':invalid,'model_calls':0,'remote_jobs':0}
(ROOT/'checkout-candidate-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
