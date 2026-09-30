import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

base=Path('docs/experiments/bio-task-generation/01-discovery');data=json.loads((base/'data/ranking-results-2026-09-29.json').read_text());out=base/'figures'
keys=['bioconda','bioconductor','pypi','github'];names=['Bioconda','Bioconductor','PyPI','GitHub stars']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
domains=['Sequence processing','Genome assembly & annotation','Genetic variation','Gene expression','Single-cell & spatial omics','Gene regulation','Phylogenetics & evolution','Microbiome & metagenomics','RNA structure','Proteomics','Protein structure & biophysics','Cheminformatics & drug discovery','Bioimaging','Neuroscience & behavior','Systems biology & ontologies','Biomedical text & clinical data','General biology & multi-omics','Computing infrastructure']
values=np.array([[data['rankings'][k]['domains'].get(t,0) for k in keys] for t in domains])
fig,ax=plt.subplots(figsize=(8.8,8.3));im=ax.imshow(values,cmap='Blues',vmin=0,vmax=40,aspect='auto')
ax.set_xticks(range(4),names);ax.xaxis.tick_top();ax.tick_params(axis='both',length=0,pad=8);ax.set_yticks(range(len(domains)),domains)
for y in range(len(domains)):
 for x in range(4):ax.text(x,y,str(values[y,x]),ha='center',va='center',color='white' if values[y,x]>=24 else '#273648')
for spine in ax.spines.values():spine.set_visible(False)
fig.suptitle('Primary topics in four top-100 source lists',x=.02,ha='left',fontsize=15,fontweight='bold')
fig.text(.02,.018,'Counts out of 100 • one assistant-assigned primary label per source\nSeptember 29, 2026 • rankings restricted to the recorded discovery scope',fontsize=9,color='#4b5563')
fig.subplots_adjust(left=.43,right=.97,top=.88,bottom=.10)
fig.savefig(out/'ranking-domains-2026-09-29.svg',metadata={'Date':'2026-09-29'});fig.savefig('/tmp/bio-discovery-20260929/top100/ranking-domains.png',dpi=150);plt.close(fig)

kinds=['Software','Infrastructure','Workflow','Research implementation','Resource index','Tutorial/course','Agent instructions','Data resource']
colors=['#3d658a','#a2b6c7','#397f71','#83b1a4','#bb7143','#e4b788','#854b77','#c4a1bb']
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12,5.2),gridspec_kw={'width_ratios':[1,1.5]})
overlap=np.full((4,4),np.nan)
for p in data['pairs']:
 i=keys.index(p['first']);j=keys.index(p['second']);overlap[i,j]=overlap[j,i]=p['intersection']
ax1.imshow(overlap,cmap='Blues',vmin=0,vmax=30);ax1.set_xticks(range(4),names,rotation=32,ha='right');ax1.set_yticks(range(4),names);ax1.tick_params(length=0)
for y in range(4):
 for x in range(4):ax1.text(x,y,'100' if x==y else str(int(overlap[y,x])),ha='center',va='center',color='#6b7280' if x==y else 'white' if overlap[y,x]>=20 else '#273648')
ax1.set_title('Shared sources',loc='left',fontweight='bold',pad=15)
for s in ax1.spines.values():s.set_visible(False)
left=np.zeros(4)
for kind,color in zip(kinds,colors):
 counts=np.array([data['rankings'][k]['source_types'].get(kind,0) for k in keys]);ax2.barh(range(4),counts,left=left,color=color,label=kind)
 for y,count in enumerate(counts):
  if count>=4:ax2.text(left[y]+count/2,y,str(count),ha='center',va='center',color='white' if kind in ['Software','Resource index','Agent instructions','Workflow'] else '#172b3a',fontsize=9)
 left+=counts
ax2.set_xlim(0,100);ax2.set_yticks(range(4),names);ax2.invert_yaxis();ax2.set_xlabel('Sources out of 100');ax2.set_title('Main source type',loc='left',fontweight='bold',pad=15);ax2.legend(loc='upper left',bbox_to_anchor=(0,-.22),ncol=2,frameon=False,fontsize=9)
fig.suptitle('Rankings contribute different sources and source types',x=.02,ha='left',fontsize=15,fontweight='bold')
fig.text(.02,.012,'September 29, 2026 • canonical-source identities • assistant metadata review • GitHub scope includes 24 queries and package-linked sources',fontsize=8,color='#4b5563')
fig.subplots_adjust(left=.11,right=.98,top=.82,bottom=.31,wspace=.50)
fig.savefig(out/'ranking-overlap-types-2026-09-29.svg',metadata={'Date':'2026-09-29'});fig.savefig('/tmp/bio-discovery-20260929/top100/ranking-overlap-types.png',dpi=150);plt.close(fig)
print('Wrote two ranking figures; matplotlib',matplotlib.__version__)
