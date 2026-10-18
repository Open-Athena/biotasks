"""Route one accepted library-task attempt through the existing blind runner."""
import json
from pathlib import Path
from run_scaler_blind_remote import main as run_blind

PROFILES = {
    'sha256:66a071c674ff32e5e35b741f42c98f4442adfc56bdc92e42c54af73298f1afde': 'history_provider_environment',
    'sha256:05a0a0b6a946e78c51b8b6848e6056474fd67df3f639701aba37132cef79c042': 'alpha_provider_environment',
    'sha256:5131392918c294ddbb1dbfa58e9e2f1d1105abaf3da077712d9bb74adce641d6': 'alpha_provider_environment',
}


def main():
    decision = json.loads(Path('acceptance.json').read_text())
    if decision['status'] != 'accepted_for_bounded_pilot':
        raise ValueError('Task acceptance required before solver setup')
    provider = PROFILES.get(decision.get('source_bundle_hash'))
    if provider is None:
        raise ValueError('Unreviewed library-task profile')
    return run_blind(provider=provider)


if __name__ == '__main__':
    raise SystemExit(main())
