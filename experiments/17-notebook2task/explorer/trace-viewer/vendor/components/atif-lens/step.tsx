"use client"

import * as React from "react"
import { BrainIcon, ChevronRightIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { TraceContent, TraceText } from "@/components/atif-lens/content"
import {
  TraceStepContext,
  useAtifTrace,
  useTraceStep,
} from "@/components/atif-lens/context"
import { StepMetricsSummary } from "@/components/atif-lens/metrics"
import { SubagentRefs } from "@/components/atif-lens/subagent"
import { ToolCall } from "@/components/atif-lens/tool-call"
import type { Step, StepSource } from "@/lib/atif/types"
import {
  contentToText,
  formatTimestamp,
  stepKind,
  stepOffsetSeconds,
  toolResultsByCallId,
  unmatchedResults,
} from "@/lib/atif/utils"
import type { StepKind } from "@/lib/atif/utils"
import { cn } from "@/lib/utils"

const SOURCE_TEXT: Record<StepSource, string> = {
  agent: "text-primary",
  user: "text-foreground",
  system: "text-muted-foreground",
}

/**
 * Marker colors by step kind: conversational agent messages carry the
 * accent, tool-using activity is distinct, user/system stay neutral.
 */
export const STEP_KIND_DOT: Record<StepKind, string> = {
  "agent-message": "bg-primary",
  "agent-tool": "bg-chart-2",
  user: "bg-foreground",
  system: "bg-muted-foreground/60",
}

export interface TraceStepProps extends React.ComponentProps<"article"> {
  step: Step
}

/**
 * One turn of the trajectory, laid out against the trace rail: a
 * source-colored marker, a metadata header, and the step's content.
 */
export function TraceStep({
  step,
  className,
  children,
  ...props
}: TraceStepProps) {
  const { depth } = useAtifTrace()
  const value = React.useMemo(() => ({ step }), [step])

  return (
    <TraceStepContext.Provider value={value}>
      <article
        data-slot="atif-trace-step"
        data-source={step.source}
        id={depth === 0 ? `step-${step.step_id}` : undefined}
        className={cn(
          "grid min-w-0 scroll-mt-24 grid-cols-[0.75rem_1fr] gap-x-3",
          step.is_copied_context && "opacity-70",
          className
        )}
        {...props}
      >
        <div className="flex flex-col items-center" aria-hidden>
          <span
            data-slot="atif-step-dot"
            className={cn(
              "mt-1 size-2 shrink-0 rounded-full",
              STEP_KIND_DOT[stepKind(step)]
            )}
          />
          <span
            data-slot="atif-step-rail"
            className="mt-1 w-px flex-1 bg-border"
          />
        </div>
        <div className="flex min-w-0 flex-col gap-2 pb-8">
          {children ?? (
            <>
              <StepHeader />
              <StepReasoning />
              <StepMessage />
              <StepToolCalls />
              <StepObservation />
            </>
          )}
        </div>
      </article>
    </TraceStepContext.Provider>
  )
}

export interface StepHeaderProps extends React.ComponentProps<"div"> {}

/** Source, step number, per-step badges, metrics, and timing. */
export function StepHeader({ className, children, ...props }: StepHeaderProps) {
  const { trajectory } = useAtifTrace()
  const { step } = useTraceStep()
  const offset = stepOffsetSeconds(trajectory, step)
  const clock = step.timestamp ? formatTimestamp(step.timestamp) : null

  return (
    <div
      data-slot="atif-step-header"
      className={cn(
        "flex flex-wrap items-center gap-x-2 gap-y-1 leading-none",
        className
      )}
      {...props}
    >
      {children ?? (
        <>
          <span
            className={cn(
              "font-mono text-xs font-semibold tracking-widest uppercase",
              SOURCE_TEXT[step.source]
            )}
          >
            {step.source}
          </span>
          <span className="font-mono text-xs text-muted-foreground/70">
            #{step.step_id}
          </span>
          {step.model_name != null &&
            step.model_name !== trajectory.agent.model_name && (
              <Badge variant="outline" className="font-mono">
                {step.model_name}
              </Badge>
            )}
          {step.reasoning_effort != null && (
            <Badge variant="outline" className="font-mono">
              effort {step.reasoning_effort}
            </Badge>
          )}
          {step.llm_call_count != null && step.llm_call_count > 1 && (
            <Badge variant="outline" className="font-mono">
              {step.llm_call_count} llm calls
            </Badge>
          )}
          {step.llm_call_count === 0 && step.source === "agent" && (
            <Badge variant="outline" className="font-mono">
              no llm
            </Badge>
          )}
          {step.is_copied_context && (
            <Badge variant="secondary">copied context</Badge>
          )}
          <span className="ml-auto inline-flex items-center gap-2.5">
            {step.metrics && <StepMetricsSummary metrics={step.metrics} />}
            {(clock || offset != null) && (
              <time
                dateTime={step.timestamp ?? undefined}
                title={step.timestamp ?? undefined}
                className="font-mono text-xs whitespace-nowrap text-muted-foreground/70"
              >
                {offset != null && offset > 0
                  ? `+${offset.toFixed(1)}s`
                  : clock}
              </time>
            )}
          </span>
        </>
      )}
    </div>
  )
}

export interface StepMessageProps extends React.ComponentProps<"div"> {
  collapseAt?: number
}

/**
 * The step's dialogue message. User and system messages sit in a quiet
 * panel; agent messages read as body text.
 */
export function StepMessage({
  collapseAt,
  className,
  ...props
}: StepMessageProps) {
  const { step } = useTraceStep()
  if (
    contentToText(step.message).trim() === "" &&
    typeof step.message === "string"
  ) {
    return null
  }

  return (
    <TraceContent
      data-slot="atif-step-message"
      content={step.message}
      context={{ slot: "message", step }}
      collapseAt={collapseAt}
      className={cn(
        step.source !== "agent" && "rounded-md bg-muted/40 p-3",
        className
      )}
      {...props}
    />
  )
}

export interface StepReasoningProps extends React.ComponentProps<"div"> {
  defaultOpen?: boolean
}

/** The agent's internal reasoning, collapsed when long. */
export function StepReasoning({
  defaultOpen,
  className,
  ...props
}: StepReasoningProps) {
  const { step } = useTraceStep()
  const reasoning = step.reasoning_content
  if (reasoning == null || reasoning.trim() === "") return null

  return (
    <Collapsible
      defaultOpen={defaultOpen ?? reasoning.length <= 280}
      data-slot="atif-step-reasoning"
      render={<div className={cn("min-w-0", className)} {...props} />}
    >
      <CollapsibleTrigger className="group flex items-center gap-1.5 font-mono text-[11px] font-medium tracking-wider text-muted-foreground uppercase hover:text-foreground">
        <ChevronRightIcon
          className="size-3.5 transition-transform group-data-[panel-open]:rotate-90"
          aria-hidden
        />
        <BrainIcon className="size-3.5" aria-hidden />
        Reasoning
        <span className="font-normal normal-case">
          · {reasoning.length.toLocaleString()} chars
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <TraceText
          text={reasoning}
          context={{ slot: "reasoning", step }}
          className="mt-1.5 border-l-2 pl-3 text-muted-foreground"
        />
      </CollapsibleContent>
    </Collapsible>
  )
}

export interface StepToolCallsProps extends React.ComponentProps<"div"> {}

/** Every tool call in the step, each paired with its results. */
export function StepToolCalls({ className, ...props }: StepToolCallsProps) {
  const { step } = useTraceStep()
  const calls = step.tool_calls
  if (!calls || calls.length === 0) return null
  const resultsById = toolResultsByCallId(step)

  return (
    <div
      data-slot="atif-step-tool-calls"
      className={cn("flex min-w-0 flex-col gap-2", className)}
      {...props}
    >
      {calls.map((call) => (
        <ToolCall
          key={call.tool_call_id}
          toolCall={call}
          results={resultsById.get(call.tool_call_id) ?? []}
        />
      ))}
    </div>
  )
}

export interface StepObservationProps extends React.ComponentProps<"div"> {}

/**
 * Observation results that aren't tied to a tool call (system events,
 * free-form actions, dangling references).
 */
export function StepObservation({ className, ...props }: StepObservationProps) {
  const { step } = useTraceStep()
  const results = unmatchedResults(step)
  if (results.length === 0) return null

  return (
    <div
      data-slot="atif-step-observation"
      className={cn("flex min-w-0 flex-col gap-1.5", className)}
      {...props}
    >
      <span className="font-mono text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
        Observation
      </span>
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
