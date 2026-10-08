"use client"

import * as React from "react"
import {
  BotIcon,
  ChevronRightIcon,
  FilePenIcon,
  FileTextIcon,
  GlobeIcon,
  SearchIcon,
  TerminalIcon,
  WrenchIcon,
} from "lucide-react"

import { JsonBlock } from "@/components/atif-lens/json-block"
import { TraceContent } from "@/components/atif-lens/content"
import { SubagentRefs } from "@/components/atif-lens/subagent"
import { TraceStepContext, useAtifTrace } from "@/components/atif-lens/context"
import { resolveToolRenderer } from "@/components/atif-lens/tool-renderer"
import type {
  ObservationResult,
  ToolCall as ToolCallData,
} from "@/lib/atif/types"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"

/** Best-effort icon for a tool by its function name. */
export function toolIcon(
  functionName: string
): React.ComponentType<React.SVGProps<SVGSVGElement>> {
  const name = functionName.toLowerCase()
  if (/(bash|shell|terminal|command|exec)/.test(name)) return TerminalIcon
  if (/(write|edit|create|patch|apply)/.test(name)) return FilePenIcon
  if (/(read|cat|view|open)/.test(name)) return FileTextIcon
  if (/(search|grep|find|glob|list)/.test(name)) return SearchIcon
  if (/(task|agent|delegate|spawn|dispatch)/.test(name)) return BotIcon
  if (/(web|http|fetch|browse|url)/.test(name)) return GlobeIcon
  return WrenchIcon
}

/** One-line preview of a tool call's arguments for the collapsed header. */
export function formatArgumentsPreview(args: Record<string, unknown>): string {
  const entries = Object.entries(args)
  if (entries.length === 0) return ""
  return entries
    .map(([key, value]) => {
      const rendered = typeof value === "string" ? value : JSON.stringify(value)
      return `${key}: ${rendered ?? ""}`
    })
    .join("  ")
    .replaceAll("\n", "⏎")
}

interface ToolCallContextValue {
  toolCall: ToolCallData
  results: ObservationResult[]
}

const ToolCallContext = React.createContext<ToolCallContextValue | null>(null)

function useToolCall(): ToolCallContextValue {
  const context = React.useContext(ToolCallContext)
  if (!context) {
    throw new Error("Tool call components must be used within a <ToolCall>")
  }
  return context
}

export interface ToolCallProps extends Omit<
  React.ComponentProps<"div">,
  "results"
> {
  toolCall: ToolCallData
  /** Observation results answering this call (matched by `source_call_id`). */
  results?: ObservationResult[]
  defaultOpen?: boolean
}

/** Select a custom renderer, falling back to the generic tool presentation. */
export function ToolCall({
  toolCall,
  results = [],
  defaultOpen,
  className,
  children,
  ...props
}: ToolCallProps) {
  const { trajectory, toolRenderers } = useAtifTrace()
  const step = React.useContext(TraceStepContext)?.step
  const renderer =
    children == null && step != null
      ? resolveToolRenderer(toolRenderers, {
          trajectory,
          step,
          toolCall,
          results,
        })
      : undefined

  if (renderer && step != null) {
    const Renderer = renderer.component
    return (
      <Renderer
        trajectory={trajectory}
        step={step}
        toolCall={toolCall}
        results={results}
        defaultOpen={defaultOpen}
        className={className}
        {...props}
      />
    )
  }

  return (
    <ToolCallRoot
      toolCall={toolCall}
      results={results}
      defaultOpen={defaultOpen}
      className={className}
      {...props}
    >
      {children}
    </ToolCallRoot>
  )
}

/**
 * Renderer-agnostic tool shell. Custom renderers can compose this with the
 * shared trigger and result components without routing through ToolCall again.
 */
