import csv,json
from pathlib import Path
base=Path('docs/experiments/bio-task-generation/01-discovery');sub='data/top200-2026-09-29';folder=base/sub
d=json.loads((folder/'expansion-results-2026-09-29.json').read_text())
rows=list(csv.DictReader((folder/'rankings-2026-09-29.csv').open()));ann={r['source_id']:r for r in csv.DictReader((folder/'source-annotations-2026-09-29.csv').open())};sources={r['source_id']:r for r in json.loads((folder/'source-observations-2026-09-29.json').read_text())}
names={'bioconda':'Bioconda','bioconductor':'Bioconductor','pypi':'PyPI','github':'GitHub stars'}
units={'bioconda':'Cumulative downloads','bioconductor':'Download score','pypi':'30-day downloads','github':'Stars'}
lines=['# Additional sources: ranks 101–200','', '[Expansion analysis](ranking-expansion.md) · [Ranks 1–100](ranking-lists.md) · [Discovery results](index.md)','', 'These are the second hundred sources in each ranking, using the same September 29, 2026 numeric snapshots as the first hundred. The complete 800 positions cover 672 distinct sources; 337 were absent from all four original lists.','',f'Download [all 800 positions]({sub}/rankings-2026-09-29.csv), [source observations and GitHub stars]({sub}/source-observations-2026-09-29.json), or [manual annotations and scope notes]({sub}/source-annotations-2026-09-29.csv). Stars for sources outside the frozen GitHub ranking pool were collected during identity checks; those sources were not added to that ranking. A dash means no verified GitHub mapping.','', 'Scores have different units and time windows. Source types describe the main deliverable; finer topics are assistant-assigned metadata judgments, not validated task capabilities.','']
for name,title in names.items():
 lines.extend([f'## {title}','',f'| Rank | Source | {units[name]} |'+(' GitHub stars |' if name!='github' else '')+' Source type | Finer topic |', '| ---: | --- | ---: |'+(' ---: |' if name!='github' else '')+' --- | --- |'])
 for row in rows:
  if row['ranking']!=name or int(row['rank'])<=100:continue
  s=sources[row['source_id']];a=ann[row['source_id']];title=s['github']['name'] if s['github'] else s['name'];title=title.replace('|','\\|');stars=f"{s['github']['stars']:,}" if s['github'] else '—'
  lines.append(f"| {row['rank']} | [{title}]({s['source_url']}) | {int(row['score']):,} |"+(f' {stars} |' if name!='github' else '')+f" {a['source_type']} | {a['manual_topic']} |")
 lines.append('')
(base/'ranking-additions.md').write_text('\n'.join(lines))
lines=['# Expanding each ranking from 100 to 200','', '[Discovery results](index.md) · [Top-100 baseline](ranking-comparison.md) · [Ranks 101–200](ranking-additions.md)','', '''Expanding to 200 is useful within the recorded discovery scope. The four lists
now contain **672 distinct sources, up from 335**, with **337 new sources** and
46 additional finer topic labels. Bioconductor shows the largest improvement in
primary-topic balance; PyPI remains the most balanced. GitHub adds teaching,
conservation and biomechanics sources while retaining a strong imaging bias.
Normalized overlap between rankings changes little.

The first 100 source identities, scores and manual labels in every list are
unchanged. Download snapshots, score windows and the GitHub discovery pool are
held fixed. The original 95-source inventory and all top-100 data artifacts are
preserved. This is source discovery: candidate software and source archives were
not executed, and task usefulness has not been validated.

## What the extra hundred contributes

“New sources” below means absent from the **combined 335-source baseline**, not
merely absent from that ranking's first hundred. These counts are not additive:
some newly discovered sources enter more than one expanded list.
''', '| Ranking | New sources vs. combined baseline | Primary groups, 100 → 200 | Finer topics, 100 → 200 | Effective primary groups, 100 → 200 |','| --- | ---: | ---: | ---: | ---: |']
for name,r in d['rankings'].items():
 a=r['first100'];b=r['full200'];lines.append(f"| {names[name]} | {len(r['new_to_baseline_union'])} | {a['domain_bins']} → {b['domain_bins']} | {a['manual_topic_bins']} → {b['manual_topic_bins']} | {a['effective_domain_bins']:.1f} → {b['effective_domain_bins']:.1f} |")
