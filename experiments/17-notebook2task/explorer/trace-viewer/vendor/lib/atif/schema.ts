/**
 * Zod schema and parsing for ATIF trajectories.
 *
 * Parsing is deliberately lenient where the Harbor reference validator is
 * strict: unknown fields pass through, unknown schema versions parse, and
 * spec conformance issues (non-sequential step ids, dangling
 * `source_call_id`s, …) are reported as warnings by `lintTrajectory` rather
 * than as hard failures. A viewer should render imperfect traces, not
 * reject them.
 */
import { z } from "zod"

import type { Trajectory } from "@/lib/atif/types"
import { KNOWN_ATIF_VERSIONS } from "@/lib/atif/types"

const extraSchema = z.record(z.string(), z.unknown()).nullish()

const imageSourceSchema = z.looseObject({
  media_type: z.string(),
  path: z.string(),
})

const contentPartSchema = z.discriminatedUnion("type", [
  z.looseObject({ type: z.literal("text"), text: z.string() }),
  z.looseObject({ type: z.literal("image"), source: imageSourceSchema }),
])

const messageContentSchema = z.union([z.string(), z.array(contentPartSchema)])

const toolCallSchema = z.looseObject({
  tool_call_id: z.string(),
  function_name: z.string(),
  arguments: z.record(z.string(), z.unknown()),
  extra: extraSchema,
})

const subagentTrajectoryRefSchema = z.looseObject({
  trajectory_id: z.string().nullish(),
  session_id: z.string().nullish(),
  trajectory_path: z.string().nullish(),
  extra: extraSchema,
})

const observationResultSchema = z.looseObject({
  source_call_id: z.string().nullish(),
  content: messageContentSchema.nullish(),
  subagent_trajectory_ref: z.array(subagentTrajectoryRefSchema).nullish(),
  extra: extraSchema,
})

const observationSchema = z.looseObject({
  results: z.array(observationResultSchema),
})

const stepMetricsSchema = z.looseObject({
  prompt_tokens: z.number().int().nullish(),
  completion_tokens: z.number().int().nullish(),
  cached_tokens: z.number().int().nullish(),
  cost_usd: z.number().nullish(),
  prompt_token_ids: z.array(z.number().int()).nullish(),
  completion_token_ids: z.array(z.number().int()).nullish(),
  logprobs: z.array(z.number()).nullish(),
  extra: extraSchema,
})

const finalMetricsSchema = z.looseObject({
  total_prompt_tokens: z.number().int().nullish(),
  total_completion_tokens: z.number().int().nullish(),
  total_cached_tokens: z.number().int().nullish(),
  total_cost_usd: z.number().nullish(),
  total_steps: z.number().int().nullish(),
  extra: extraSchema,
})

const stepSchema = z.looseObject({
  step_id: z.number().int(),
  timestamp: z.string().nullish(),
  source: z.enum(["system", "user", "agent"]),
  model_name: z.string().nullish(),
  reasoning_effort: z.union([z.string(), z.number()]).nullish(),
  message: messageContentSchema,
  reasoning_content: z.string().nullish(),
  tool_calls: z.array(toolCallSchema).nullish(),
  observation: observationSchema.nullish(),
  metrics: stepMetricsSchema.nullish(),
  is_copied_context: z.boolean().nullish(),
  llm_call_count: z.number().int().nullish(),
  extra: extraSchema,
})

const agentInfoSchema = z.looseObject({
  name: z.string(),
  version: z.string(),
  model_name: z.string().nullish(),
  tool_definitions: z.array(z.record(z.string(), z.unknown())).nullish(),
  extra: extraSchema,
})

export const trajectorySchema: z.ZodType<Trajectory> = z.lazy(() =>
  z.looseObject({
    schema_version: z.string(),
    session_id: z.string().nullish(),
    trajectory_id: z.string().nullish(),
    agent: agentInfoSchema,
    steps: z.array(stepSchema).min(1),
    notes: z.string().nullish(),
    final_metrics: finalMetricsSchema.nullish(),
    continued_trajectory_ref: z.string().nullish(),
    extra: extraSchema,
    subagent_trajectories: z.array(trajectorySchema).nullish(),
  })
)

export interface AtifIssue {
  /** Dotted path into the document, e.g. `steps[3].message`. */
  path: string
  message: string
}

export class AtifParseError extends Error {
  readonly issues: AtifIssue[]

  constructor(message: string, issues: AtifIssue[]) {
    super(message)
    this.name = "AtifParseError"
    this.issues = issues
  }
}

