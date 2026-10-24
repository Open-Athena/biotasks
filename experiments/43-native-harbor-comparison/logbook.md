# Native published-Harbor comparison

## 2026-10-24: preparation

Issue #43 is an actual child of #33, from main 2a1950d239f1ada467c35393991dac87debe35f7. Reuse the #41 outer transport/ownership design at b5533ced and the verified published 0.24.0 acquisition from #42 at 6d359949. No admission or remote runtime yet. Compare both published versions serially with the same additional external observer, preserving native package source, 2/30-second writer, 5-second verifier deadline and resource contract. Keep the exact writer bytes; its legacy BIOTASKS_RUN_ID input marker retains the biotasks41 prefix while Docker/job ownership uses biotasks43 labels. No biological task or pipeline dependency changes.
