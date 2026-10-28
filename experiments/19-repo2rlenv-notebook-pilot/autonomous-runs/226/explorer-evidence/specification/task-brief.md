# Growth effects of gene and reaction knockouts in the E. coli core metabolic model

## Objective

You are given the curated "textbook" E. coli core metabolic model (SBML). Using flux balance analysis (FBA), determine how every possible single-gene deletion, single-reaction deletion and pairwise reaction deletion affects the maximal achievable growth (the maximum of the model's biomass objective), plus the growth of a few specific knockouts that illustrate gene-level redundancy (isozymes) for phosphofructokinase.

For each knockout scenario the quantity of interest is the optimal value of the model's biomass objective after the knockout is applied, together with the status reported by the LP solve ("optimal" or "infeasible").

## Supplied inputs

- `inputs/e_coli_core.xml` — the E. coli core metabolic model in SBML format (the model known as "textbook" / BiGG `e_coli_core`), including its biomass objective reaction and gene–protein–reaction (GPR) associations. Use the model exactly as supplied; do not modify it, its medium, bounds or objective.

## Knockout semantics

- **Reaction knockout**: the reaction is deleted from any flux-carrying solution — its flux is constrained to zero in both directions.
- **Gene knockout**: a reaction is disabled only if its GPR rule evaluates to false with the knocked-out gene(s) removed. If a reaction has an isozyme gene that remains functional (e.g. an OR in the GPR), the reaction still carries flux. A gene whose removal disables no reaction therefore has no growth effect even though the gene is knocked out.

## Required outputs

Produce four CSV files. All use the columns `knockouts,growth,status`:

- `knockouts`: the identifier(s) of the knocked-out entity (gene id or reaction id, exactly as defined in the supplied model), sorted lexicographically and joined with `;` (e.g. `b1723;b3916`, `Biomass_Ecoli_core;LDH_D`). For a knockout of a single entity the label is just that entity's id.
- `growth`: the optimal objective value of the LP after the knockout, as reported by the solver at full double precision, with no rounding, clamping or sign correction (tiny negative numerical values of magnitude ~1e-14 that arise from solver noise are expected and must be reported as-is). If the knockout makes the problem infeasible, leave this field empty.
- `status`: the LP solve status string, e.g. `optimal` or `infeasible`.

### 1. `single_gene_deletions.csv`
One row for **every gene defined in the supplied model** (including genes whose deletion disables no reaction), reporting the effect of knocking out that gene alone.

### 2. `single_reaction_deletions.csv`
One row for **every reaction defined in the supplied model** (this includes boundary/exchange reactions), reporting the effect of knocking out that reaction alone.

### 3. `double_reaction_deletions.csv`
One row for **each distinct set of one or two reactions** obtained by pairing every reaction in the model with every reaction in the model and reducing the pair to an unordered set. Concretely: for all ordered pairs (r_i, r_j) over the model's full reaction list, the resulting knockout sets {r_i, r_j}; the i = j cases contribute the single-reaction sets {r_i}. Do not apply gene-level GPR logic here — both reactions are knocked out directly. Report growth and status for each set.

### 4. `pfk_knockout_optima.csv`
Four rows, using the same column convention, with an empty `knockouts` field for the no-knockout row:

| knockouts | scenario |
|---|---|
| *(empty)* | wild-type model, no knockout |
| `PFK` | the PFK reaction knocked out |
| `b1723` | gene b1723 (pfkA) knocked out |
| `b1723;b3916` | genes b1723 (pfkA) and b3916 (pfkB) knocked out simultaneously |

These quantify the redundancy narrative: the isozyme pfkB can compensate for a pfkA deletion, but not when both are removed.

## Conventions

- Row order in every file carries no scientific meaning; any row ordering is acceptable.
- Growth is reported in the model's native biomass-objective units (the raw LP objective value).
- Use the knockout populations exactly as defined above; do not skip entities that have no reaction associations or no growth effect.
- Do not round any value (`growth` is written at full double precision).

## Environment and resources

- CPU only (up to 4 cores), 8 GiB RAM, 10 GiB disk, no network access. Your program must complete within 600 seconds.
- A reference Python environment (cobrapy 0.32.1 with the GLPK solver) can be supplied for convenience, but any software stack that satisfies the definitions above is acceptable; the results, not the tool, are what is compared.
- Exact acceptance criteria (including numerical tolerances appropriate for LP-solver variation) are finalized separately during validation before the contract takes effect; produce results faithful to the definitions above.
