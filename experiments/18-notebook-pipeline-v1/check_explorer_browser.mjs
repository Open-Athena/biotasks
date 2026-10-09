import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
const targets=await fetch('http://127.0.0.1:43188/json/list').then(r=>r.json());
const socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise((r,j)=>{socket.addEventListener('open',r,{once:true});socket.addEventListener('error',j,{once:true});});
let id=0;const pending=new Map(),contexts=[],errors=[];
socket.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.method==='Runtime.executionContextCreated')contexts.push(m.params.context);if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);if(pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}});
function send(method,params={}){return new Promise((resolve,reject)=>{const key=++id;pending.set(key,{resolve,reject});socket.send(JSON.stringify({id:key,method,params}));});}
async function ev(expression,contextId){const r=await send('Runtime.evaluate',{expression,contextId,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value;}
await send('Runtime.enable');await send('Page.enable');await send('Page.navigate',{url:'file:///tmp/biotasks-18-intake-001/index.html'});
await new Promise(r=>setTimeout(r,1800));
assert.equal(await ev('document.querySelectorAll("article").length'),10);
const opened=await ev(`(()=>{const a=document.querySelector('#scanpy');const d=[...a.querySelectorAll(':scope > details')];for(const x of d)x.querySelector('summary').click();return d.map(x=>({label:x.querySelector('summary').textContent,open:x.open}));})()`);
assert(opened.every(x=>x.open));assert.equal(opened.length,3);
assert.equal(await ev('document.querySelectorAll("iframe").length'),1);
let frame=null;for(const c of contexts){try{const r=await ev('({title:document.title,text:document.body?.innerText?.slice(0,6000),buttons:[...document.querySelectorAll("button")].map(x=>x.textContent)})',c.id);if(r.title==='Recorded Pi attempt')frame={...r,context:c.id};}catch{}}
assert(frame,'iframe execution context exists');assert(frame.text.length>200,'trajectory renders');assert.equal(errors.length,0);
await writeFile('/tmp/biotasks-18-private/explorer-browser-result.json',JSON.stringify({cards:10,opened,frame,errors},null,2)+'\n');socket.close();
