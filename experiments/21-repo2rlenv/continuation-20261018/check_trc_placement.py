"""No-service placement controls: reject paid/unknown worker paths."""
import json

from iris.cluster.constraints import AttributeValue, evaluate_constraint
from iris.cluster.types import ResourceSpec
from trc_placement import existing_trc_constraints


def main():
    constraints = existing_trc_constraints(['existing-reserved-a'])
    good = {'cluster': 'marin', 'device-type': 'tpu', 'preemptible': 'false', 'tpu-name': 'existing-reserved-a'}
    cases = [(good, True)]
    for key, value in [('cluster', 'cw-rno2a'), ('device-type', 'cpu'), ('preemptible', 'true'), ('tpu-name', 'unobserved-new-slice')]:
        cases.append(({**good, key: value}, False))
    for attributes, expected in cases:
        assert all(evaluate_constraint(AttributeValue(attributes[c.key]), c) for c in constraints) is expected
    try:
        existing_trc_constraints([])
    except ValueError:
        pass
    else:
        raise AssertionError('Empty placement allowlist accepted')
    resources = ResourceSpec(cpu=2, memory='4g', disk='10g').to_proto()
    assert not resources.HasField('device') or resources.device.WhichOneof('device') == 'cpu'
    print(json.dumps({'placement_cases_passed': len(cases), 'empty_allowlist_rejected': True, 'accelerators_requested': False, 'remote_calls': 0}))


if __name__ == '__main__':
    main()
