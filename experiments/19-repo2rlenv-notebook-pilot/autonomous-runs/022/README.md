# Compact-payload placement test: handoff still blocked

Factory `92a1e6f5562be9de7652e3ac35e3d58b05b452ca` submitted the original PyHMMER
seed with the compact runtime archive, after the isolated checks in
payload-checks/001. The job still did not establish a container within its
scheduling allowance. A read of its own handoff row recorded PENDING_HANDOFF:
awaiting peer acknowledgement, rather than queued admission for capacity.

Cancellation returned terminal KILLED, peer reported the job gone, with no start
time and zero tasks. An independent provider inventory found no owned sandboxes.
This is a placement infrastructure failure, not a notebook rejection or scientific
outcome. Model-call count is unknown without a worker ledger. Retain $1 in
conservative holds rather than inventing a measured zero invoice.

The smaller archive reduces source-payload growth and local submission memory,
but this attempt does not establish it as a fix for the external handoff blocker.
All prior outcomes and the earlier full prepared payload remain preserved.
