import json,re
from pathlib import Path
r=Path('/tmp/bio-discovery-20260929/top200')
d=json.loads((r/'screening-decisions.json').read_text())
d['github_exclusions'].update({'patrick-llgc/learning-deep-learning':'General deep-learning reading notes; no biology-specific repository scope.','mir-group/nequip':'General interatomic potentials; materials-modeling scope without a demonstrated biological workflow in this screen.'})
d['pypi_exclusions'].update({
'pycifrw':'General crystallographic file I/O; reviewed project scope does not establish biological analysis.',
'fprime-fpy':'Flight-software sequencing language; sequence keyword is unrelated to biology.',
'vesin-torch':'PyTorch interface to the same general neighbor-list library excluded as vesin.',
'jarvis-tools':'Atomistic materials design.',
'pymatviz':'Materials-informatics visualization.',
'sella':'General atomic saddle-point optimization; no biological scope established.',
'seam':'Current project is a smart-device API; historical metadata does not establish biological scope.',
'nolds':'General nonlinear time-series measures; no dedicated biological workflow in reviewed package scope.',
'pyfai':'General detector-image azimuthal integration for diffraction; biological scope not established.',
'hyperspy':'General multidimensional signal analysis; biological scope not established by reviewed package description.',
'tooluniverse':'General scientific tool/agent integration runtime; same scope rule as excluded general scientific agent platforms.',
'molify':'General atomistic structure construction and molecular simulation interfaces; biological scope not established.',
'structuregraph-helpers':'General structure graph utilities associated with materials modeling.',
'upet':'Interatomic potentials for materials modeling.',
'upd':'General software dependency update tool.',
'visual-genome':'General computer-vision dataset; genome keyword is unrelated to biological genomics.',
'robocrys':'General crystal-structure descriptions for materials.',
'star-magic-program':'Downhole gauge and generic physics/engineering software; no biological scope.',
'linkml-validator':'General schema validation.',
'colormap':'General colormap utilities.',
'pyclustering':'General clustering algorithms.',
'memori':'General AI memory SDK.',
'snntorch':'General brain-inspired machine learning; same exclusion as GitHub screen.',
})
d['bioconda_exclusions']={'munkres':'General assignment algorithm.','fastdtw':'General time-series distance.','java-jdk':'General Java runtime.','sentieon':'Distributed artifacts are proprietary binaries; no code archive or instructional source identified in the package recipe.','r-restfulr':'General REST interface; unlike BioC ecosystem support packages, this is a CRAN general computing utility.'}
(r/'screening-decisions.json').write_text(json.dumps(d,indent=2)+'\n')
# Explicit identity corrections use selected current package descriptions or pinned recipe source URLs.
pypi={
'propka':'https://github.com/jensengroup/propka',
'pyradiomics':'https://github.com/AIM-Harvard/pyradiomics',
'fcsparser':'https://github.com/eyurtsev/fcsparser',
'biolink-model':'https://github.com/biolink/biolink-model',
'bmt':'https://github.com/biolink/biolink-model-toolkit',
'pyensembl':'https://github.com/openvax/pyensembl',
'cg':'https://github.com/Clinical-Genomics/cg',
'smoldyn':'https://github.com/ssandrews/Smoldyn',
'refgenie':'https://github.com/refgenie/refgenie',
'parmed':'https://github.com/ParmEd/ParmEd',
'medspacy-quickumls':'https://github.com/medspacy/quickumls',
}
conda={
'gmap':'http://research-pub.gene.com/gmap/src/gmap-gsnap-2025-07-31.tar.gz',
'clustalw':'https://ftp.ebi.ac.uk/pub/software/clustalw2/2.1/clustalw-2.1.tar.gz',
'clustalo':'http://www.clustal.org/omega/clustal-omega-1.2.4.tar.gz',
'rpsbproc':'https://ftp.ncbi.nih.gov/pub/mmdb/cdd/rpsbproc/20250513_112041/RpsbProc-src.tar.gz',
'gneiss':'https://github.com/biocore/gneiss',
'kalign2':'https://github.com/TimoLassmann/kalign',
'snpsift':'https://github.com/pcingola/SnpSift',
'gatk4-spark':'https://github.com/broadinstitute/gatk',
'perl-bioperl':'https://cpan.metacpan.org/authors/id/C/CJ/CJFIELDS/BioPerl-1.7.8.tar.gz',
'perl-bioperl-core':'https://cpan.metacpan.org/authors/id/C/CJ/CJFIELDS/BioPerl-1.7.8.tar.gz',
}
rows=json.loads((r/'bioconda-screen.json').read_text())['records']
for row in rows:
 p=row['package']
 if not p.startswith('perl-bio') or p in conda:continue
 content=(r.parent/'recipes'/(p+'.yaml')).read_text()
 variables=dict(re.findall(r'{% set (\w+) = ["\']([^"\']+)["\'] %}',content))
 url=re.search(r'^  url: (\S.*)$',content,re.M).group(1)
 for k,v in variables.items():url=url.replace('{{ '+k+' }}',v)
 assert '{{' not in url,(p,url)
 conda[p]=url
(r/'identity-overrides.json').write_text(json.dumps({'pypi':pypi,'bioconda':conda},indent=2)+'\n')
s=(r/'prepare_cohorts.py').read_text()
s=s.replace("decisions=json.loads((out/'screening-decisions.json').read_text())", "decisions=json.loads((out/'screening-decisions.json').read_text())\noverrides=json.loads((out/'identity-overrides.json').read_text())")
s=s.replace("if row.get('exclusion') or row.get('mapping_deferred'):continue", "if row.get('exclusion') or row.get('mapping_deferred') or package in decisions['bioconda_exclusions']:continue")
s=s.replace("if package in conda_overrides:name,url,summary=conda_overrides[package]", "if package in overrides['bioconda']:name,url,summary=package,overrides['bioconda'][package],row.get('summary','')\n    elif package in conda_overrides:name,url,summary=conda_overrides[package]")
s=s.replace("elif name in pypi_overrides:url=pypi_overrides[name]", "elif name in overrides['pypi']:url=overrides['pypi'][name]\n    elif name in pypi_overrides:url=pypi_overrides[name]")
(r/'prepare_cohorts.py').write_text(s)
