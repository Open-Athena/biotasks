"""Convert saved Pi message events to ATIF for display; never infer missing output."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


def convert(path, session_id='seta-cytopathology-pi-glm53'):
    raw = path.read_bytes()
    steps, calls, completed = [], {}, False
    for line in raw.decode().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'agent_end':
            completed = True
        if event.get('type') != 'message_end':
            continue
        msg = event['message']
        role = msg.get('role')
        content = msg.get('content', [])
        if isinstance(content, str):
            content = [{'type': 'text', 'text': content}]
        text = '\n\n'.join(p.get('text', '') for p in content if p.get('type') == 'text')
        if role == 'toolResult':
            call_id = msg['toolCallId']
            if call_id not in calls:
                raise ValueError('Tool result without a recorded call')
            step = calls[call_id]
            step.setdefault('observation', {'results': []})['results'].append({
                'source_call_id': call_id, 'content': text,
                'extra': {'is_error': msg.get('isError', False)},
            })
            continue
        if role not in ['system', 'user', 'assistant']:
            continue
        step = {'step_id': len(steps) + 1, 'source': 'agent' if role == 'assistant' else role,
                'message': text}
        if msg.get('timestamp'):
            step['timestamp'] = datetime.fromtimestamp(msg['timestamp']/1000, timezone.utc).isoformat()
        if role == 'assistant':
            step['reasoning_content'] = '\n\n'.join(p.get('thinking', '') for p in content if p.get('type') == 'thinking')
            step['tool_calls'] = [{'tool_call_id': p['id'], 'function_name': p['name'], 'arguments': p.get('arguments', {})} for p in content if p.get('type') == 'toolCall']
            for call in step['tool_calls']:
                calls[call['tool_call_id']] = step
            usage = msg.get('usage', {})
            # Pi reports input separately from cache reads/writes.
            step['metrics'] = {'prompt_tokens': usage.get('input', 0) + usage.get('cacheRead', 0) + usage.get('cacheWrite', 0),
                               'completion_tokens': usage.get('output', 0), 'cached_tokens': usage.get('cacheRead', 0)}
            step['extra'] = {'pi_stop_reason': msg.get('stopReason')}
        steps.append(step)
    pending = [call_id for call_id,step in calls.items() if not any(r.get('source_call_id') == call_id for r in step.get('observation', {}).get('results', []))]
    trace = {'schema_version': 'ATIF-v1.7', 'session_id': session_id,
             'agent': {'name': 'Pi', 'version': '0.87.0', 'model_name': 'GLM-5.3'}, 'steps': steps,
             'notes': 'Converted from retained Pi message_end events. Intermediate streaming deltas are omitted; messages, reasoning, tool calls and observed outputs are preserved. No missing output is invented.',
             'extra': {'source_sha256': hashlib.sha256(raw).hexdigest(), 'conversion': 'pi-message-events-to-atif-v1', 'agent_end_observed': completed, 'pending_tool_call_ids': pending}}
    encoded = json.dumps(trace, ensure_ascii=True, indent=2)
    encoded = re.sub(r'https?://[^\s"<>]+(?:iris\.oa\.dev)[^\s"<>]*', '[private service URL]', encoded)
    # Include the common host-first form as well.
    encoded = re.sub(r'https?://(?:[^/"\s]+\.)?iris\.oa\.dev[^\s"<>]*', '[private service URL]', encoded)
    return json.loads(encoded)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--session-id', default='seta-cytopathology-pi-glm53')
    args = parser.parse_args()
    trace = convert(args.source, args.session_id)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(json.dumps(trace, indent=2) + '\n')
    print(json.dumps({'steps': len(trace['steps']), 'complete': trace['extra']['agent_end_observed'], 'pending_tools': len(trace['extra']['pending_tool_call_ids'])}))
