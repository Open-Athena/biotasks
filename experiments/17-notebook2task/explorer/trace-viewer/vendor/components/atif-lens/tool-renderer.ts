import type * as React from "react"

import type {
  ObservationResult,
  Step,
  ToolCall,
  Trajectory,
} from "@/lib/atif/types"

/** Everything a renderer can use to decide how a tool call should look. */
export interface ToolRendererContext {
  trajectory: Trajectory
  step: Step
  toolCall: ToolCall
  results: ObservationResult[]
}

/** Props passed to the renderer selected for a tool call. */
export interface ToolRendererProps
  extends
    ToolRendererContext,
    Omit<React.ComponentProps<"div">, "children" | "results"> {
  defaultOpen?: boolean
}

/**
 * A custom tool presentation.
 *
 * Renderers are checked in order. Keeping matching separate from rendering
 * makes it straightforward to target a harness, a tool name, an argument
 * shape, or any combination of the three.
 */
export interface ToolRenderer {
  id: string
  matches: (context: ToolRendererContext) => boolean
  component: React.ComponentType<ToolRendererProps>
}

/** Identity helper that preserves inference when declaring a renderer. */
export function defineToolRenderer(renderer: ToolRenderer): ToolRenderer {
  return renderer
}

/** Return the first renderer that claims a tool call. */
export function resolveToolRenderer(
  renderers: readonly ToolRenderer[],
  context: ToolRendererContext
): ToolRenderer | undefined {
  return renderers.find((renderer) => renderer.matches(context))
}