lines.extend(['', '''Effective groups are exp(Shannon entropy): a larger value indicates a more even
spread under the chosen labels. Comparing equal-size halves gives 7.5 → 9.6 for
Bioconda, 6.6 → 11.3 for Bioconductor, 13.9 → 14.3 for PyPI and 8.1 → 10.6 for
GitHub. The right panel below uses those equal-size halves, rather than the
100-versus-200 values in the table.

![Topic accumulation and balance in the second hundred](figures/ranking-expansion-2026-09-29.svg)

The combined lists grow from 18 to 22 primary groups and from 79 to 125 finer
labels. Four new **primary assignments** appear: immunology, metabolomics,
ecology/conservation and biomechanics/physiology. This does not establish that
all uses of those subjects were absent from the first hundred: multi-purpose
sources receive one primary label, and some baseline repositories already carry
immunology or metabolomics tags.

These are practical discovery labels, not a comprehensive biological ontology.
The finer labels include formats, infrastructure, teaching and literature uses.
They were assigned from metadata and selected README checks, without independent
human validation. Existing labels are frozen; newly selected sources can receive
additional labels when the old vocabulary does not describe their main use.

## Scientific and instructional additions

Bioconda adds [ANARCI](https://github.com/oxpig/ANARCI) for immune-receptor
annotation, [CRISPRme](https://github.com/pinellolab/CRISPRme) for off-target
analysis, [cooltools](https://github.com/open2c/cooltools) for chromosome
conformation, and [Augur](https://github.com/nextstrain/augur) for pathogen
phylogenetics. Its primary-group gain is modest, 14 to 15, but its finer labels
grow by 14. Sequence processing falls from 35% of the first hundred to 18% of
the second hundred.

Bioconductor's second hundred includes metabolomics through
[xcms](https://github.com/sneumann/xcms), methylation through
[minfi](https://github.com/hansenlab/minfi) and [bsseq](https://github.com/hansenlab/bsseq),
cell trajectories through [Slingshot](https://github.com/kstreet13/slingshot),
and [DEXSeq](https://bioconductor.org/packages/3.23/bioc/html/DEXSeq.html) for
differential exon usage. DEXSeq appears through the download ranking, without a
splicing-specific search. Computing infrastructure accounts for 39 of its first
hundred primary labels and 19 of its second hundred. Bioconductor remains
R-centered; these additions broaden scientific uses within that ecosystem.

PyPI already covers many primary groups in its first hundred. The expansion
adds finer uses such as antigen presentation and vaccine peptides through
[mhctools](https://github.com/openvax/mhctools),
[Topiary](https://github.com/openvax/topiary) and
[Vaxrank](https://github.com/openvax/vaxrank); population simulation through
[msprime](https://github.com/tskit-dev/msprime); and biochemical reaction/diffusion
simulation through [Smoldyn](https://github.com/ssandrews/Smoldyn).

GitHub adds [OpenSim](https://github.com/opensim-org/opensim-core) for
musculoskeletal modeling and the [Microsoft Biodiversity hub](https://github.com/microsoft/Biodiversity)
for conservation resources. The latter currently links to separately maintained
projects, so it is classified as a resource index. Those linked projects were
not recursively added to the frozen ranking. Imaging still accounts for 57 of
200 sources, or 28.5%, compared with 30% at the original cutoff.

GitHub's five additional teaching sources are
[Practical Cheminformatics Tutorials](https://github.com/patwalters/practical_cheminformatics_tutorials),
[Single-cell Best Practices](https://github.com/theislab/single-cell-best-practices),
[Applied Computational Genomics](https://github.com/quinlan-lab/applied-computational-genomics),
the [GWAS/PRS tutorial](https://github.com/MareesAT/GWA_tutorial), and
[An Introduction to Applied Bioinformatics](https://github.com/applied-bioinformatics/an-introduction-to-applied-bioinformatics).
They bring the teaching total to nine. Two microscope-construction projects and
one review/article also enter, adding source types missing from the first hundred.

## Marginal gains by blocks of 25

Each cell counts finer labels first encountered in that ranking at the indicated
block. A label already found through another ranking still counts here; the
combined-union row counts novelty across all four lists.
''','| Ranking | 101–125 | 126–150 | 151–175 | 176–200 |','| --- | ---: | ---: | ---: | ---: |'])
for name,r in d['rankings'].items():lines.append('| '+names[name]+' | '+' | '.join(str(len(b['new_topics'])) for b in r['blocks'])+' |')
nov=[len(d['union_by_depth'][str(k)]['new_topics']) for k in [100,125,150,175,200]]
lines.append('| Combined union | '+' | '.join(str(b-a) for a,b in zip(nov,nov[1:]))+' |')
lines.extend(['', '''The corresponding additions of distinct sources to the union are 82, 88, 85
and 82. There is no clear plateau by rank 200 under these labels. This supports
keeping the expanded inventory; it does not by itself establish that collecting
another hundred will improve executable task yield.

## Overlap remains low outside Bioconda/Bioconductor

Absolute intersections grow with the lists. Jaccard overlap divides the shared
sources by the union and makes the two cutoff sizes comparable.
''','| Pair | Shared at 100 | Shared at 200 | Jaccard at 100 | Jaccard at 200 |','| --- | ---: | ---: | ---: | ---: |'])
for p in d['pairs']:
 a=p['by_depth']['100'];b=p['by_depth']['200'];lines.append(f"| {names[p['first']]} / {names[p['second']]} | {a['shared']} | {b['shared']} | {a['jaccard']:.1%} | {b['jaccard']:.1%} |")
