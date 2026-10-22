# Staged-input publication review

Observed 21 October 2026. This review uses hash-verified input manifests retrieved from the two live workers. It does not change their tasks, scientific methods, selected endpoints or running factory. Neither new campaign is yet scientifically validated or published. Machine-readable evidence and source hashes are in [the review record](development-panel-active-input-terms.json).

## PyHMMER 025

The staged inputs are the pinned repository's `LuxC.sto` and `LuxC.faa`; their SHA-256 values match the exact upstream files. The alignment header identifies Pfam PF05893.5, and the sequence headers identify UniProtKB/Swiss-Prot accessions. [Pfam's primary notice](https://pfam-docs.readthedocs.io/en/dev/#license) states CC0; [UniProt's primary notice](https://www.uniprot.org/help/license) applies CC BY 4.0 to copyrightable database content ([machine-readable notice](https://rest.uniprot.org/help/license)). The repository MIT license is considered separately from these data notices.

This provenance supports redistribution of these two unchanged inputs with source references and UniProt attribution. Inspect the final release inventory for any additional data before publishing. Retain the PyHMMER MIT notice and relevant dependency notices; do not relabel all data MIT. Scientific controls, native trials and a fresh release download must still establish the task's validation and publication state.

## NeuroKit HRV 024

The live worker stages the original five-minute, 100-Hz physiological recording and a documented offline adaptation of the MIT-licensed loader. The pinned [data README](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/data/README.rst) describes use for testing, but does not provide an independent redistribution license for this recording. The [official example](https://neuropsychology.github.io/NeuroKit/examples/bio_intervalrelated/bio_intervalrelated.html) identifies the single-subject resting recording; its documentation license does not establish the dataset's license.

Keep the task and staged recording private while source-specific redistribution remains unestablished. This does not classify the notebook as scientifically rejected or stop its approved execution. No substitute data, synthetic recording or task-specific patch was introduced.


## Pyteomics filtering 038 — 22 October 2026

This selected-output task passed its exact archived bundle checks, 27 final scientific controls and all three native trials. The later source-coverage review rejected its omission of two eligible endpoints; full-scope acceptance is not established. Publication is also a separate boundary. The final task stages `example.PSMs.tsv` (3,612,795 bytes) and `example_output.csv` (9,815,862 bytes); their source URLs and SHA-256 values are bound in the machine-readable record. The [official filtering example](https://pyteomics.readthedocs.io/en/latest/examples/example_filtering.html) links to the [original public data directory](http://pubdata.theorchromo.ru/pyteomics_filtering_example/). The inspected directory lists data files but no license or README link. Public download availability and the notebook’s Apache-2.0 code license do not independently establish permission to redistribute these example inputs.

Keep this candidate and its data private while source-specific terms remain unestablished. No public release or data upload is claimed, and no substitute data, task modification or scientific rerun was introduced to bypass that boundary. The directory snapshot remains private; the public record contains only its source URL and checksum.
