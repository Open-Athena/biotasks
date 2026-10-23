"""Synthetic classification checks only; no Harbor execution or scientific result."""
from copy import deepcopy
from harvest_macs_742_controls import classify_pair


def main():
    common = dict(verifier_timeout_seconds=300, state='completed', wrapper_exit=0,
        trial_record_present=True, reward_details_present=True, exception_present=False,
        parse_status='ok', resolved=True, command_resolved=True, p2p_total=10, p2p_passed=10)
    rows = [dict(common, agent='nop', reward=0), dict(common, agent='oracle', reward=1)]
    assert classify_pair(rows)['positive_control_pair']
    assert not classify_pair(rows[:1])['positive_control_pair']
    checks = 2
    for changes in (dict(state='timeout'), dict(wrapper_exit=1), dict(trial_record_present=False),
                    dict(reward_details_present=False), dict(exception_present=True), dict(parse_status='error'),
                    dict(reward=0), dict(resolved=False)):
        changed = deepcopy(rows)
        changed[1].update(changes)
        assert not classify_pair(changed)['positive_control_pair'], changes
        checks += 1
    changed = deepcopy(rows)
    changed[1].update(command_resolved=False)
    result = classify_pair(changed)
    assert result['positive_control_pair'] and not result['clean_oracle_command']
    changed = deepcopy(rows)
    changed[0].update(p2p_passed=9)
    assert not classify_pair(changed)['all_regression_tests_pass_both']
    print(f'{checks + 2} synthetic classification checks passed; no live controls executed')


if __name__ == '__main__':
    main()
