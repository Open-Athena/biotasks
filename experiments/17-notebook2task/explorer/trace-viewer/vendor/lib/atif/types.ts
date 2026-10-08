/**
 * TypeScript types for the Agent Trajectory Interchange Format (ATIF).
 *
 * Mirrors the Harbor reference models (harbor-framework/harbor,
 * src/harbor/models/trajectories) up to ATIF-v1.7.
 *
 * Optional fields may be `null` or absent — producers differ on which they
 * emit, so consumers should treat both the same.
 */

/** Schema versions this library knows about. Unknown versions still parse. */
export const KNOWN_ATIF_VERSIONS = [
  "ATIF-v1.0",
  "ATIF-v1.1",
  "ATIF-v1.2",
  "ATIF-v1.3",
  "ATIF-v1.4",
  "ATIF-v1.5",
  "ATIF-v1.6",
  "ATIF-v1.7",
] as const

export type KnownAtifVersion = (typeof KNOWN_ATIF_VERSIONS)[number]

export type StepSource = "system" | "user" | "agent"

/** Image reference for multimodal content (ATIF-v1.6+). */
export interface ImageSource {
  /** MIME type, e.g. `image/png`. The spec allows jpeg/png/gif/webp. */
  media_type: string
  /** Relative or absolute file path, or a URL. */
  path: string
}

export type ContentPart =
  { type: "text"; text: string } | { type: "image"; source: ImageSource }

/** A message body: plain text, or an array of parts when multimodal. */
export type MessageContent = string | ContentPart[]

export interface ToolCall {
  tool_call_id: string
  function_name: string
  arguments: Record<string, unknown>
  extra?: Record<string, unknown> | null
}

/**
 * Reference to a delegated subagent trajectory. Resolvable via
 * `trajectory_id` (embedded in the root's `subagent_trajectories`) or
 * `trajectory_path` (external file). `session_id` is informational only.
 */
export interface SubagentTrajectoryRef {
  trajectory_id?: string | null
  session_id?: string | null
  trajectory_path?: string | null
  extra?: Record<string, unknown> | null
}

export interface ObservationResult {
  /** Links this result to a `tool_call_id` in the same step, when set. */
  source_call_id?: string | null
  content?: MessageContent | null
  subagent_trajectory_ref?: SubagentTrajectoryRef[] | null
  extra?: Record<string, unknown> | null
}

export interface Observation {
  results: ObservationResult[]
}

/** Per-step LLM operational data. */
export interface StepMetrics {
  prompt_tokens?: number | null
  completion_tokens?: number | null
  cached_tokens?: number | null
  cost_usd?: number | null
  prompt_token_ids?: number[] | null
  completion_token_ids?: number[] | null
  logprobs?: number[] | null
  extra?: Record<string, unknown> | null
}

export interface FinalMetrics {
  total_prompt_tokens?: number | null
  total_completion_tokens?: number | null
  total_cached_tokens?: number | null
  total_cost_usd?: number | null
  total_steps?: number | null
  extra?: Record<string, unknown> | null
}

export interface Step {
  /** Ordinal index of the turn, starting from 1. */
  step_id: number
  /** ISO 8601 timestamp. */
  timestamp?: string | null
  source: StepSource
  /** Overrides the trajectory-level `agent.model_name` for this turn. */
  model_name?: string | null
  reasoning_effort?: string | number | null
  message: MessageContent
  reasoning_content?: string | null
  tool_calls?: ToolCall[] | null
  observation?: Observation | null
  metrics?: StepMetrics | null
  /** Copied from a previous trajectory for context (ATIF-v1.5+). */
  is_copied_context?: boolean | null
  /** Number of LLM inferences this step represents; 0 = deterministic dispatch (ATIF-v1.7). */
  llm_call_count?: number | null
  extra?: Record<string, unknown> | null
}

export interface AgentInfo {
  name: string
  version: string
  model_name?: string | null
  /** OpenAI function-calling style tool definitions. */
  tool_definitions?: Record<string, unknown>[] | null
  extra?: Record<string, unknown> | null
}

export interface Trajectory {
  schema_version: string
  /** Run-scoped identifier; may be shared across related trajectories. */
  session_id?: string | null
  /** Document-unique identifier (ATIF-v1.7); required on embedded subagents. */
  trajectory_id?: string | null
  agent: AgentInfo
  steps: Step[]
  notes?: string | null
  final_metrics?: FinalMetrics | null
  continued_trajectory_ref?: string | null
  extra?: Record<string, unknown> | null
  /** Complete embedded subagent trajectories (ATIF-v1.7). */
  subagent_trajectories?: Trajectory[] | null
}
