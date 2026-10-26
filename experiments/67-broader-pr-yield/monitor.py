"""Read-only run monitor and aggregate issue reporter; never admits remote work."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
WORK = ROOT / 'inputs-private/run-001'
REPOS = {'nibabel': 'NiBabel', 'dendropy': 'DendroPy', 'anndata': 'AnnData', 'biopython': 'Biopython'}
STAGES = ['candidate_verified', 'submission_recorded', 'remote_terminal', 'archive_readback_verified', 'publication_resolved', 'cleanup_terminal', 'cleanup_verified']
START = '<!-- biotasks67-monitor-start -->'
END = '<!-- biotasks67-monitor-end -->'


def read(path, default=None):
    return json.loads(path.read_text()) if path.is_file() else default


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.partial')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def alive():
    active = read(ROOT / 'active-workflow.json', {})
    process = read(ROOT / active.get('controller_process', 'controller-process.json'))
    assert len(process) == 1
    p = process[0]
    try:
        fields = Path(f'/proc/{p["pid"]}/stat').read_text().split()
        return fields[21] == p['start_ticks'] and fields[2] != 'Z'
    except FileNotFoundError:
        return False


def complete(directory):
    j = read(directory / 'journal.json', {})
    return [s['stage'] for s in j.get('stages', [])] == STAGES and not j.get('intent')


def history_coverage(history, observations):
    closed = [n for b in history['batches'] for n in b.get('entered', [])]
    unfinished = any('finished' not in b for b in history['batches'])
    events = observations / 'events.jsonl'
    if events.is_file():
        entered = []
        with events.open() as stream:
            for line in stream:
                event = json.loads(line)
                if event.get('event') == 'candidate_entered': entered.append(event['pr'])
        assert len(entered) == len(set(entered)) and set(closed) <= set(entered)
        if not unfinished: assert set(entered) == set(closed)
        # The final interrupted batch never updates its denormalized backlog.
        # Subtract its durable entry events; preserve the original ledger.
        backlog = set(history['backlog_pr_numbers']) - set(entered)
        return {'entered': len(entered), 'backlog': len(backlog), 'entered_source': 'append_only_native_events', 'unfinished_native_batch': unfinished}
    if unfinished:
        return {'entered': None, 'backlog': None, 'entered_source': 'unknown_without_interrupted_batch_events', 'unfinished_native_batch': True}
    assert len(set(closed)) == len(closed)
    return {'entered': len(closed), 'backlog': len(history['backlog_pr_numbers']), 'entered_source': 'closed_native_batch_ledger', 'unfinished_native_batch': False}


def snapshot():
    active = read(ROOT / 'active-workflow.json', {})
    manifest = read(ROOT / active.get('manifest', 'manifest.json'))
    work = ROOT / active['work_dir'] if active else WORK
    budget = read(Path(manifest['budget_ledger']))
    cases = []
    for case in manifest['cases']:
        name = case['id']; gen = (Path(case['generation_root']) if case.get('mode') == 'completed' else work / name) / 'runs/generation'
        listing = read(Path(case['candidates']['path']))
        journal = read(gen / 'journal.json', {})
        r = read(gen / 'readback.json', {})
        proof = read(gen / 'cleanup-proof.json', {})
        c = {'case': name, 'inventory_queued': len(listing['candidates']), 'phase': 'not_started',
             'entered': None, 'backlog': len(listing['candidates']), 'exports': None,
             'positive': 0, 'clean': 0, 'controls_cleaned': 0, 'generation_cleanup_verified': False}
        held = any((gen / f).exists() for f in ['held.json', 'budget-hold.json', 'model-budget-hold.json'])
        if held: c['phase'] = 'held_requires_review'
        elif journal.get('stages') or journal.get('intent'): c['phase'] = 'generation_running_or_finalizing'
        history = read(gen / 'generation-source/native-observations/history-batches.json')
        if history:
            c.update(history_coverage(history, gen / 'generation-source/native-observations'))
        if r and r.get('durable_readback_verified'):
            c['exports'] = len(set(r['exported_tasks']))
        if complete(gen):
            assert proof.get('verified_empty') is True
            c['generation_cleanup_verified'] = True
            c['phase'] = 'zero_exports_complete' if not r['exported_tasks'] else 'export_ready'
        val = work / (name + '-handoff') / 'validation'
        vp = read(val / 'plan.json')
        if vp:
            c['controls_planned'] = len(vp['tasks'])
            c['phase'] = 'controls_running_or_finalizing'
            waiting_cleanup_capacity = False
            for group in vp['tasks']:
                directory = val / 'runs' / group['id']
                failed_cleanup = directory / 'cleanup/submit.log'
                if failed_cleanup.is_file() and not (directory / 'cleanup/submission.json').exists() and 'No compatible existing reserved worker with declared headroom' in failed_cleanup.read_text():
                    waiting_cleanup_capacity = True
                if (directory / 'held.json').is_file():
                    c['phase'] = 'held_requires_review'
                if complete(directory):
                    rb = read(directory / 'readback.json'); cp = read(directory / 'cleanup-proof.json')
                    assert cp['verified_empty'] is True
                    c['controls_cleaned'] += 1
                    c['positive'] += rb.get('positive_control_pair') is True
                    c['clean'] += all(rb.get(k) is True for k in ['positive_control_pair', 'clean_oracle_command', 'complete_parseable_pair', 'all_p2p_pass_both'])
            if waiting_cleanup_capacity: c['phase'] = 'waiting_for_cleanup_capacity'
            if c['controls_cleaned'] == len(vp['tasks']): c['phase'] = 'controls_complete'
        model = [e for e in budget['events'] if e['kind'] == 'model_run_reservation' and e['run_id'] == case['run_id']]
        c['model_cost_usd'] = model[0]['known_actual_usd'] if model and model[0]['state'] == 'terminal reconciled' else None
        c['model_calls'] = model[0]['known_calls'] if c['model_cost_usd'] is not None else None
        cases.append(c)
    running = alive()
    terminal_cases = all(c['phase'] in ['zero_exports_complete', 'controls_complete'] for c in cases)
    state = 'monitoring' if running else ('workflow_complete' if terminal_cases else 'controller_stopped_requires_review')
    return {'report_profile': 'cumulative-table-v5', 'observed_utc': datetime.now(timezone.utc).isoformat(), 'state': state, 'controller_alive': running,
            'cases': cases, 'settled_issue67_model_usd': str(sum((Decimal(c['model_cost_usd']) for c in cases if c['model_cost_usd'] is not None), Decimal(0))),
            'settled_issue67_model_calls': sum(c['model_calls'] or 0 for c in cases),
            'epic_actual_model_usd': budget['recorded_paid_cost_usd'],
            'epic_allocated_cpu_hours': budget['additional_allocated_cpu_hours'],
            'epic_cpu_hour_ceiling': budget['additional_reserved_cpu_hour_ceiling'],
            'epic_reserved_cpu_hours': budget.get('outstanding_cpu_hour_reservations', 0),
            'epic_outstanding_usd_including_storage': budget['outstanding_reservations_usd'],
            'native_or_model_submission_by_monitor': False}


def cumulative_table(body, value):
    # Frozen pre-reassessment outcomes, already deduplicated in issue33's ledger.
    baseline = {
        'nibabel': ('NiBabel / neuroimaging', 1, 1, 1, Decimal('0.473580')),
        'dendropy': ('DendroPy / phylogenetics', 1, 1, 0, Decimal('0.087849')),
        'anndata': ('AnnData / transcriptomics', 0, 0, 0, Decimal('0.313983')),
        'biopython': ('Biopython / sequence-analysis tooling', 0, 0, 0, Decimal('1.033545')),
    }
    for c in value['cases']:
        if c['exports'] is None:
            continue
        label, exports, positive, clean, cost = baseline[c['case']]
        entered = 'unknown' if c['entered'] is None else str(c['entered'])
        backlog = 'unknown' if c['backlog'] is None else str(c['backlog'])
        coverage = f"{entered} / {c['inventory_queued']} historical PRs entered; {backlog} backlog; prior small-run results included"
        if c.get('unfinished_native_batch'): coverage += '; interrupted final batch'
        cost += Decimal(c['model_cost_usd']) if c['model_cost_usd'] is not None else Decimal(0)
        row = f"| {label} | {coverage} | {exports+c['exports']} | {positive+c['positive']} | {clean+c['clean']} | {cost:.6f} |"
        body, changed = re.subn(r'^\| '+re.escape(label)+r' \|[^\n]+$', lambda match: row, body, count=1, flags=re.M)
        assert changed == 1, 'Expected unique overall repository row'
    exports = 85 + sum(c['exports'] or 0 for c in value['cases'])
    positive = 84 + sum(c['positive'] for c in value['cases'])
    clean = 68 + sum(c['clean'] for c in value['cases'])
    cost = Decimal('8.310168') + Decimal(value['settled_issue67_model_usd'])
    total = f'| **Recorded cohort total** | **Incomplete coverage** | **{exports}** | **{positive}** | **{clean}** | **{cost:.6f}** |'
    body, changed = re.subn(r'^\| \*\*Recorded cohort total\*\* \|[^\n]+$', lambda match: total, body, count=1, flags=re.M)
    assert changed == 1, 'Expected unique overall total row'
    return body


def render(value):
    stamp = datetime.fromisoformat(value['observed_utc']).astimezone(ZoneInfo('America/New_York')).strftime('%b %d, %I:%M %p %Z')
    pending_billing = any(c['phase'] != 'not_started' and c['model_cost_usd'] is None for c in value['cases'])
    billing = 'unfinished billing remains pending' if pending_billing else 'all admitted generation billing is reconciled'
    rows = [START, f'**Monitored progress — {stamp}:** `{value["state"]}`. The original controller owns execution; this monitor only reads artifacts and reports changes.', '',
            '| Repository | Stage | Entered / queued | Exports | Positive / clean controls | Settled OpenRouter USD |',
            '| --- | --- | ---: | ---: | ---: | ---: |']
    for c in value['cases']:
        entered = 'pending' if c['entered'] is None else str(c['entered'])
        exports = 'pending' if c['exports'] is None else str(c['exports'])
        cost = 'pending' if c['model_cost_usd'] is None else c['model_cost_usd']
        controls = 'pending' if not c['controls_cleaned'] else f'{c["positive"]} / {c["clean"]}'
        rows.append(f'| {REPOS[c["case"]]} | {c["phase"].replace("_", " ")} | {entered} / {c["inventory_queued"]} | {exports} | {controls} | {cost} |')
    rows += ['', f'Settled new model cost: **${value["settled_issue67_model_usd"]}**; {billing}. Shared ledger: **${value["epic_actual_model_usd"]} settled model cost**, **{value["epic_allocated_cpu_hours"]:.3f} CPUh used / {value["epic_reserved_cpu_hours"]:.3f} reserved / {value.get("epic_cpu_hour_ceiling", 32)} CPUh ceiling**; outstanding dollars include the existing storage reserve. Counts enter this block only from retained readbacks, with positive/clean controls requiring verified cleanup.', END]
    return '\n'.join(rows)


def api(args, value=None):
    command = ['gh', 'api', *args]
    if value is not None: command += ['--input', '-']
    return json.loads(subprocess.check_output(command, input=json.dumps(value).encode() if value is not None else None, timeout=45))


def publish(value):
    old = api(['repos/Open-Athena/biotasks/issues/33'])
    body = cumulative_table(old['body'], value); block = render(value)
    if START in body:
        assert body.count(START) == body.count(END) == 1
        body = body[:body.index(START)] + block + body[body.index(END) + len(END):]
    else:
        heading = '### Broader reassessment underway\n\n'
        assert heading in body
        body = body.replace(heading, heading + block + '\n\n', 1)
    # Remove the superseded manually checked sentence, preserving the rest of the summary.
    body = re.sub(r'\*\*Last checked October 26, 11:33 a\.m\. ET:\*\*[^\n]+\n\n', '', body)
    body = body.replace('DendroPy, AnnData and Biopython remain queued.', 'The live table shows which repositories are running or queued.')
    body = body.replace('The original NiBabel job is active on reserved TRC CPUs, with later repositories and controls subject to the remaining shared budget.', 'The monitor above records the active repository and stage; remaining work shares the original budget.')
    body = body.replace('Its current reservations are **6.333333333 CPUh** and **$13.07 model allowance**, in addition to the **unreconciled $10 storage reserve**. Actual new charges remain pending.', 'Current reservations and reconciled charges are in the monitored progress block; the **$10 storage reserve remains unreconciled**.')
    api(['--method', 'PATCH', 'repos/Open-Athena/biotasks/issues/33'], {'body': body})
    fresh = api(['repos/Open-Athena/biotasks/issues/33'])
    assert fresh['body'] == body and 'agent-generated' in [x['name'] for x in fresh['labels']]
    save(ROOT / 'monitor/last-issue-readback.json', {'body': body, 'verified': True})
    child_body = '**Agent-owned broader historical reassessment:** ' + value['state'].replace('_', ' ') + '. The overall summary is in #33.\n\n' + block + f'\n\nComplete history through October 17; known exports excluded, successive batches at most 100 with no repository count cap. Original controller owns admission, native execution, billing and cleanup. Shared $90 operating / {value.get("epic_cpu_hour_ceiling", 32)} cumulative CPUh limits are read from the campaign ledger; this reporter grants no allowance or capacity. Raw evidence remains private pending redistribution review. Detailed logs and receipts belong in comments and durable artifacts. No additional run, retry or model call is made by this monitor.\n'
    api(['--method', 'PATCH', 'repos/Open-Athena/biotasks/issues/67'], {'body': child_body})
    child = api(['repos/Open-Athena/biotasks/issues/67'])
    assert child['body'] == child_body and 'agent-generated' in [x['name'] for x in child['labels']]
    save(ROOT / 'monitor/last-child-readback.json', {'body': child_body, 'verified': True})
    if value['state'] != 'monitoring':
        text = '🤖 Automatic monitor: ' + value['state'].replace('_', ' ') + '.\n\n' + render(value).replace(START, '').replace(END, '') + '\n\nNo run was admitted or retried by the monitor. Detailed originals remain under the experiment’s private HOME directory; review is required for any held or unsettled state.'
        api(['--method', 'POST', 'repos/Open-Athena/biotasks/issues/67/comments'], {'body': text})


def signature(value):
    return hashlib.sha256(json.dumps({k:v for k,v in value.items() if k != 'observed_utc'}, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--watch', action='store_true'); args = parser.parse_args()
    with (ROOT / 'monitor.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        last = read(ROOT / 'monitor/last-published.json', {})
        while True:
            value = snapshot(); save(ROOT / 'monitor/latest.json', value)
            sig = signature(value)
            if last.get('signature') != sig:
                # Pending phases and costs remain explicitly unknown; no raw logs or model text are published.
                publish(value)
                last = {'signature': sig, 'snapshot': value}; save(ROOT / 'monitor/last-published.json', last)
                print(json.dumps(value), flush=True)
            if not args.watch or value['state'] != 'monitoring': return
            time.sleep(300)


if __name__ == '__main__': main()
