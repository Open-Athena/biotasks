"""Read-only exact-ID absence check using the authorized process environment.

The caller supplies IDs from its own creation receipts. Only a native SDK
not-found response proves absence; other errors propagate.
"""
import json,re,sys
from daytona import Daytona
from daytona.common.errors import DaytonaNotFoundError
worker_id=sys.argv[1]
assert re.fullmatch(r'[0-9a-f-]{36}',worker_id)
try:
 Daytona().get(worker_id)
 raise RuntimeError('Exact owned sandbox still present; no release')
except DaytonaNotFoundError:
 print(json.dumps({'worker_id':worker_id,'independently_confirmed':True,'http_status':404}))
