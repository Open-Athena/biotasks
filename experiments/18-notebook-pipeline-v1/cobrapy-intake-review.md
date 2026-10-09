# COBRApy input preparation

The pinned seed calls `load_model("textbook")`. Its repository contains `src/cobra/data/textbook.xml.gz`; this exact 18237-byte archive is staged with URL and SHA-256 in `cobrapy-inputs.json`. Inspection confirms the SBML model ID `e_coli_core`, biomass maximization objective and flux units mmol/gDW/hour. This is a curated mechanistic reconstruction and computed predictions, not observed flux measurements.

Keep the scoped comparison of biomass versus ATP maintenance. The seed explicitly sets ATPM upper bound to 1000 for the second objective; preserve or explicitly justify consequential bounds. Grade objective values and flux feasibility with documented numerical tolerances, not one unique optimal flux vector. Avoid sampling, expensive loopless analyses or solver-package requirements in the task instruction.

The repository LICENSE is preserved in private intake and its hash is recorded; it contains GPL and LGPL license text. Model-specific attribution and redistribution eligibility remain to be resolved before public artifact publication. No model optimization, authoring or native validation has occurred for this seed.
