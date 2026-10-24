# Bootstrap recipe state comparison

Start: main `2a1950d239f1ada467c35393991dac87debe35f7`. Permanent research
branch `codex/research/47-bootstrap-recipe-state`, child47 of epic33.

Question: can deterministic, generic recipe emission preserve package-manager
setup state without per-repository repair or additional model calls? The original
official source remains `27d04ee8203cd5b2f20c3997d13836e5f5b64238`.

First inspect the verified fresh45 raw/cache/transcript, emitter and bootstrap
checks. Keep the original export, archive and failed clean build unchanged.
The successful committed-image test boundary is not a Dockerfile rebuild:
identify exactly which invariant was checked before proposing a candidate.

Potential generic policies include validating the emitted recipe before calling
it portable, or refreshing package indexes before an unambiguous saved APT
install. Preserve all original saved commands; do not infer commands from model
thoughts/output, alter task/grading contracts, inject package-specific fixes,
rerun generation or add model repairs. A source-only result is not native proof.

Before any candidate execution, checkpoint the exact source delta, supported
command grammar, meaningful negative cases, raw versus candidate identities and
the declared environment variant. Reuse frozen input/cache and ordinary
validation; keep original verifier/agent limits and resources. Keep build,
positive-control pair, clean oracle command and release readiness separate.
One recovered build cannot establish general dependency closure or fidelity.

Initial source inspection has zero new model calls, jobs or CPU reservations.
A later native comparison needs explicit checkpointed admission inside the
existing epic32CPUh/$90 ceiling (strictly below the user's $100 extra), reserved
TRC capacity only. Stop repeated identical failures. Public HF evidence must be
eligible, append-only and anonymously verified before owned cleanup. Keep issues
open for review and detailed logs in comments; never auto-merge research.