function formatPath(path: PropertyKey[]): string {
  if (path.length === 0) return "(root)"
  return path.reduce<string>((acc, key) => {
    if (typeof key === "number") return `${acc}[${key}]`
    return acc ? `${acc}.${String(key)}` : String(key)
  }, "")
}

function toIssues(error: z.ZodError): AtifIssue[] {
  return error.issues.map((issue) => ({
    path: formatPath(issue.path),
    message: issue.message,
  }))
}

export type ParseTrajectoryResult =
  { ok: true; trajectory: Trajectory } | { ok: false; error: AtifParseError }

/**
 * Parse a trajectory without throwing. Accepts a parsed object or a raw
 * JSON string.
 */
export function safeParseTrajectory(input: unknown): ParseTrajectoryResult {
  let data = input
  if (typeof input === "string") {
    try {
      data = JSON.parse(input)
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Invalid JSON document"
      return {
        ok: false,
        error: new AtifParseError(`Not valid JSON: ${message}`, [
          { path: "(root)", message },
        ]),
      }
    }
  }

  const result = trajectorySchema.safeParse(data)
  if (result.success) return { ok: true, trajectory: result.data }

  const issues = toIssues(result.error)
  const preview = issues
    .slice(0, 3)
    .map((issue) => `${issue.path}: ${issue.message}`)
    .join("; ")
  const suffix = issues.length > 3 ? ` (+${issues.length - 3} more)` : ""
  return {
    ok: false,
    error: new AtifParseError(
      `Not a valid ATIF trajectory — ${preview}${suffix}`,
      issues
    ),
  }
}

/**
 * Parse a trajectory from a parsed object or raw JSON string.
 *
 * @throws {AtifParseError} when the input is not a structurally valid
 * ATIF trajectory.
 */
export function parseTrajectory(input: unknown): Trajectory {
  const result = safeParseTrajectory(input)
  if (!result.ok) throw result.error
  return result.trajectory
}

/**
 * Report spec-conformance problems that parsing intentionally tolerates.
 * Mirrors the Harbor reference validators.
 */
export function lintTrajectory(trajectory: Trajectory): AtifIssue[] {
  const issues: AtifIssue[] = []
  const versions: readonly string[] = KNOWN_ATIF_VERSIONS

  if (!versions.includes(trajectory.schema_version)) {
    issues.push({
      path: "schema_version",
      message: `Unknown schema version "${trajectory.schema_version}" — rendering with ATIF-v1.7 semantics`,
    })
  }

  trajectory.steps.forEach((step, i) => {
    const path = `steps[${i}]`
    if (step.step_id !== i + 1) {
      issues.push({
        path: `${path}.step_id`,
        message: `Expected sequential step_id ${i + 1}, got ${step.step_id}`,
      })
    }

    if (step.source !== "agent") {
      for (const field of [
        "model_name",
        "reasoning_effort",
        "reasoning_content",
        "tool_calls",
        "metrics",
      ] as const) {
        if (step[field] != null) {
          issues.push({
            path: `${path}.${field}`,
            message: `Only valid on agent steps, but source is "${step.source}"`,
          })
        }
      }
    }

    if (step.llm_call_count === 0 && step.source === "agent") {
      for (const field of ["metrics", "reasoning_content"] as const) {
        if (step[field] != null) {
          issues.push({
            path: `${path}.${field}`,
            message: "Must be absent when llm_call_count is 0",
          })
        }
      }
    }

    const callIds = new Set(
      (step.tool_calls ?? []).map((call) => call.tool_call_id)
    )
    step.observation?.results.forEach((result, j) => {
      if (
        result.source_call_id != null &&
        !callIds.has(result.source_call_id)
      ) {
        issues.push({
          path: `${path}.observation.results[${j}].source_call_id`,
          message: `References tool_call_id "${result.source_call_id}" not present in this step`,
        })
      }
    })
  })

  const seenIds = new Set<string>()
  trajectory.subagent_trajectories?.forEach((subagent, i) => {
    const path = `subagent_trajectories[${i}]`
    if (subagent.trajectory_id == null) {
      issues.push({
        path: `${path}.trajectory_id`,
        message: "Embedded subagent trajectories must set trajectory_id",
      })
    } else if (seenIds.has(subagent.trajectory_id)) {
      issues.push({
        path: `${path}.trajectory_id`,
        message: `Duplicate trajectory_id "${subagent.trajectory_id}"`,
      })
    } else {
      seenIds.add(subagent.trajectory_id)
    }
  })

  return issues
}
