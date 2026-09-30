import csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
base=Path('docs/experiments/bio-task-generation/01-discovery');d=json.loads((base/'data/top200-2026-09-29/expansion-results-2026-09-29.json').read_text())
keys=['bioconda','bioconductor','pypi','github'];names=['Bioconda','Bioconductor','PyPI','GitHub stars'];colors=['#377594','#b06a38','#337e63','#87528c'];depths=[100,125,150,175,200]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','svg.hashsalt':'biotasks-depth-20260929','axes.spines.top':False,'axes.spines.right':False})
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12,5),gridspec_kw={'width_ratios':[1.2,1]})
for key,name,color in zip(keys,names,colors):
 r=d['rankings'][key];y=[r['first100']['manual_topic_bins']]+[b['cumulative_diversity']['manual_topic_bins'] for b in r['blocks']]
 ax1.plot(depths,y,color=color,label=name,marker='o',lw=2);ax1.annotate(str(y[-1]),(200,y[-1]),xytext=(7,0),textcoords='offset points',va='center',color=color)
ax1.set_xlim(97,212);ax1.set_xticks(depths);ax1.set_ylim(20,78);ax1.grid(axis='y',alpha=.2);ax1.set_xlabel('Sources retained per ranking');ax1.set_ylabel('Distinct finer topics');ax1.set_title('Topic coverage keeps growing',loc='left',fontweight='bold',pad=16);ax1.legend(frameon=False,loc='upper left')
y=np.arange(4)
for offset,field,label,alpha in [(-.18,'first100','Ranks 1–100',.4),(.18,'second100','Ranks 101–200',1)]:
 vals=[d['rankings'][k][field]['effective_domain_bins'] for k in keys]
 ax2.barh(y+offset,vals,height=.31,color=colors,alpha=alpha,label=label)
 for i,v in enumerate(vals):ax2.text(v+.16,i+offset,f'{v:.1f}',va='center',fontsize=9)
ax2.set_yticks(y,names);ax2.invert_yaxis();ax2.set_xlim(0,16.5);ax2.set_xlabel('Effective primary groups, exp(Shannon entropy)');ax2.set_title('Second hundred is more balanced',loc='left',fontweight='bold',pad=16);ax2.legend(frameon=False,loc='lower left',bbox_to_anchor=(0,-.32),ncol=2)
fig.suptitle('What changes when each source list grows from 100 to 200?',x=.035,ha='left',fontsize=15,fontweight='bold')
fig.text(.035,.018,'Frozen September 29, 2026 rankings • assistant-assigned labels • discovery scope limits apply\nFiner topics include analysis, infrastructure and teaching uses; labels do not measure task quality.',fontsize=9,color='#4b5563')
fig.subplots_adjust(left=.065,right=.96,top=.80,bottom=.23,wspace=.42)
fig.savefig(base/'figures/ranking-expansion-2026-09-29.svg',metadata={'Date':'2026-09-29'})
fig.savefig('/tmp/bio-discovery-20260929/top200/ranking-expansion.png',dpi=140)
print('Saved expansion figure')
