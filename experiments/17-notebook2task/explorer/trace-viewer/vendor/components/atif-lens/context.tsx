"use client"

import * as React from "react"

import type { ToolRenderer } from "@/components/atif-lens/tool-renderer"
import type { ImageSource, Step, Trajectory } from "@/lib/atif/types"

export type TextSlot = "message" | "reasoning" | "tool-result" | "notes"

export interface TextRenderContext {
  slot: TextSlot
  step?: Step
}

export interface AtifTraceOptions {
  /**
   * Turn an ATIF image source (file path or URL) into a `src` the browser
   * can load. Defaults to using the path as-is, which works for URLs and
   * for files served relative to the page.
   */
  resolveImageSrc: (source: ImageSource) => string
  /**
   * Render a block of text content. Override to plug in markdown, ANSI
   * colors, syntax highlighting, etc. Defaults to preformatted plain text.
   */
  renderText: (text: string, context: TextRenderContext) => React.ReactNode
  /** Whether collapsible sections (tool calls, subagents) start open. */
  defaultOpen: boolean
  /**
   * Ordered custom presentations for harness/tool combinations. The first
   * matching renderer wins.
   */
  toolRenderers: readonly ToolRenderer[]
}

export interface AtifTraceContextValue extends AtifTraceOptions {
  trajectory: Trajectory
  /** 0 for the root trajectory, +1 for each nested subagent level. */
  depth: number
  /** Renders a nested trajectory; wired up by `AtifTrace`. */
  renderSubagentTrajectory: (trajectory: Trajectory) => React.ReactNode
}

export const AtifTraceContext =
  React.createContext<AtifTraceContextValue | null>(null)

export function useAtifTrace(): AtifTraceContextValue {
  const context = React.useContext(AtifTraceContext)
  if (!context) {
    throw new Error("useAtifTrace must be used within an <AtifTrace>")
  }
  return context
}

export interface TraceStepContextValue {
  step: Step
}

export const TraceStepContext =
  React.createContext<TraceStepContextValue | null>(null)

export function useTraceStep(): TraceStepContextValue {
  const context = React.useContext(TraceStepContext)
  if (!context) {
    throw new Error("useTraceStep must be used within a <TraceStep>")
  }
  return context
}

export function defaultRenderText(text: string): React.ReactNode {
  return (
    <span className="break-words whitespace-pre-wrap" data-slot="atif-text">
      {text}
    </span>
  )
}

export function defaultResolveImageSrc(source: ImageSource): string {
  return source.path
}
