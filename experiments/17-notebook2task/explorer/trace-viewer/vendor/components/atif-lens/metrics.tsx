"use client"

import * as React from "react"

import type { StepMetrics, Trajectory } from "@/lib/atif/types"
import {
  formatCost,
  formatDuration,
  formatTokens,
  sourceCounts,
  trajectoryDurationSeconds,
  trajectoryTotals,
} from "@/lib/atif/utils"
import { cn } from "@/lib/utils"

export interface TraceMetricProps extends React.ComponentProps<"span"> {
  /** Full-precision description shown as the native tooltip. */
  label?: string
}

/** A single compact metric, e.g. `↑ 1.2k` or `$0.0039`. */
export function TraceMetric({
  label,
  className,
  children,
  ...props
}: TraceMetricProps) {
  return (
    <span
      data-slot="atif-trace-metric"
      title={label}
      className={cn(
        "inline-flex items-center gap-1 font-mono text-xs whitespace-nowrap text-muted-foreground",
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}

export interface StepMetricsSummaryProps extends React.ComponentProps<"span"> {
  metrics: StepMetrics
}

/** Token and cost chips for a single step. */
export function StepMetricsSummary({
  metrics,
  className,
  ...props
}: StepMetricsSummaryProps) {
  const cacheRatio =
    metrics.prompt_tokens && metrics.cached_tokens
      ? metrics.cached_tokens / metrics.prompt_tokens
      : null

  return (
    <span
      data-slot="atif-step-metrics"
      className={cn("inline-flex items-center gap-2.5", className)}
      {...props}
    >
      {metrics.prompt_tokens != null && (
        <TraceMetric
          label={`${metrics.prompt_tokens.toLocaleString()} prompt tokens${
            metrics.cached_tokens
              ? ` (${metrics.cached_tokens.toLocaleString()} cached)`
              : ""
          }`}
        >
          ↑{formatTokens(metrics.prompt_tokens)}
        </TraceMetric>
      )}
      {metrics.completion_tokens != null && (
        <TraceMetric
          label={`${metrics.completion_tokens.toLocaleString()} completion tokens`}
        >
          ↓{formatTokens(metrics.completion_tokens)}
        </TraceMetric>
      )}
      {cacheRatio != null && cacheRatio > 0 && (
        <TraceMetric label="Prompt cache hit ratio">
          ⚡{Math.round(cacheRatio * 100)}%
        </TraceMetric>
      )}
      {metrics.cost_usd != null && (
        <TraceMetric label={`$${metrics.cost_usd} USD`}>
          {formatCost(metrics.cost_usd)}
        </TraceMetric>
      )}
    </span>
  )
}

export interface TraceTotalsSummaryProps extends React.ComponentProps<"div"> {
  trajectory: Trajectory
}

/** Whole-trajectory rollup: steps by source, duration, tokens, cost. */
export function TraceTotalsSummary({
  trajectory,
  className,
  ...props
}: TraceTotalsSummaryProps) {
  const totals = trajectoryTotals(trajectory)
  const counts = sourceCounts(trajectory)
  const duration = trajectoryDurationSeconds(trajectory)
  const cacheRatio =
    totals.promptTokens && totals.cachedTokens
      ? totals.cachedTokens / totals.promptTokens
      : null

  return (
    <div
      data-slot="atif-trace-totals"
      className={cn("flex flex-wrap items-center gap-x-3 gap-y-1", className)}
      {...props}
    >
      <TraceMetric
        label={`${counts.agent} agent · ${counts.user} user · ${counts.system} system`}
      >
        {totals.steps} steps
      </TraceMetric>
      {duration != null && (
        <TraceMetric label="Wall-clock duration">
          {formatDuration(duration)}
        </TraceMetric>
      )}
      {totals.promptTokens != null && (
        <TraceMetric
          label={`${totals.promptTokens.toLocaleString()} total prompt tokens${
            totals.cachedTokens
              ? ` (${totals.cachedTokens.toLocaleString()} cached)`
              : ""
          }`}
        >
          ↑{formatTokens(totals.promptTokens)}
        </TraceMetric>
      )}
      {totals.completionTokens != null && (
        <TraceMetric
          label={`${totals.completionTokens.toLocaleString()} total completion tokens`}
        >
          ↓{formatTokens(totals.completionTokens)}
        </TraceMetric>
      )}
      {cacheRatio != null && cacheRatio > 0 && (
        <TraceMetric label="Prompt cache hit ratio">
          ⚡{Math.round(cacheRatio * 100)}%
        </TraceMetric>
      )}
      {totals.costUsd != null && (
        <TraceMetric label={`$${totals.costUsd} USD total`}>
          {formatCost(totals.costUsd)}
        </TraceMetric>
      )}
    </div>
  )
}
