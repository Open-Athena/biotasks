# Static inspection evidence

Repo2RLEnv pin: 27d04ee8203cd5b2f20c3997d13836e5f5b64238.

- [Route/input mapping](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/docs/pipelines/owned_recipes.md)
- [Native parser dispatch](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/src/repo2rlenv/log_parsers/__init__.py): pytest, unittest, Go, Cargo, nextest, Jest; unknown runners return an empty map. Some prose in pr_runtime.md still says Python is pytest-only, despite unittest dispatch in source; execute a profile before concluding compatibility.
- [CodeMidas stages](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/docs/pipelines/codemidas.md): dedicated author/review/solver model paths require inspection.
- [Biopython test runner](https://github.com/biopython/biopython/blob/4eda92397bdedff82f04ac218a862ae25ebdc4a8/Tests/run_tests.py): custom PyUnit runner; --offline skips network-dependent tests.
- [DESeq2 package](https://github.com/thelovelab/DESeq2/blob/76c5f8523716804dbe0a9500b4b7e216c6af225c/DESCRIPTION): Bioconductor dependencies, Rcpp/RcppArmadillo, testthat, LGPL >=3. License inspection is not a redistribution clearance for all fixtures.

The matrix marks source-based candidates provisionally. No language/profile claim proves buildability, deterministic grading, model compatibility, or scientific suitability.