lines.extend(['', '''The near-constant normalized overlaps support retaining separate discovery
routes. The zero Bioconductor/PyPI intersection concerns canonical source
identities at these cutoffs, not shared scientific capabilities or interoperability.
''','## Source types in ranks 101–200','', '| Main deliverable | Bioconda | Bioconductor | PyPI | GitHub stars |','| --- | ---: | ---: | ---: | ---: |'])
for kind in ['Software','Infrastructure','Workflow','Research implementation','Resource index','Tutorial/course','Agent instructions','Data resource','Hardware project','Review/article']:
 lines.append('| '+kind+' | '+' | '.join(str(d['rankings'][k]['second100']['source_types'].get(kind,0)) for k in names)+' |')
lines.extend(['', '''A software-only sensitivity retains software, infrastructure, workflows and
research implementations without backfilling. Resource indexes and educational
materials remain eligible for the main discovery inventory. Source type records
the main deliverable; software packages may also contain useful exercises.
''','| Ranking | Software subset at 200 | Effective groups in that subset |','| --- | ---: | ---: |'])
for name,r in d['rankings'].items():
 s=r['full200']['software_subset'];lines.append(f"| {names[name]} | {s['n']} | {s['effective_domain_bins']:.1f} |")
lines.extend(['','## GitHub tags','', '''Raw tags expand substantially, but include languages, frameworks and agent
infrastructure. They should not be interpreted as a count of biological fields.
Coverage is especially sparse in the second hundred of both Bioconda and
Bioconductor: only 33 and 31 sources, respectively, have any GitHub tags.
''','| Ranking | Tagged sources, first / second hundred | Distinct tags, 100 → 200 | New raw tags |','| --- | ---: | ---: | ---: |'])
for name,r in d['rankings'].items():
 a=r['tags_first100'];b=r['tags_second100'];c=r['tags_full200'];lines.append(f"| {names[name]} | {a['tagged_sources']} / {b['tagged_sources']} | {a['raw_tag_count']} → {c['raw_tag_count']} | {len(r['new_raw_tags'])} |")
lines.extend(['', '''The expanded exact-string mapping adds scientific tags and gives `immunology`
and `metabolomics` their own groups. **Both cutoffs are recomputed using this same
mapping**, so the tag-based baseline below differs slightly from the earlier
report's coarser mapping. No baseline tags or star observations were refreshed.
A source matching several groups contributes one unit divided equally among
them; untagged or unmapped sources receive no inferred tags.
''','| Ranking | Sources with mapped tags, 100 → 200 | Mapped groups, 100 → 200 | Effective tag groups, 100 → 200 |','| --- | ---: | ---: | ---: | ---: |'])
for name,r in d['rankings'].items():
 a=r['tags_first100'];b=r['tags_full200'];lines.append(f"| {names[name]} | {a['mapped_sources']} → {b['mapped_sources']} | {len(a['mapped_domains'])} → {len(b['mapped_domains'])} | {a['effective_domain_bins']:.1f} → {b['effective_domain_bins']:.1f} |")
