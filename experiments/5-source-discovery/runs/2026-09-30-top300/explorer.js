"use strict";
(() => {
const D = window.BIOTASKS_DATA;
const M = ["bioconda", "bioconductor", "pypi", "github"];
const N = {bioconda:"Bioconda", bioconductor:"Bioconductor", pypi:"PyPI", github:"GitHub stars"};
const SHORT = {bioconda:"Conda", bioconductor:"Bioc", pypi:"PyPI", github:"GitHub"};
const COLORS = {bioconda:"#267b6e", bioconductor:"#4273bb", pypi:"#b56b21", github:"#8960a1"};
const TYPES = ["Software","Infrastructure","Workflow","Research implementation","Resource index","Tutorial/course","Data resource","Agent instructions","Hardware project","Review/article"];
const TYPE_COLORS = ["#347e78","#a4afb8","#487aae","#8b68a7","#c99947","#cc7861","#74a391","#939269","#ab7090","#7f8795"];
const SCIENTIFIC = new Set(["Software", "Workflow", "Research implementation"]);
const PAIRS = M.flatMap((a,i) => M.slice(i+1).map(b => [a,b]));
const $ = id => document.getElementById(id);
const esc = text => String(text ?? "").replace(/[&<>"']/g, x => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]));
const fmt = x => Number(x).toLocaleString("en-US");
const pct = x => (100*x).toFixed(1)+"%";
const rhoLabel = x => x === null ? "Not defined" : x.toFixed(2);
const safeURL = value => { try { const url = new URL(value); return ["https:","http:"].includes(url.protocol) ? url.href : "#"; } catch { return "#"; } };
const link = (url, text) => `<a href="${esc(safeURL(url))}" target="_blank" rel="noopener noreferrer">${esc(text)} ↗</a>`;
const sourceMap = new Map(D.sources.map(r => [r.id,r]));
const repo = `https://github.com/Open-Athena/biotasks/blob/${D.provenance.checkpoint}/experiments/5-source-discovery/`;
const state = {tab:"explore",depth:300,search:"",type:"",domain:"",topic:"",scientific:false,sort:"bioconda",direction:1,page:0,pageSize:25,selection:null,rankPair:0,adoptionPair:2};
for (const r of D.sources) r.searchText = [r.name,r.alias,r.summary,r.type,r.domain,r.topic,...r.tags,...Object.values(r.ranks).map(x=>x.packages)].join(" ").toLowerCase();

function ranks(values) {
  const sorted = values.map((v,i)=>({v,i})).sort((a,b)=>a.v-b.v);
  const out = Array(values.length);
  for(let i=0;i<sorted.length;) { let j=i+1; while(j<sorted.length && sorted[j].v===sorted[i].v) j++; for(let k=i;k<j;k++) out[sorted[k].i]=(i+j-1)/2; i=j; }
  return out;
}
function pearson(a,b) {
  if(a.length<2) return null;
  const ma=a.reduce((x,y)=>x+y,0)/a.length, mb=b.reduce((x,y)=>x+y,0)/b.length;
  let xy=0,xx=0,yy=0; a.forEach((v,i)=>{const x=v-ma,y=b[i]-mb;xy+=x*y;xx+=x*x;yy+=y*y;});
  return xx && yy ? xy/Math.sqrt(xx*yy) : null;
}
const spearman = (a,b) => pearson(ranks(a),ranks(b));
const selected = (r,m,depth=state.depth) => !!r.ranks[m] && r.ranks[m].rank<=depth;
const mask = (r,depth=state.depth) => M.reduce((bits,m,i)=>bits|(selected(r,m,depth)?1<<i:0),0);
const listCount = r => M.filter(m=>selected(r,m)).length;
function matches(r) {
  return (!state.search || r.searchText.includes(state.search.toLowerCase())) &&
    (!state.type || r.type===state.type) && (!state.domain || r.domain===state.domain) &&
    (!state.topic || r.topic===state.topic) && (!state.scientific || SCIENTIFIC.has(r.type));
}
const filtered = (depth=state.depth) => D.sources.filter(r=>matches(r) && mask(r,depth));
function tableRows() {
  let rows=filtered();
  if(state.selection?.kind==="exact") rows=rows.filter(r=>mask(r)===state.selection.mask);
  if(state.selection?.kind==="pair") rows=rows.filter(r=>state.selection.pair.every(m=>selected(r,m)));
  return rows.sort((a,b)=>{
    let x,y;
    if(M.includes(state.sort)){ x=selected(a,state.sort)?a.ranks[state.sort].rank:null; y=selected(b,state.sort)?b.ranks[state.sort].rank:null; }
    else if(state.sort==="lists"){x=listCount(a);y=listCount(b);}
    else {x=a[state.sort];y=b[state.sort];}
    if(x===null && y!==null) return 1;
    if(y===null && x!==null) return -1;
    const comparison=x===null?0:typeof x==="number"?x-y:String(x).localeCompare(String(y));
    return comparison*state.direction || a.name.localeCompare(b.name);
  });
}
function pairStats(rows,a,b,depth=state.depth) {
  const first=rows.filter(r=>selected(r,a,depth)), second=rows.filter(r=>selected(r,b,depth));
  const shared=rows.filter(r=>selected(r,a,depth)&&selected(r,b,depth));
  const union=new Set([...first,...second].map(r=>r.id)).size;
  return {first:first.length,second:second.length,shared,union,jaccard:union?shared.length/union:null,
    rho:spearman(shared.map(r=>r.ranks[a].rank),shared.map(r=>r.ranks[b].rank))};
}
function setOptions(id,values,first) {
  $(id).innerHTML=(first?`<option value="">${esc(first)}</option>`:"")+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("");
}
function resetSelection(){state.selection=null;state.page=0;}
function showTab(tab) {
  state.tab=tab;
  document.querySelectorAll(".view").forEach(el=>el.hidden=el.id!==tab);
  document.querySelectorAll("[data-tab]").forEach(el=>{ if(el.dataset.tab===tab) el.setAttribute("aria-current","page"); else el.removeAttribute("aria-current"); });
  $("filters").hidden=!["explore","composition","compare"].includes(tab);
  render();
}
function applyType(type){state.type=type;$("type").value=type;resetSelection();render();}
function applyDomain(domain){state.domain=domain;state.topic="";$("domain").value=domain;$("topic").value="";resetSelection();updateTopics();render();}
function inspectSelection(selection){state.selection=selection;state.page=0;showTab("explore");$("membership-filter").scrollIntoView({block:"nearest"});}
function updateTopics(){setOptions("topic",[...new Set(D.sources.filter(r=>!state.domain||r.domain===state.domain).map(r=>r.topic))].sort(),"All finer topics");$("topic").value=state.topic;}
function render() {
  const rows=filtered();
  $("filter-status").innerHTML=`<strong>${fmt(rows.length)}</strong> of ${fmt(D.sources.length)} sources · ${new Set(rows.map(r=>r.domain)).size} primary groups · ${new Set(rows.map(r=>r.topic)).size} finer topics · at least one rank ≤ ${state.depth}`;
  if(state.tab==="explore") renderTable();
  if(state.tab==="composition") renderComposition(rows);
  if(state.tab==="compare") renderComparison(rows);
  if(state.tab==="adoption") renderAdoption();
  if(state.tab==="tail") renderTail();
}
function renderTable() {
  const rows=tableRows(), pages=Math.ceil(rows.length/state.pageSize);
  state.page=Math.min(state.page,Math.max(0,pages-1));
  const start=state.page*state.pageSize, current=rows.slice(start,start+state.pageSize);
  $("source-rows").innerHTML=current.map(r=>`<tr><td><button class="source-name" data-source="${esc(r.id)}">${esc(r.name)}</button><span class="source-summary">${esc(r.summary||r.topic)}</span></td><td><span class="type-badge">${esc(r.type)}</span><span class="domain-text">${esc(r.domain)}<br>${esc(r.topic)}</span></td>${M.map(m=>selected(r,m)?`<td class="rank-cell" title="${esc(N[m])}: rank ${r.ranks[m].rank}; score ${fmt(r.ranks[m].score)}">${r.ranks[m].rank}<span class="rank-bar ${m}" style="width:${Math.max(3,60*(1-(r.ranks[m].rank-1)/state.depth))}px"></span></td>`:`<td class="absent" title="Not selected within this cutoff">—</td>`).join("")}<td class="list-count">${listCount(r)}</td></tr>`).join("") || `<tr><td colspan="7" class="empty">No sources match these filters. Try a broader topic or reset the filters.</td></tr>`;
  $("page-summary").textContent=rows.length?`${start+1}–${Math.min(start+state.pageSize,rows.length)} of ${fmt(rows.length)} sources`:"0 sources";
  $("previous").disabled=state.page===0;$("next").disabled=state.page>=pages-1;
  document.querySelectorAll("[data-sort]").forEach(button=>{
    const key=button.dataset.sort, active=key===state.sort;
    button.parentElement.setAttribute("aria-sort",active?(state.direction===1?"ascending":"descending"):"none");
    const label=N[key]?.replace(" stars","")||({name:"Source",type:"Type / primary group",lists:"Lists"}[key]);
    button.innerHTML=(M.includes(key)?`<span class="dot ${key}"></span>`:"")+esc(label)+(active?(state.direction===1?" ↑":" ↓"):" ↕");
  });
  $("membership-filter").hidden=!state.selection;
  if(state.selection){const s=state.selection;const names=s.kind==="exact"?M.filter((m,i)=>s.mask&(1<<i)).map(m=>N[m]).join(" + "):s.pair.map(m=>N[m]).join(" + ");$("membership-filter").innerHTML=`Table selection: ${s.kind==="exact"?"only these lists":"shared by"} <strong>${esc(names)}</strong> at top ${state.depth}<button id="clear-membership">Clear selection ×</button>`;$("clear-membership").onclick=()=>{resetSelection();renderTable();};}
}
function renderComparison(rows) {
  $("comparison-scope").textContent=`${fmt(rows.length)} filtered sources at top ${state.depth}. List sizes and denominators reflect the filters above.`;
  const mode=$("overlap-mode").value;
  $("overlap").innerHTML=`<table class="matrix"><thead><tr><th></th>${M.map(m=>`<th scope="col">${esc(SHORT[m])}</th>`).join("")}</tr></thead><tbody>${M.map(a=>`<tr><th scope="row">${esc(N[a])}</th>${M.map(b=>{
    const s=pairStats(rows,a,b);
    if(a===b)return `<td><span class="diagonal">${s.first}<small>in list</small></span></td>`;
    const value=mode==="count"?String(s.shared.length):s.jaccard===null?"—":pct(s.jaccard);
    return `<td><button data-overlap="${a},${b}" title="${esc(N[a])} × ${esc(N[b])}: ${s.shared.length} shared / ${s.union} combined; Jaccard ${s.jaccard===null?"undefined":pct(s.jaccard)}" style="background:rgba(0,109,114,${.025+.25*(s.jaccard||0)/.3})">${value}</button></td>`;
  }).join("")}</tr>`).join("")}</tbody></table>`;
  const groups=new Map();rows.forEach(r=>groups.set(mask(r),(groups.get(mask(r))||0)+1));
  const combinations=[...groups].sort((a,b)=>b[1]-a[1]||a[0]-b[0]);
  const maximum=Math.max(1,...groups.values());
  $("intersections").innerHTML=`<div class="upset-head">${M.map(m=>`<span title="${N[m]}">${SHORT[m]}</span>`).join("")}<span>Sources</span><span>n</span></div>`+combinations.map(([bits,n])=>`<button class="intersection" data-mask="${bits}" aria-label="Only ${esc(M.filter((m,i)=>bits&(1<<i)).map(m=>N[m]).join(' and '))}: ${n} sources">${M.map((m,i)=>`<span class="membership-dot ${bits&(1<<i)?"on":""}"></span>`).join("")}<span class="intersection-track"><span style="width:${100*n/maximum}%"></span></span><span class="intersection-value">${n}</span></button>`).join("")+(combinations.length?"":"<p class=\"empty\">No matching sources.</p>");
  renderRank(rows);renderDepth();
}
function scatter(points,xLabel,yLabel,{rank=false,maxRank=300}={}) {
  const w=760,h=390,left=70,right=22,top=25,bottom=58,pw=w-left-right,ph=h-top-bottom;
  const xmax=rank?maxRank:Math.max(1,...points.map(p=>p.x))*1.05;
  const ymax=rank?maxRank:Math.max(1,...points.map(p=>p.y))*1.05;
  const xmin=rank?1:0,ymin=rank?1:0;
  const x=v=>left+(v-xmin)/(xmax-xmin)*pw;
  const y=v=>top+(rank?(v-ymin)/(ymax-ymin):1-(v-ymin)/(ymax-ymin))*ph;
  const ticks=rank?[...new Set([1,...[25,50,100,150,200,250,300].filter(v=>v<=maxRank),maxRank])].sort((a,b)=>a-b):[0,1,2,3,4,5];
  const xt=rank?ticks:ticks.map(i=>i*xmax/5),yt=rank?ticks:ticks.map(i=>i*ymax/5);
  let inner=xt.map(v=>`<line class="grid" x1="${x(v)}" x2="${x(v)}" y1="${top}" y2="${top+ph}"/><text x="${x(v)}" y="${top+ph+21}" text-anchor="middle">${rank?v:v.toFixed(1)}</text>`).join("");
  inner+=yt.map(v=>`<line class="grid" x1="${left}" x2="${left+pw}" y1="${y(v)}" y2="${y(v)}"/><text x="${left-10}" y="${y(v)+4}" text-anchor="end">${rank?v:v.toFixed(1)}</text>`).join("");
  if(rank)inner+=`<line x1="${x(1)}" y1="${y(1)}" x2="${x(maxRank)}" y2="${y(maxRank)}" stroke="#b8c5c2" stroke-dasharray="4 5"/>`;
  inner+=points.map(p=>`<circle class="point" cx="${x(p.x)}" cy="${y(p.y)}" r="4.5" fill="${p.color||COLORS.bioconda}" tabindex="0" role="button" aria-label="${esc(p.title)}" ${p.id?`data-source="${esc(p.id)}"`:`data-adoption-name="${esc(p.name)}"`}><title>${esc(p.title)}</title></circle>`).join("");
  if(!points.length)inner+=`<text x="${left+pw/2}" y="${top+ph/2}" text-anchor="middle">No complete pairs at this selection.</text>`;
  inner+=`<text class="axis-title" x="${left+pw/2}" y="${h-10}" text-anchor="middle">${esc(xLabel)}</text><text class="axis-title" transform="translate(16 ${top+ph/2}) rotate(-90)" text-anchor="middle">${esc(yLabel)}</text>`;
  return `<svg class="chart-svg" viewBox="0 0 ${w} ${h}" role="group" aria-label="${esc(xLabel+' versus '+yLabel)}">${inner}</svg>`;
}
function renderRank(rows) {
  const [a,b]=PAIRS[state.rankPair],s=pairStats(rows,a,b);
  const points=s.shared.map(r=>({id:r.id,x:r.ranks[a].rank,y:r.ranks[b].rank,color:TYPE_COLORS[TYPES.indexOf(r.type)],title:`${r.name}: ${N[a]} rank ${r.ranks[a].rank}, ${N[b]} rank ${r.ranks[b].rank}; ${r.type}`}));
  $("rank-scatter").innerHTML=scatter(points,`${N[a]} rank → lower is better`,`${N[b]} rank → lower is better`,{rank:true,maxRank:state.depth});
  $("rank-summary").innerHTML=`<span>Spearman ρ</span><strong class="rho">${rhoLabel(s.rho)}</strong><strong>${s.shared.length} shared sources</strong><p>${s.first} in ${esc(N[a])}<br>${s.second} in ${esc(N[b])}<br>${s.jaccard===null?"—":pct(s.jaccard)} Jaccard overlap</p><p>${s.shared.length<10?"Very small intersection: interpret cautiously.":"Agreement is conditional on selection in both lists."}</p><p>Rank 1 is at the top left. Dotted line: equal recorded ranks. Color indicates source type.</p><button class="quiet" id="inspect-rank-pair">Inspect shared sources →</button>`;
  $("inspect-rank-pair").onclick=()=>inspectSelection({kind:"pair",pair:[a,b]});
}
function compositionData(rows,field) {
  const cohorts=[...M,"merged"].map(key=>{
    const members=key==="merged"?rows:rows.filter(r=>selected(r,key));
    const counts={};
    for(const r of members) counts[r[field]]=(counts[r[field]]||0)+1;
    return {key,name:key==="merged"?"Merged union":N[key],n:members.length,counts};
  });
  const totals=cohorts.at(-1).counts;
  const categories=Object.keys(totals).sort((a,b)=>totals[b]-totals[a]||a.localeCompare(b));
  return {cohorts,categories};
}
function distributionTable(rows,field,title) {
  const {cohorts,categories}=compositionData(rows,field);
  const percent=$("composition-mode").value==="percent";
  const maximum=percent?1:Math.max(1,...Object.values(cohorts.at(-1).counts));
  const scale=percent?"0–100% of each filtered column":`0–${fmt(maximum)} sources in every column`;
  const header=`<thead><tr><th scope="col">${title}<small>Ordered by merged count</small></th>${cohorts.map(c=>`<th scope="col" data-cohort="${c.key}" class="${c.key==="merged"?"merged-column":""}"><span class="cohort-dot" style="background:${COLORS[c.key]||"#153543"}"></span>${esc(c.name)}<small>n = ${fmt(c.n)} sources</small></th>`).join("")}</tr></thead>`;
  const body=categories.map(category=>`<tr><th scope="row"><button data-${field==="type"?"type":"domain"}="${esc(category)}">${esc(category)}</button></th>${cohorts.map(c=>{
    const count=c.counts[category]||0,share=c.n?count/c.n:null;
    const width=100*(percent?(share||0):count)/maximum;
    return `<td data-cohort="${c.key}" data-count="${count}" data-total="${c.n}" class="${c.key==="merged"?"merged-column":""}" title="${esc(category)} · ${esc(c.name)}: ${count} of ${c.n} sources${share===null?"; no sources in this column":` (${pct(share)})`}"><div class="distribution-value"><strong>${fmt(count)}</strong><span>${share===null?"—":pct(share)}</span></div><div class="distribution-track" aria-hidden="true"><span style="width:${width}%;background:${COLORS[c.key]||"#153543"}"></span></div></td>`;
  }).join("")}</tr>`).join("");
  return {html:`<table class="distribution-table" aria-label="${title} distribution; bars ${scale}">${header}<tbody>${body||'<tr><td colspan="6" class="empty">No sources match these filters. Reset filters to restore the distributions.</td></tr>'}</tbody></table>`,scale};
}
function renderComposition(rows) {
  $("composition-scope").textContent=`${fmt(rows.length)} distinct sources in the filtered union · top ${state.depth} per list.`;
  for(const [id,field,title] of [["types","type","Source type"],["coverage","domain","Primary group"]]) {
    const result=distributionTable(rows,field,title);
    $(id).innerHTML=result.html;
    $(id).nextElementSibling.textContent=`Bar scale: ${result.scale}. Shares sum to 100% in each nonempty column before rounding. — means an empty column, not zero share.`;
  }
}
function depthData() {return [10,25,50,75,100,125,150,175,200,225,250,275,300].map(k=>{const rows=filtered(k);return {k,n:rows.length,topics:new Set(rows.map(r=>r.topic)).size,domains:new Set(rows.map(r=>r.domain)).size};});}
function renderDepth() {
  const points=depthData(), max=Math.max(1,...points.map(p=>p.n));
  const x=k=>58+(k-10)/290*540,y=n=>248-n/max*210;
  let svg=[0,.25,.5,.75,1].map(f=>`<line class="grid" x1="58" x2="598" y1="${y(max*f)}" y2="${y(max*f)}"/><text x="48" y="${y(max*f)+4}" text-anchor="end">${Math.round(max*f)}</text>`).join("");
  svg+=`<path d="${points.map((p,i)=>(i?"L":"M")+x(p.k)+","+y(p.n)).join(" ")}" stroke="${COLORS.bioconda}" stroke-width="2.5" fill="none"/>`;
  svg+=points.map(p=>`<circle cx="${x(p.k)}" cy="${y(p.n)}" r="${p.k===state.depth?6:4}" fill="${COLORS.bioconda}"><title>Top ${p.k}: ${p.n} sources, ${p.domains} primary groups, ${p.topics} finer topics</title></circle>`).join("");
  svg+=[25,50,100,150,200,250,300].map(k=>`<text x="${x(k)}" y="270" text-anchor="middle">${k}</text>`).join("");
  svg+=`<text class="axis-title" x="325" y="297" text-anchor="middle">Depth per list</text><text class="axis-title" transform="translate(14 143) rotate(-90)" text-anchor="middle">Distinct sources in union</text>`;
  $("depth-chart").innerHTML=`<svg class="chart-svg" viewBox="0 0 630 315" role="img" aria-label="Distinct-source accumulation by ranking depth">${svg}</svg>`;
  const first=points.find(p=>p.k===100),last=points.at(-1);
  $("depth-summary").innerHTML=`<table><thead><tr><th>Depth</th><th>Sources</th><th>Groups</th><th>Topics</th></tr></thead><tbody>${points.filter(p=>p.k>=100).map(p=>`<tr class="${p.k===state.depth?"highlight":""}"><td>Top ${p.k}</td><td>${p.n}</td><td>${p.domains}</td><td>${p.topics}</td></tr>`).join("")}</tbody></table><p class="note"><strong>+${last.n-first.n} sources</strong> and <strong>+${last.topics-first.topics} finer labels</strong> from top 100 to top 300 in this filtered union. Label growth describes this annotation scheme, not validated task yield.</p>`;
}
function adoptionStats(a,b){const rows=D.adoption.filter(r=>r.values[a]!==null&&r.values[b]!==null);return {rows,rho:spearman(rows.map(r=>r.values[a]),rows.map(r=>r.values[b]))};}
function renderAdoption() {
  const [a,b]=PAIRS[state.adoptionPair],s=adoptionStats(a,b);
  $("adoption-scatter").innerHTML=scatter(s.rows.map(r=>({name:r.name,x:Math.log10(1+r.values[a]),y:Math.log10(1+r.values[b]),title:`${r.name}: ${N[a]} ${fmt(r.values[a])}; ${N[b]} ${fmt(r.values[b])}`})),`${N[a]} · log₁₀(1 + value)`,`${N[b]} · log₁₀(1 + value)`);
  $("adoption-summary").innerHTML=`<span>Spearman ρ</span><strong class="rho">${rhoLabel(s.rho)}</strong><strong>${s.rows.length} complete pairs / 95</strong><p>${95-s.rows.length} candidates lack at least one measurement in this pair.</p><p>Different observation windows and measurement definitions. Select a dot to see its values and source link.</p>`;
  $("adoption-table").innerHTML=`<table class="plain-table"><thead><tr><th>Measures</th><th>Complete pairs</th><th>Spearman ρ</th></tr></thead><tbody>${PAIRS.map(([x,y],i)=>{const p=adoptionStats(x,y);return `<tr><td><button data-adoption-pair="${i}">${N[x]} × ${N[y]}</button></td><td>${p.rows.length}</td><td>${p.rho===null?"Not defined":p.rho.toFixed(3)}</td></tr>`;}).join("")}</tbody></table>`;
}
function openSource(id) {
  const r=sourceMap.get(id);if(!r)return;
  $("source-detail").innerHTML=`<h2 id="detail-title" class="detail-title">${esc(r.name)}</h2><p>${esc(r.summary)}</p><div class="detail-links">${link(r.url,"Open source")}${r.sourceHead&&r.url.includes("github.com/")?link(r.url.replace(/\/$/,"")+"/tree/"+r.sourceHead,"Recorded revision"):""}</div><p class="detail-meta"><strong>${esc(r.type)}</strong> · ${esc(r.domain)}<br>${esc(r.topic)}</p>${r.note?`<p class="detail-note">${esc(r.note)}</p>`:""}<div class="detail-section"><h3>Recorded top-300 selections</h3><table class="plain-table"><thead><tr><th>Approach</th><th>Rank</th><th>Native score</th><th>Packages</th></tr></thead><tbody>${M.map(m=>{const x=r.ranks[m];return `<tr><td>${N[m]}</td><td>${x?x.rank:"—"}${x&&x.rank>state.depth?" (beyond current cutoff)":""}</td><td>${x?fmt(x.score):"—"}</td><td>${x?esc(x.packages||"—"):"—"}</td></tr>`;}).join("")}</tbody></table><p>Scores use each approach’s own units and window; they are not directly comparable. — means not in that stored top-300 list.</p></div><div class="detail-section"><h3>Recorded metadata</h3><p>GitHub stars: ${r.stars===null?"not available":fmt(r.stars)}${r.archived===true?" · archived at observation":""}<br>Canonical identity: <code>${esc(r.id)}</code></p><div class="tags">${r.tags.length?r.tags.map(t=>`<span>${esc(t)}</span>`).join(""):"<span>No recorded GitHub topic tags</span>"}</div></div><div class="detail-section"><h3>Annotation evidence</h3><p>${[...new Set(r.evidence)].map(url=>link(url,url)).join("<br>")}</p><p>Labels are assistant-assigned from recorded metadata and selected README checks; no independent human validation is claimed.</p></div>`;
  $("source-dialog").showModal();
}
function openAdoption(name) {
  const r=D.adoption.find(r=>r.name===name);if(!r)return;
  $("source-detail").innerHTML=`<h2 id="detail-title" class="detail-title">${esc(r.name)}</h2><p>Original 95-source adoption cohort</p><div class="detail-links">${link(r.url,"Open source")}</div><table class="plain-table"><thead><tr><th>Measure</th><th>Value</th></tr></thead><tbody>${M.map(m=>`<tr><td>${N[m]}</td><td>${r.values[m]===null?"Missing":fmt(r.values[m])}</td></tr>`).join("")}</tbody></table><p class="footnote">This inventory observation is separate from the top-300 selections. Registry scores retain their original definitions and windows.</p>`;
  $("source-dialog").showModal();
}
function csvContent(rows) {
  const cell=v=>`"${String(v??"").replace(/"/g,'""')}"`;
  const header=["source_id","name","source_url","source_type","primary_group","finer_topic",...M.map(m=>m+"_rank"),...M.map(m=>m+"_score")];
  return [header,...rows.map(r=>[r.id,r.name,r.url,r.type,r.domain,r.topic,...M.map(m=>selected(r,m)?r.ranks[m].rank:""),...M.map(m=>selected(r,m)?r.ranks[m].score:"")])].map(row=>row.map(cell).join(",")).join("\r\n")+"\r\n";
}
function exportCSV(){const blob=new Blob([csvContent(tableRows())],{type:"text/csv;charset=utf-8"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=`biotasks-sources-top${state.depth}-filtered.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

const TAIL_BANDS=["0","1","2–5","6–10",">10"];
const TAIL_COLORS=["#e4e8ea","#be7b56","#d5ad56","#84aaa2","#326e67"];
const band = n => n===0?"0":n===1?"1":n<=5?"2–5":n<=10?"6–10":">10";
function tailData(cohort) {
  const groups=[...new Set(D.sources.map(r=>r.domain))].sort();
  return [100,200,300].map(k=>{
    const members=D.sources.filter(r=>cohort==="merged"?!!mask(r,k):selected(r,cohort,k));
    const counts=Object.fromEntries(groups.map(g=>[g,0]));
    for(const r of members) counts[r.domain]++;
    const bands=Object.fromEntries(TAIL_BANDS.map(b=>[b,0]));
    Object.values(counts).forEach(n=>bands[band(n)]++);
    return {k,n:members.length,counts,bands};
  });
}
function renderTail() {
  const cohort=$("tail-cohort").value, focus=$("tail-focus").value, share=$("tail-scale").value==="share";
  $("tail-legend").innerHTML=TAIL_BANDS.map((b,i)=>`<span><i style="background:${TAIL_COLORS[i]}"></i>${b==="0"?"Absent":b+" sources"}</span>`).join("");
  $("tail-overview").innerHTML=[...M,"merged"].map(m=>`<div class="tail-card ${cohort===m?"active":""}"><button data-tail-cohort="${m}" aria-pressed="${cohort===m}">${m==="merged"?"Merged union":N[m]}</button>${tailData(m).map(d=>`<div class="tail-band-row"><span>Top ${d.k}</span><div class="tail-band" aria-label="${esc(TAIL_BANDS.map(b=>`${b} sources: ${d.bands[b]} groups`).join('; '))}">${TAIL_BANDS.filter(b=>d.bands[b]).map(b=>`<span data-band="${b}" data-groups="${d.bands[b]}" style="width:${100*d.bands[b]/22}%;background:${TAIL_COLORS[TAIL_BANDS.indexOf(b)]}" title="${b} sources: ${d.bands[b]} groups">${d.bands[b]}</span>`).join("")}</div><small>${22-d.bands["0"]}/22 represented · n=${fmt(d.n)}</small></div>`).join("")}</div>`).join("");
  const data=tailData(cohort), initial=data[0], last=data[2];
  const groups=Object.keys(initial.counts).filter(g=>focus==="all" || (focus==="sparse100"&&initial.counts[g]<=5) || (focus==="fixed"&&initial.counts[g]>=1&&initial.counts[g]<=5) || (focus==="new"&&initial.counts[g]===0) || (focus==="current"&&last.counts[g]>=1&&last.counts[g]<=5)).sort((a,b)=>initial.counts[a]-initial.counts[b]||last.counts[b]-last.counts[a]||a.localeCompare(b));
  const maximum=Math.max(1e-12,...groups.flatMap(g=>data.map(d=>share?d.counts[g]/d.n:d.counts[g])));
  $("tail-detail-title").textContent=`${cohort==="merged"?"Merged union":N[cohort]} · ${groups.length} groups to follow`;
  $("tail-detail-note").textContent=`Same groups across all three columns. Ordered by top-100 count, then top-300 count. Counts and shares are shown together.`;
  $("tail-detail").innerHTML=`<table class="distribution-table tail-table"><thead><tr><th>Primary group / status</th>${data.map(d=>`<th>Top ${d.k}<small>n = ${fmt(d.n)} sources</small></th>`).join("")}<th>Added 200 → 300</th></tr></thead><tbody>${groups.map(g=>`<tr data-group="${esc(g)}"><th><button data-tail-group="${esc(g)}">${esc(g)}</button><small>${initial.counts[g]===0?(last.counts[g]===0?"Absent at every cutoff":"Newly represented after 100"):initial.counts[g]<=5?"Fixed top-100 tail":"Above 5 at top 100"}</small></th>${data.map(d=>`<td data-depth="${d.k}" data-count="${d.counts[g]}" data-total="${d.n}"><div class="distribution-value"><strong>${d.counts[g]}</strong><span>${pct(d.counts[g]/d.n)}</span></div><div class="distribution-track"><span style="width:${100*(share?d.counts[g]/d.n:d.counts[g])/maximum}%;background:${cohort==="merged"?"#326e67":COLORS[cohort]}"></span></div></td>`).join("")}<td class="tail-delta">+${last.counts[g]-data[1].counts[g]}</td></tr>`).join("") || '<tr><td colspan="5" class="empty">No groups meet this definition.</td></tr>'}</tbody></table>`;
  $("tail-scale-note").textContent=`Common bar scale across every displayed cell: 0–${share?pct(maximum):fmt(maximum)+" sources"}. The scale updates when the cohort or group subset changes.`;
  $("tail-overview").querySelectorAll('[data-tail-cohort]').forEach(b=>b.onclick=()=>{$("tail-cohort").value=b.dataset.tailCohort;renderTail();});
  $("tail-detail").querySelectorAll('[data-tail-group]').forEach(b=>b.onclick=()=>{$("reset").click();applyDomain(b.dataset.tailGroup);showTab("explore");});
}

function renderMethods() {
  $("method-definitions").innerHTML=`<dl><dt>Bioconda</dt><dd>Cumulative recorded downloads across builds and platforms. Source score is the maximum package counter mapped to that source, not a sum or a unique-user estimate.</dd><dt>Bioconductor</dt><dd>Average monthly distinct IPs over September 2025–August 2026; provider table as of September 28, 2026.</dd><dt>PyPI</dt><dd>August 30–September 28, 2026 downloads in the saved ClickHouse query, excluding four known mirror installer strings. Maximum package count per source. This is not the complete PyPIStats filtering pipeline.</dd><dt>GitHub stars</dt><dd>Recorded stars within the observed and screened source universe, frozen when expanding the lists. This is not a global biology ranking.</dd></dl>`;
  $("adoption-report").href=repo+"baseline/adoption.md";
  $("evidence-links").innerHTML=`<ul><li>${link(repo+"runs/2026-09-30-top300/README.md","Top-300 depth and primary-group tail report")}</li><li>${link(repo+"runs/2026-09-30-top300/primary-group-depths.csv","All primary-group counts and shares at 100 / 200 / 300")}</li><li>${link(repo+"runs/2026-09-30-discovery-gaps/README.md","Known-repository discovery gap audit")}</li><li>${link(repo+"baseline/ranking-expansion.md","Top-200 expansion report")}</li><li>${link(repo+"baseline/ranking-comparison.md","Original top-100 comparison")}</li><li>${link(repo+"baseline/adoption.md","95-source adoption analysis and sensitivity checks")}</li><li>${link(repo+"baseline/data/top200-2026-09-29/ranking-provenance-2026-09-29.json","Collection methods, candidate universes and corrections")}</li><li>${link(repo+"runs/2026-09-30-explorer/README.md","Explorer build and validation workflow")}</li><li>${link("https://huggingface.co/buckets/open-athena/biotasks","Retained provider cache")}</li></ul><p>Build input checkpoint: <code>${esc(D.provenance.checkpoint)}</code>. Snapshot label: ${esc(D.snapshot)}; collection and identity corrections have their own timestamps in the provenance. First-200 IDs, scores and labels remain unchanged; new identity metadata and annotations support the top-300 expansion.</p><details><summary>Embedded input checksums</summary><table class="plain-table provenance-table"><thead><tr><th>Input relative to this study</th><th>SHA-256</th></tr></thead><tbody>${D.provenance.inputs.map(item=>`<tr><td>${esc(item.path)}</td><td><code>${esc(item.sha256)}</code></td></tr>`).join("")}</tbody></table></details>`;
}
setOptions("type",TYPES,"All source types");setOptions("domain",[...new Set(D.sources.map(r=>r.domain))].sort(),"All primary groups");updateTopics();
for(const id of ["rank-pair","adoption-pair"])$(id).innerHTML=PAIRS.map(([a,b],i)=>`<option value="${i}">${N[a]} × ${N[b]}</option>`).join("");
$("adoption-pair").value=state.adoptionPair;
document.querySelectorAll("[data-tab]").forEach(b=>b.onclick=()=>showTab(b.dataset.tab));
$("search").oninput=()=>{state.search=$("search").value.trim();resetSelection();render();};
for(const key of ["type","domain","topic","depth"])$(key).onchange=()=>{state[key]=key==="depth"?Number($(key).value):$(key).value;if(key==="domain"){state.topic="";updateTopics();}resetSelection();render();};
$("scientific").onchange=()=>{state.scientific=$("scientific").checked;resetSelection();render();};
$("reset").onclick=()=>{Object.assign(state,{search:"",type:"",domain:"",topic:"",scientific:false,depth:300,page:0,selection:null});for(const id of ["search","type","domain","topic"])$(id).value="";$("depth").value="300";$("scientific").checked=false;updateTopics();render();};
document.querySelectorAll("[data-sort]").forEach(b=>b.onclick=()=>{const sort=b.dataset.sort;state.direction=sort===state.sort?-state.direction:sort==="lists"?-1:1;state.sort=sort;state.page=0;renderTable();});
$("page-size").onchange=()=>{state.pageSize=Number($("page-size").value);state.page=0;renderTable();};
$("previous").onclick=()=>{state.page--;renderTable();};$("next").onclick=()=>{state.page++;renderTable();};$("export").onclick=exportCSV;
$("overlap-mode").onchange=()=>renderComparison(filtered());
$("composition-mode").onchange=()=>renderComposition(filtered());
$("rank-pair").onchange=()=>{state.rankPair=Number($("rank-pair").value);renderRank(filtered());};
$("adoption-pair").onchange=()=>{state.adoptionPair=Number($("adoption-pair").value);renderAdoption();};
$("close-dialog").onclick=()=>$("source-dialog").close();
document.addEventListener("click",event=>{
  const target=event.target.closest("[data-source],[data-mask],[data-overlap],[data-type],[data-domain],[data-adoption-name],[data-adoption-pair]");if(!target)return;
  if(target.dataset.source)openSource(target.dataset.source);
  else if(target.dataset.mask)inspectSelection({kind:"exact",mask:Number(target.dataset.mask)});
  else if(target.dataset.overlap)inspectSelection({kind:"pair",pair:target.dataset.overlap.split(",")});
  else if(target.dataset.type)applyType(target.dataset.type);
  else if(target.dataset.domain)applyDomain(target.dataset.domain);
  else if(target.dataset.adoptionName)openAdoption(target.dataset.adoptionName);
  else if(target.dataset.adoptionPair!==undefined){state.adoptionPair=Number(target.dataset.adoptionPair);$("adoption-pair").value=state.adoptionPair;renderAdoption();}
});
document.addEventListener("keydown",event=>{if(["Enter"," "].includes(event.key)&&event.target.matches("svg .point")){event.preventDefault();event.target.dispatchEvent(new MouseEvent("click",{bubbles:true}));}});
for(const id of ["tail-cohort","tail-focus","tail-scale"]) $(id).onchange=renderTail;
renderMethods();render();
// Expose the pure calculations for research-side numerical checks, without a server.
window.DiscoveryExplorer={data:D,state,filtered,tableRows,pairStats,adoptionStats,depthData,compositionData,tailData,spearman,csvContent,render,showTab};
})();
