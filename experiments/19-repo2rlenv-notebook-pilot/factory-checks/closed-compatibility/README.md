# Completed synthetic-control reservations

`reconcile.py` binds the original configurations, known sandbox creator, execution
receipts, resource claims, deletion receipts and independently observed absence for
the two completed transport/staging controls in `plan.json`. It also verifies the
exact source hashes against the current checkout. Unknown, incomplete or mismatched
evidence retains the original reservation.

Each control used one offline 4-CPU/8-GiB/10-GiB sandbox with no model or biological
execution. Price the entire approved 480-second work/cleanup allowance, plus
300 seconds at each end, at the existing conservative full-resource rate. Add
$0.10 and round upward to $0.25. The bound is $0.25 per completed control; the
original $1 holds release $1.50 in total. This is not an invoice or an assumption
of free credits. The full $5 reservation for a new notebook campaign is unchanged.

The eleven refusal/bound tests pass:

```sh
PYTHONPATH=experiments/19-repo2rlenv-notebook-pilot/factory-checks/closed-compatibility \
  .venv/bin/python -m pytest \
  experiments/19-repo2rlenv-notebook-pilot/factory-checks/closed-compatibility/test_reconcile.py -q
```

`dry-run.json` records the pre-application ledger hash. Application uses a distinct
proof and verifies that the ledger has not changed before writing it. Original
provider evidence remains unchanged and retained privately.