export function ToolCallRoot({
  toolCall,
  results = [],
  defaultOpen,
  className,
  children,
  ...props
}: ToolCallProps) {
  const { defaultOpen: traceDefaultOpen } = useAtifTrace()
  const value = React.useMemo(
    () => ({ toolCall, results }),
    [toolCall, results]
  )

  return (
    <ToolCallContext.Provider value={value}>
      <Collapsible
        defaultOpen={defaultOpen ?? traceDefaultOpen}
        data-slot="atif-tool-call"
        render={
          <div
            className={cn("min-w-0 rounded-md border", className)}
            {...props}
          />
        }
      >
        {children ?? (
          <>
            <ToolCallTrigger />
            <CollapsibleContent>
              <div className="flex flex-col gap-3 border-t p-3">
                <ToolCallArguments />
                <ToolCallResults />
              </div>
            </CollapsibleContent>
          </>
        )}
      </Collapsible>
    </ToolCallContext.Provider>
  )
}

export type ToolCallTriggerProps = React.ComponentProps<
  typeof CollapsibleTrigger
> & {
  /** Override the generic JSON-ish argument summary. */
  preview?: React.ReactNode
  /** Full text shown when a custom preview is truncated. */
  previewTitle?: string
}

/** The collapsed one-line summary: icon, name, argument preview, status. */
export function ToolCallTrigger({
  className,
  children,
  preview,
  previewTitle,
  ...props
}: ToolCallTriggerProps) {
  const { toolCall, results } = useToolCall()
  const Icon = toolIcon(toolCall.function_name)

  return (
    <CollapsibleTrigger
      className={cn(
        "group flex w-full min-w-0 items-center gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-muted/50",
        className
      )}
      {...props}
    >
      {children ?? (
        <>
          <ChevronRightIcon
            className="size-4 shrink-0 text-muted-foreground transition-transform group-data-[panel-open]:rotate-90"
            aria-hidden
          />
          <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
          <span className="shrink-0 font-mono font-medium">
            {toolCall.function_name}
          </span>
          <span
            className="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground"
            title={previewTitle}
          >
            {preview ?? formatArgumentsPreview(toolCall.arguments)}
          </span>
          {results.length === 0 && (
            <span
              className="shrink-0 text-xs text-muted-foreground/70"
              title="No observation result recorded for this call"
            >
              no result
            </span>
          )}
        </>
      )}
    </CollapsibleTrigger>
  )
}

export interface ToolCallArgumentsProps extends React.ComponentProps<"div"> {}

/** The call's arguments as highlighted JSON. */
export function ToolCallArguments({
  className,
  ...props
}: ToolCallArgumentsProps) {
  const { toolCall } = useToolCall()
  return (
    <div
      data-slot="atif-tool-call-arguments"
      className={cn("flex min-w-0 flex-col gap-1.5", className)}
      {...props}
    >
      <ToolCallSectionLabel>Arguments</ToolCallSectionLabel>
      <JsonBlock value={toolCall.arguments} />
    </div>
  )
}

export interface ToolCallResultsProps extends React.ComponentProps<"div"> {}

/** The observation results answering this call, including subagents. */
export function ToolCallResults({ className, ...props }: ToolCallResultsProps) {
  const { results } = useToolCall()
  const step = React.useContext(TraceStepContext)?.step

  if (results.length === 0) return null
  return (
    <div
      data-slot="atif-tool-call-results"
      className={cn("flex min-w-0 flex-col gap-1.5", className)}
      {...props}
    >
      <ToolCallSectionLabel>Result</ToolCallSectionLabel>
      {results.map((result, index) => (
        <React.Fragment key={index}>
          {result.content != null && (
            <TraceContent
              content={result.content}
              context={{ slot: "tool-result", step }}
              className="rounded-md bg-muted/50 p-3 font-mono text-xs"
            />
          )}
          {result.subagent_trajectory_ref && (
            <SubagentRefs refs={result.subagent_trajectory_ref} />
          )}
        </React.Fragment>
      ))}
    </div>
  )
}

function ToolCallSectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="font-mono text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
      {children}
    </span>
  )
}
