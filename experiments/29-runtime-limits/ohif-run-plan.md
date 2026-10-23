# OHIF unchanged reconstruction, attempt 001

Replay the original saved recipe at `OHIF/Viewers@4965e280cada2202a99f9dd0212a8465865b49f7` on existing reserved TRC CPUs. Same bounded reconstruction procedure as Matchms: 4 allocated CPUs/16 GiB RAM/disk, 2,400-second job maximum and 1,800-second Docker-build deadline, 1.5 CPU/6 GiB build limits, one attempt, no automatic retries, no new capacity and no model calls. Public source acquisition is anonymous. This at-most 2.667 CPU-hour attempt is part of the cumulative 32 CPU-hour first-stage bound; prior completed work consumed 0.43497723 CPU-hours.

The sole Dockerfile adaptation is the ownership LABEL after FROM for scoped cleanup. Preserve base/COPY/RUN commands exactly. No package, test or per-repository repair. If the recipe fails, retain its diagnostic and stop; do not silently skip a failed command. A successful image is owned and retained only for the pending original OHIF controls, then removed after archive readback or investigation termination. Shared input images are not removed. Record mutable base/dependency drift separately from original-image reproduction.

The Matchms recipe implementation is copied with only owner/repository/ref substitutions; submission adds a cumulative budget check and requires all previous #29 jobs terminal. No task generation or control execution is part of this reconstruction attempt.
