/**
 * Helpers for working with parsed ATIF trajectories: pairing tool calls
 * with observation results, resolving subagent references, aggregating
 * metrics, and formatting values for display.
 */
import type {
  ContentPart,
  MessageContent,
  ObservationResult,
  Step,
  StepSource,
  SubagentTrajectoryRef,
  Trajectory,
} from "@/lib/atif/types"

/** Normalize a message body to an array of content parts. */
export function toContentParts(content: MessageContent): ContentPart[] {
  if (typeof content === "string") return [{ type: "text", text: content }]
  return content
}

/** Flatten a message body to plain text, dropping images. */
export function contentToText(
  content: MessageContent | null | undefined
): string {
  if (content == null) return ""
  if (typeof content === "string") return content
  return content
    .filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("\n")
}

/** Observation results grouped by the tool call they respond to. */
export function toolResultsByCallId(
  step: Step
): Map<string, ObservationResult[]> {
  const byId = new Map<string, ObservationResult[]>()
  const callIds = new Set((step.tool_calls ?? []).map((c) => c.tool_call_id))
  for (const result of step.observation?.results ?? []) {
    if (result.source_call_id == null || !callIds.has(result.source_call_id)) {
      continue
    }
    const bucket = byId.get(result.source_call_id) ?? []
    bucket.push(result)
    byId.set(result.source_call_id, bucket)
  }
  return byId
}

/**
 * Observation results that do not correspond to a tool call in the step
 * (system events, free-form actions, or dangling `source_call_id`s).
 */
export function unmatchedResults(step: Step): ObservationResult[] {
  const callIds = new Set((step.tool_calls ?? []).map((c) => c.tool_call_id))
  return (step.observation?.results ?? []).filter(
    (result) =>
      result.source_call_id == null || !callIds.has(result.source_call_id)
  )
}

/**
 * Resolve a subagent reference against a root trajectory's embedded
 * `subagent_trajectories`. Returns `null` for external (file-path only)
 * references — those need I/O to resolve.
 */
export function resolveSubagentRef(
  root: Trajectory,
  ref: SubagentTrajectoryRef
): Trajectory | null {
  if (ref.trajectory_id == null) return null
  return (
    root.subagent_trajectories?.find(
      (subagent) => subagent.trajectory_id === ref.trajectory_id
    ) ?? null
  )
}

/**
 * Whether a step is intermediate agent activity (tool calls / observations)
 * rather than a conversational beat. Used to fold work into collapsed
 * groups so a trace reads as: user message → ⟨N steps⟩ → response.
 */
export function isActivityStep(step: Step): boolean {
  if (step.source !== "agent") return false
  return (
    (step.tool_calls?.length ?? 0) > 0 ||
    (step.observation?.results.length ?? 0) > 0
  )
}

/** How a step reads at a glance — drives marker colors. */
export type StepKind = "user" | "system" | "agent-tool" | "agent-message"

export function stepKind(step: Step): StepKind {
  if (step.source === "user") return "user"
  if (step.source === "system") return "system"
  return isActivityStep(step) ? "agent-tool" : "agent-message"
}

export type TraceListItem =
  { kind: "step"; step: Step } | { kind: "activity"; steps: Step[] }

/**
 * Fold consecutive activity steps into groups, leaving conversational
 * steps (user, system, and agent responses without tool calls) standalone.
 */
export function groupSteps(steps: Step[]): TraceListItem[] {
  const items: TraceListItem[] = []
  for (const step of steps) {
    const last = items.at(-1)
    if (isActivityStep(step)) {
      if (last?.kind === "activity") last.steps.push(step)
      else items.push({ kind: "activity", steps: [step] })
    } else {
      items.push({ kind: "step", step })
    }
  }
  return items
}

/** Total tool calls across a set of steps. */
export function countToolCalls(steps: Step[]): number {
  return steps.reduce((sum, step) => sum + (step.tool_calls?.length ?? 0), 0)
}

/** The model in effect for a step, falling back to the agent default. */
export function stepModel(trajectory: Trajectory, step: Step): string | null {
  return step.model_name ?? trajectory.agent.model_name ?? null
}