lines.extend(['', '''Tags broadly agree that Bioconductor and GitHub gain balance, while PyPI's
mapped-tag balance changes little. Manual labels find new immune-analysis uses
in PyPI even though its second-hundred sources do not add an immunology tag
assignment. This is a concrete reason to retain both views.

## Scope, identity checks and cutoffs

The [baseline methods](ranking-comparison.md#ranking-definitions-and-search-scope)
remain in force: separate scores, no composite popularity rank, the same broad
searches, and no biological-domain quotas. Eligibility includes software,
workflows, education, research code, biological resource collections and official
source archives. General computing/materials false positives are explicitly
screened out. Ambiguous cross-domain cases have per-source notes.
''','| Ranking | Expanded screen | 200th source score | Raw rank |','| --- | --- | ---: | ---: |'])
scopes={'bioconda':'Highest 500 raw package rows','bioconductor':'Highest 250 package rows','pypi':'Current identities checked for highest 350 of 1,000 retained numeric rows','github':'Same 1,370 resolved repository universe'}
for name,r in d['rankings'].items():lines.append(f"| {names[name]} | {scopes[name]} | {r['full200']['cutoff_score']:,} | {r['full200']['last_raw_rank']} |")
lines.extend(['', '''Bioconda still uses cumulative file counters; Bioconductor uses average monthly
distinct IPs over September 2025–August 2026. PyPI still uses the same ClickPy
30-day window, August 30–September 28, 2026, excluding the four recorded mirror
installers. These counters are not interchangeable and do not measure unique
researchers. The original 95-source PyPIStats measurements remain a separate
provider snapshot.

The GitHub list is the top 200 **within the recorded universe**, not an exhaustive
global biology ranking. Newly checked package repositories receive metadata but
do not enter the star-ranking pool. Otherwise deeper package discovery could
change the first hundred and confound the depth comparison. The two truncated
search pages ended at 642 and 523 stars, below the new 889-star cutoff. Restricting
to search-discovered repositories retains 172 of the supplemented top 200;
its overlaps with Bioconda, Bioconductor and PyPI are 15, 1 and 25. Package seeds
therefore still affect the GitHub overlap analysis.

Identity review collapses BioPerl metapackage/core distributions to one source,
verifies redirects for PyRanges/NCLS, and corrects stale PyPI links for
PEPHubClient, fcsparser and medspacy-QuickUMLS. The unresolved scCoord repository
link is replaced with its official PyPI source archive. GMAP, ClustalW,
Clustal Omega, Stacks, Subread and RpsbProc have versioned source-archive links
from pinned recipes. Archive payloads were not downloaded or executed. MEME
Suite and Entrez Direct remain in the unchanged first hundred.

## Artifacts and reproduction
''',f'- [Additional ranked sources](ranking-additions.md), with scores, GitHub stars, source types and finer topics.',f'- [Complete ranking table]({sub}/rankings-2026-09-29.csv), [annotations]({sub}/source-annotations-2026-09-29.csv), and [source observations]({sub}/source-observations-2026-09-29.json).',f'- [Expansion results]({sub}/expansion-results-2026-09-29.json), [top-200 results]({sub}/ranking-results-2026-09-29.json), [tag frequencies]({sub}/ranking-topic-frequencies-2026-09-29.csv), and [tag mapping]({sub}/tag-domains-2026-09-29.csv).',f'- Screening tables for [Bioconda]({sub}/ranking-candidates-bioconda-2026-09-29.csv), [Bioconductor]({sub}/ranking-candidates-bioconductor-2026-09-29.csv), [PyPI]({sub}/ranking-candidates-pypi-2026-09-29.csv) and [GitHub]({sub}/ranking-candidates-github-2026-09-29.csv).',f'- [Provenance]({sub}/ranking-provenance-2026-09-29.json) and [exclusions]({sub}/ranking-exclusions-2026-09-29.json), including input hashes, identity overrides, the frozen discovery scope and provider definitions.','', '''The commands below run from the repository root using Python's standard library.
They validate ordered unique sources, package-to-source maximum aggregation,
annotation coverage, input hashes, unchanged baseline identities/scores/labels,
frozen baseline tags/stars and the search-page boundaries.

```bash
uv run --no-project experiments/bio_tasks/01_discovery/analyze_rankings.py \\
  --data-dir docs/experiments/bio-task-generation/01-discovery/data/top200-2026-09-29 \\
  --date 2026-09-29 --size 200

uv run --no-project experiments/bio_tasks/01_discovery/analyze_expansion.py \\
  --baseline-dir docs/experiments/bio-task-generation/01-discovery/data \\
  --expanded-dir docs/experiments/bio-task-generation/01-discovery/data/top200-2026-09-29 \\
  --date 2026-09-29
```

On the shared VM, run analysis inside the nonblocking heavy-work lock and the
resource limits in `AGENTS.md`. This pass used one local worker, no candidate
package execution and no paid compute. Analysis peaked below 50 MiB RSS;
figure generation used Matplotlib 3.10.8 and peaked near 80 MiB.

The retained 200-source lists provide enough additional breadth to justify the
expansion. Source inspection should now determine which of the new scientific
and teaching uses provide observed data, runnable examples and defensible
oracles; diversity labels alone cannot answer that question.
'''])
(base/'ranking-expansion.md').write_text('\n'.join(lines))
print('Wrote expansion report and 400-position additions catalog')
