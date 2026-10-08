"use client"

import * as React from "react"
import { ChevronRightIcon } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { useAtifTrace } from "@/components/atif-lens/context"
import { TraceMetric } from "@/components/atif-lens/metrics"
import { TraceStep } from "@/components/atif-lens/step"
import type { Step } from "@/lib/atif/types"
import { countToolCalls, formatCost, formatTokens } from "@/lib/atif/utils"
import { cn } from "@/lib/utils"

/** Anchor id for a group of steps, used by outline/minimap navigation. */
export function stepGroupId(steps: Step[]): string {
  const first = steps[0]?.step_id
  const last = steps.at(-1)?.step_id
  return first === last ? `steps-${first}` : `steps-${first}-${last}`
}

function toolNamesPreview(steps: Step[], limit = 3): string {
  const names: string[] = []
  for (const step of steps) {
    for (const call of step.tool_calls ?? []) {
      if (!names.includes(call.function_name)) names.push(call.function_name)
    }
  }
  const shown = names.slice(0, limit).join(", ")
  const rest = names.length - limit
  return rest > 0 ? `${shown} +${rest}` : shown
}

export interface TraceStepGroupProps extends React.ComponentProps<"div"> {
  /** Consecutive activity steps folded into this group. */
  steps: Step[]
  defaultOpen?: boolean
}

/**
 * A run of intermediate agent activity, collapsed to a single line on the
 * rail so the trace reads as a conversation: user message → ⟨N steps⟩ →
 * response. Expanding reveals the full steps.
 */
export function TraceStepGroup({
  steps,
  defaultOpen,
  className,
  children,
  ...props
}: TraceStepGroupProps) {
  const { defaultOpen: traceDefaultOpen, depth } = useAtifTrace()
  if (steps.length === 0) return null

  const toolCalls = countToolCalls(steps)
  const names = toolNamesPreview(steps)
  const promptTokens = steps.reduce(
    (sum: number | null, step) =>
      step.metrics?.prompt_tokens != null
        ? (sum ?? 0) + step.metrics.prompt_tokens
        : sum,
    null
  )
  const costUsd = steps.reduce(
    (sum: number | null, step) =>
      step.metrics?.cost_usd != null ? (sum ?? 0) + step.metrics.cost_usd : sum,
    null
  )

  return (
    <div
      data-slot="atif-trace-step-group"
      id={depth === 0 ? stepGroupId(steps) : undefined}
      className={cn(
        "grid min-w-0 scroll-mt-24 grid-cols-[0.75rem_1fr] gap-x-3",
        className
      )}
      {...props}
    >
      <div className="flex flex-col items-center" aria-hidden>
        <span
          data-slot="atif-step-dot"
          className="mt-1 size-2 shrink-0 rounded-full border-2 border-chart-2"
        />
        <span
          data-slot="atif-step-rail"
          className="mt-1 w-px flex-1 bg-border"
        />
      </div>
      <div className="flex min-w-0 flex-col pb-8">
        <Collapsible defaultOpen={defaultOpen ?? traceDefaultOpen}>
          <CollapsibleTrigger className="group flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-left font-mono text-xs text-muted-foreground hover:text-foreground">
            <ChevronRightIcon
              className="size-3.5 shrink-0 transition-transform group-data-[panel-open]:rotate-90"
              aria-hidden
            />
            <span className="font-medium">
              {steps.length} {steps.length === 1 ? "step" : "steps"}
            </span>
            {toolCalls > 0 && (
              <span>
                · {toolCalls} {toolCalls === 1 ? "tool call" : "tool calls"}
              </span>
            )}
            {names && <span className="truncate">· {names}</span>}
            <span className="ml-auto inline-flex items-center gap-2.5">
              {promptTokens != null && (
                <TraceMetric label="Prompt tokens across these steps">
                  ↑{formatTokens(promptTokens)}
                </TraceMetric>
              )}
              {costUsd != null && (
                <TraceMetric label="Cost across these steps">
                  {formatCost(costUsd)}
                </TraceMetric>
              )}
            </span>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="flex min-w-0 flex-col pt-4 [&>[data-slot=atif-trace-step]:last-child>div:last-child]:pb-2">
              {children ??
                steps.map((step) => (
                  <TraceStep key={step.step_id} step={step} />
                ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  )
}