export interface TrajectoryTotals {
  promptTokens: number | null
  completionTokens: number | null
  cachedTokens: number | null
  costUsd: number | null
  steps: number
}

function sumDefined(values: (number | null | undefined)[]): number | null {
  let sum: number | null = null
  for (const value of values) {
    if (value != null) sum = (sum ?? 0) + value
  }
  return sum
}

/**
 * Aggregate metrics for a trajectory. Prefers `final_metrics`, filling
 * gaps by summing per-step metrics.
 */
export function trajectoryTotals(trajectory: Trajectory): TrajectoryTotals {
  const metrics = trajectory.steps.map((step) => step.metrics)
  const final = trajectory.final_metrics
  return {
    promptTokens:
      final?.total_prompt_tokens ??
      sumDefined(metrics.map((m) => m?.prompt_tokens)),
    completionTokens:
      final?.total_completion_tokens ??
      sumDefined(metrics.map((m) => m?.completion_tokens)),
    cachedTokens:
      final?.total_cached_tokens ??
      sumDefined(metrics.map((m) => m?.cached_tokens)),
    costUsd:
      final?.total_cost_usd ?? sumDefined(metrics.map((m) => m?.cost_usd)),
    steps: final?.total_steps ?? trajectory.steps.length,
  }
}

/** Step counts by source, e.g. `{ system: 0, user: 2, agent: 7 }`. */
export function sourceCounts(
  trajectory: Trajectory
): Record<StepSource, number> {
  const counts: Record<StepSource, number> = { system: 0, user: 0, agent: 0 }
  for (const step of trajectory.steps) counts[step.source] += 1
  return counts
}

function parseTimestamp(value: string | null | undefined): number | null {
  if (!value) return null
  const ms = Date.parse(value)
  return Number.isNaN(ms) ? null : ms
}

/** Seconds elapsed from the first timestamped step to this step. */
export function stepOffsetSeconds(
  trajectory: Trajectory,
  step: Step
): number | null {
  const start = parseTimestamp(
    trajectory.steps.find((s) => s.timestamp)?.timestamp
  )
  const current = parseTimestamp(step.timestamp)
  if (start == null || current == null) return null
  return (current - start) / 1000
}

/** Wall-clock duration of the whole trajectory, when timestamps allow. */
export function trajectoryDurationSeconds(
  trajectory: Trajectory
): number | null {
  const stamps = trajectory.steps
    .map((step) => parseTimestamp(step.timestamp))
    .filter((ms): ms is number => ms != null)
  if (stamps.length < 2) return null
  return (Math.max(...stamps) - Math.min(...stamps)) / 1000
}

// --- Display formatting ---------------------------------------------------

/** Compact token count: 982 → "982", 14230 → "14.2k", 2400000 → "2.4M". */
export function formatTokens(count: number): string {
  if (count < 1000) return String(count)
  if (count < 1_000_000) {
    return `${(count / 1000).toFixed(count < 10_000 ? 1 : 0)}k`
  }
  return `${(count / 1_000_000).toFixed(1)}M`
}

/** USD cost with sensible precision: 0.0039 → "$0.0039", 1.5 → "$1.50". */
export function formatCost(usd: number): string {
  if (usd === 0) return "$0"
  if (usd < 0.01) return `$${usd.toFixed(4)}`
  if (usd < 1) return `$${usd.toFixed(3)}`
  return `$${usd.toFixed(2)}`
}

/** Duration in seconds: 4.2 → "4.2s", 154 → "2m 34s", 4000 → "1h 6m". */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`
  }
  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    return `${minutes}m ${Math.round(seconds % 60)}s`
  }
  const hours = Math.floor(seconds / 3600)
  return `${hours}h ${Math.round((seconds % 3600) / 60)}m`
}

/** Time-of-day for step headers, e.g. "14:03:21". */
export function formatTimestamp(iso: string): string | null {
  const ms = parseTimestamp(iso)
  if (ms == null) return null
  return new Date(ms).toLocaleTimeString(undefined, { hour12: false })
}
