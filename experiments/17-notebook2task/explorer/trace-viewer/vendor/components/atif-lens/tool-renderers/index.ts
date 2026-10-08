import type { ToolRenderer } from "@/components/atif-lens/tool-renderer"
import { openCodeEditRenderer } from "@/components/atif-lens/tool-renderers/open-code-edit"

/** Built-ins are deliberately ordered: more specific renderers go first. */
export const BUILT_IN_TOOL_RENDERERS: readonly ToolRenderer[] = [
  openCodeEditRenderer,
]

export { openCodeEditRenderer }
