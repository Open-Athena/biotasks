"use client"

import { EditToolCall } from "@/components/atif-lens/edit-tool-call"
import type { TextEdit } from "@/components/atif-lens/edit-tool-call"
import {
  defineToolRenderer,
  type ToolRendererContext,
  type ToolRendererProps,
} from "@/components/atif-lens/tool-renderer"

function isString(value: unknown): value is string {
  return typeof value === "string"
}

/** Validate and normalize the argument shape emitted by OpenCode's edit tool. */
export function parseOpenCodeEditArguments(
  context: Pick<ToolRendererContext, "trajectory" | "toolCall">
): TextEdit | null {
  const { trajectory, toolCall } = context
  const harness = trajectory.agent.name.toLowerCase().replaceAll(/[\s_-]/g, "")

  if (
    harness !== "opencode" ||
    toolCall.function_name.toLowerCase() !== "edit"
  ) {
    return null
  }

  const { filePath, oldString, newString } = toolCall.arguments
  if (!isString(filePath) || !isString(oldString) || !isString(newString)) {
    return null
  }
  return { filePath, oldString, newString }
}

function OpenCodeEditRenderer(props: ToolRendererProps) {
  const edit = parseOpenCodeEditArguments(props)
  if (!edit) return null
  return <EditToolCall {...props} edit={edit} />
}

export const openCodeEditRenderer = defineToolRenderer({
  id: "opencode/edit",
  matches: (context) => parseOpenCodeEditArguments(context) != null,
  component: OpenCodeEditRenderer,
})
