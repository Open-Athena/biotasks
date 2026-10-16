# Materialization 001 — stopped before submission

GLM made 52 requests, inspected real inputs and tested partial implementations, but submitted no accepted candidate. The worker repeatedly waited for background processes after shell cleanup had terminated them. The advertised tool timeout also remained at upstream’s 120-second default despite the controller accepting 600 seconds.

The operator stopped only the owned authoring process. The old serial exporter then stalled; a verified recovery archive was written on the same Iris host, and the stalled exporter was stopped so normal sandbox cleanup could finish. A versioned concurrent exporter preserved and download-checked all 323 final evidence files. The final records and original prompt are preserved here; the complete private archive retains raw requests and tool traces. No scientific artifact was manually repaired.

Daytona cleanup passed, and a subsequent provider inventory found zero owned sandboxes. This run is an infrastructure/workflow failure, not a scientific validation or a solver result. Retry 002 corrects stage scope, foreground lifecycle instructions, and the advertised/enforced shell timeout together.
