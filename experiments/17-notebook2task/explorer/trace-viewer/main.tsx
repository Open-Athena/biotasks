import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {AtifTrace, TraceHeader, TraceSteps} from './vendor/components/atif-lens/trace';
import {parseTrajectory} from './vendor/lib/atif/schema';
import {HighlightedCode} from './vendor/components/atif-lens/code-block';

import {piTools} from './pi-tools';

const trace = parseTrajectory(JSON.parse(document.getElementById('trajectory-data')!.textContent!));
function App(){
  const [query,setQuery]=useState('');
  const [grouped,setGrouped]=useState(false);
  const [includeSetup,setIncludeSetup]=useState(false);
  const steps=trace.steps.filter(s=>(includeSetup||s.source==='agent')&&(!query||JSON.stringify(s).toLowerCase().includes(query.toLowerCase())));
  return <><div className="viewer-toolbar"><label>Search messages, code and output<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="e.g. DESeq2, error, simplify"/></label><label className="group-toggle"><input type="checkbox" checked={grouped} onChange={e=>setGrouped(e.target.checked)}/>Group intermediate steps</label><label className="group-toggle"><input type="checkbox" checked={includeSetup} onChange={e=>setIncludeSetup(e.target.checked)}/>Show setup messages</label><span>{steps.length} / {trace.steps.length} steps</span></div>
    <AtifTrace toolRenderers={piTools} trace={{...trace,steps}} defaultOpen={false} renderText={(text,context)=> context.slot==='tool-result'?<pre className="terminal-output">{text}</pre>:<div className="markdown"><Markdown remarkPlugins={[remarkGfm]} components={{a:props=><a {...props} target="_blank" rel="noopener noreferrer"/>,code:({className,children,...props})=>className?.startsWith('language-')?<HighlightedCode code={String(children).replace(/\n$/,'')} language={className.slice(9)}/>:<code {...props}>{children}</code>}}>{text}</Markdown></div>}><TraceHeader/><TraceSteps grouped={grouped}/></AtifTrace>
    {!steps.length&&<p>No matching steps. Clear the search to restore the trace.</p>}
    <footer>Viewer: <a href="https://github.com/Eli-Chandler/atif-lens" target="_blank" rel="noopener noreferrer">atif-lens</a> · MIT · bundled locally. This is a saved trace snapshot, not a live connection.</footer></>;
}
createRoot(document.getElementById('root')!).render(<App/>);
