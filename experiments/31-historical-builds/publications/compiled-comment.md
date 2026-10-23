🤖 Twelve compiled-fixture cases now pass through the pinned native-stage and exported-verifier shell builders.

The original reset/clean removes the shared library. Running a deterministic compiler command after the source patch restores the intended revision: nop imports value 1 and fails; oracle imports value 2 and passes. A negative control that preserves fixed-ref compiled bytes makes the unfixed nop pass incorrectly. A separate failure control confirms that a multiline rebuild beginning with `false` stops verification before tests.

This uses synthetic C source, local path remapping and a research adapter, not a repaired biological environment. It does not yet cover integrated pipeline configuration, reset/patch failure guards, the graded-parser path or MACS recovery. The saved MACS reconstruction problems remain a separate prerequisite.

The final run took under one second, peaked below 25 MiB RSS and removed its owned temporary directory. No model calls, remote jobs or new capacity.

[Exact results](https://github.com/Open-Athena/biotasks/blob/397b7769c362c689a0714a5d1f014a6830b72cb9/experiments/31-historical-builds/compiled-lifecycle-results.json), [harness](https://github.com/Open-Athena/biotasks/blob/397b7769c362c689a0714a5d1f014a6830b72cb9/experiments/31-historical-builds/check_compiled_lifecycle.py), [resource record](https://github.com/Open-Athena/biotasks/blob/397b7769c362c689a0714a5d1f014a6830b72cb9/experiments/31-historical-builds/compiled-lifecycle-resources.txt), [findings and next steps](https://github.com/Open-Athena/biotasks/blob/397b7769c362c689a0714a5d1f014a6830b72cb9/experiments/31-historical-builds/findings.md).
