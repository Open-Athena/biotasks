"use client"

import * as React from "react"
import { ArrowRightIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  AtifTraceContext,
  defaultRenderText,
  defaultResolveImageSrc,
  useAtifTrace,
} from "@/components/atif-lens/context"
import type { AtifTraceContextValue } from "@/components/atif-lens/context"
import { TraceText } from "@/components/atif-lens/content"
import { TraceTotalsSummary } from "@/components/atif-lens/metrics"
import { TraceStep } from "@/components/atif-lens/step"
import { TraceStepGroup, stepGroupId } from "@/components/atif-lens/step-group"
import { BUILT_IN_TOOL_RENDERERS } from "@/components/atif-lens/tool-renderers"
import type { ToolRenderer } from "@/components/atif-lens/tool-renderer"
import type { ImageSource, Trajectory } from "@/lib/atif/types"
import { groupSteps } from "@/lib/atif/utils"
import { cn } from "@/lib/utils"

export interface AtifTraceProps extends React.ComponentProps<"section"> {
  /** A parsed ATIF trajectory. Use `parseTrajectory` to validate raw JSON. */
  trace: Trajectory
  /** Whether tool calls and subagents start expanded. Defaults to false. */
  defaultOpen?: boolean
  /** Resolve image content paths to loadable URLs. */
  resolveImageSrc?: (source: ImageSource) => string
  /** Custom text rendering (markdown, ANSI, …). */
  renderText?: AtifTraceContextValue["renderText"]
  /**
   * Custom tool renderers, checked before the built-ins. Use this to add or
   * override presentations for a harness/tool combination.
   */
  toolRenderers?: readonly ToolRenderer[]
}

/**
 * The root ATIF trace view.
 *
 * Renders a complete trajectory on its own:
 *
 * ```tsx
 * <AtifTrace trace={trajectory} />
 * ```
 *
 * or compose the pieces yourself:
 *
 * ```tsx
 * <AtifTrace trace={trajectory}>
 *   <TraceHeader />
 *   <TraceSteps />
 * </AtifTrace>
 * ```
 *
 * Nested instances (rendered for embedded subagent trajectories) inherit
 * options from their parent trace.
 */
export function AtifTrace({
  trace,
  defaultOpen,
  resolveImageSrc,
  renderText,
  toolRenderers,
  className,
  children,
  ...props
}: AtifTraceProps) {
  const parent = React.useContext(AtifTraceContext)
  const depth = parent ? parent.depth + 1 : 0

  const value = React.useMemo<AtifTraceContextValue>(() => {
    const options = {
      resolveImageSrc:
        resolveImageSrc ?? parent?.resolveImageSrc ?? defaultResolveImageSrc,
      renderText: renderText ?? parent?.renderText ?? defaultRenderText,
      defaultOpen: defaultOpen ?? parent?.defaultOpen ?? false,
      toolRenderers:
        toolRenderers != null
          ? [...toolRenderers, ...BUILT_IN_TOOL_RENDERERS]
          : (parent?.toolRenderers ?? BUILT_IN_TOOL_RENDERERS),
    }
    return {
      ...options,
      trajectory: trace,
      depth,
      renderSubagentTrajectory: (subagent) => (
        <AtifTrace trace={subagent} className="gap-3" />
      ),
    }
  }, [
    trace,
    depth,
    defaultOpen,
    resolveImageSrc,
    renderText,
    toolRenderers,
    parent,
  ])

  return (
    <AtifTraceContext.Provider value={value}>
      <section
        data-slot="atif-trace"
        data-depth={depth}
        className={cn("flex min-w-0 flex-col gap-5", className)}
        {...props}
      >
        {children ?? (
          <>
            <TraceHeader />
            <TraceSteps />
          </>
        )}
      </section>
    </AtifTraceContext.Provider>
  )
}

export interface TraceHeaderProps extends React.ComponentProps<"header"> {}

/** Agent identity, schema version, rollup metrics, and notes. */
export function TraceHeader({
  className,
  children,
  ...props
}: TraceHeaderProps) {
  const { trajectory, depth } = useAtifTrace()
  const { agent } = trajectory

  return (
    <header
      data-slot="atif-trace-header"
      className={cn("flex min-w-0 flex-col gap-2", className)}
      {...props}
    >
      {children ?? (
        <>
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            <span
              className={cn(
                "font-medium",
                depth === 0 ? "text-base" : "text-sm"
              )}
            >
              {agent.name}
            </span>
            <span className="text-xs text-muted-foreground">
              v{agent.version}
            </span>
            {agent.model_name != null && (
              <Badge variant="secondary" className="font-mono">
                {agent.model_name}
              </Badge>
            )}
            <Badge variant="outline" className="font-mono">
              {trajectory.schema_version}
            </Badge>
            {trajectory.session_id != null && (
              <span
                className="ml-auto max-w-48 truncate font-mono text-xs text-muted-foreground/70"
                title={`session ${trajectory.session_id}`}
              >
                {trajectory.session_id}
              </span>
            )}
          </div>
          <TraceTotalsSummary trajectory={trajectory} />
          {trajectory.continued_trajectory_ref != null && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ArrowRightIcon className="size-3.5" aria-hidden />
              <span>
                continues in{" "}
                <span className="font-mono">
                  {trajectory.continued_trajectory_ref}
                </span>
              </span>
            </div>
          )}
          {trajectory.notes != null && <TraceNotes />}
          {depth === 0 && <Separator className="mt-2" />}
        </>
      )}
    </header>
  )
}

export interface TraceNotesProps extends React.ComponentProps<"div"> {}

/** The trajectory's free-form notes field. */
export function TraceNotes({ className, ...props }: TraceNotesProps) {
  const { trajectory } = useAtifTrace()
  if (trajectory.notes == null) return null

  return (
    <div
      data-slot="atif-trace-notes"
      className={cn(
        "rounded-md border border-dashed px-3 py-2 text-muted-foreground",
        className
      )}
      {...props}
    >
      <TraceText
        text={trajectory.notes}
        context={{ slot: "notes" }}
        collapseAt={400}
        className="text-xs"
      />
    </div>
  )
}

export interface TraceStepsProps extends React.ComponentProps<"ol"> {
  /**
   * Fold runs of intermediate agent activity (tool calls, observations)
   * into collapsed groups so the trace reads as a conversation. Pass
   * `false` to show every step inline.
   */
  grouped?: boolean
}

/** The step timeline. The rail line stops at the last step. */
export function TraceSteps({
  grouped = true,
  className,
  children,
  ...props
}: TraceStepsProps) {
  const { trajectory } = useAtifTrace()

  return (
    <ol
      data-slot="atif-trace-steps"
      className={cn(
        "flex min-w-0 list-none flex-col",
        "[&>li:last-child_[data-slot=atif-step-rail]]:hidden",
        "[&>li:last-child_[data-slot=atif-trace-step]>div:last-child]:pb-0",
        "[&>li:last-child>[data-slot=atif-trace-step-group]>div:last-child]:pb-0",
        className
      )}
      {...props}
    >
      {children ??
        (grouped
          ? groupSteps(trajectory.steps).map((item) =>
              item.kind === "step" ? (
                <li key={item.step.step_id}>
                  <TraceStep step={item.step} />
                </li>
              ) : (
                <li key={stepGroupId(item.steps)}>
                  <TraceStepGroup steps={item.steps} />
                </li>
              )
            )
          : trajectory.steps.map((step) => (
              <li key={step.step_id}>
                <TraceStep step={step} />
              </li>
            )))}
    </ol>
  )
}
