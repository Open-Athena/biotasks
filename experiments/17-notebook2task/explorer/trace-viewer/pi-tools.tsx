import React from 'react';
import {ToolCallRoot,ToolCallTrigger,ToolCallResults} from './vendor/components/atif-lens/tool-call';
import {CollapsibleContent} from './vendor/components/ui/collapsible';
import {HighlightedCode,languageFromPath} from './vendor/components/atif-lens/code-block';
import type {ToolRenderer,ToolRendererProps} from './vendor/components/atif-lens/tool-renderer';
function PiCodeTool(props:ToolRendererProps){
 const args=props.toolCall.arguments;
 const bash=props.toolCall.function_name==='bash';
 const code=String(bash?args.command:args.content);
 const language=bash?'bash':languageFromPath(String(args.path));
 return <ToolCallRoot toolCall={props.toolCall} results={props.results} defaultOpen={props.defaultOpen}>
  <ToolCallTrigger/><CollapsibleContent><div className="flex flex-col gap-3 border-t p-3">
   <div data-slot="atif-tool-call-arguments"><p className="text-xs text-muted-foreground">{bash?'Command':String(args.path)}{args.timeout?` · timeout ${args.timeout}s`:''}</p><pre className="trace-code"><HighlightedCode code={code} language={language}/></pre></div>
   <ToolCallResults/>
  </div></CollapsibleContent></ToolCallRoot>;
}
export const piTools:ToolRenderer[]=[{id:'pi-code',matches:({trajectory,toolCall})=>trajectory.agent.name==='Pi'&&((toolCall.function_name==='bash'&&typeof toolCall.arguments.command==='string')||(toolCall.function_name==='write'&&typeof toolCall.arguments.content==='string')),component:PiCodeTool}];
