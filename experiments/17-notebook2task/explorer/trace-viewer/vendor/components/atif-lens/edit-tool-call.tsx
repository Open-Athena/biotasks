"use client"

import * as React from "react"
import { diffLines } from "diff"
import {
  ChevronsDownUpIcon,
  ChevronsUpDownIcon,
  FilePenIcon,
} from "lucide-react"
import { Highlight } from "prism-react-renderer"
import type { PrismTheme, Token } from "prism-react-renderer"

import {
  ToolCallResults,
  ToolCallRoot,
  ToolCallTrigger,
} from "@/components/atif-lens/tool-call"
import {
  HighlightedCode,
  languageFromPath,
} from "@/components/atif-lens/code-block"
import type { ToolRendererProps } from "@/components/atif-lens/tool-renderer"
import { Button } from "@/components/ui/button"
import { CollapsibleContent } from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"

const SEMANTIC_THEME: PrismTheme = { plain: {}, styles: [] }
const CONTEXT_LINES = 3

export interface TextEdit {
  filePath: string
  oldString: string
  newString: string
}

export type EditDiffLineKind = "context" | "remove" | "add"

export interface EditDiffLine {
  kind: EditDiffLineKind
  text: string
  oldLine?: number
  newLine?: number
}

export interface EditDiff {
  lines: EditDiffLine[]
  hasSharedContext: boolean
  additions: number
  deletions: number
}

export interface CollapsedDiffLines {
  kind: "collapsed"
  count: number
}

export type VisibleDiffRow = EditDiffLine | CollapsedDiffLines

function splitChangeLines(value: string): string[] {
  const lines = value.split("\n")
  if (lines.at(-1) === "") lines.pop()
  return lines
}

/** Build line-numbered data for a unified edit view. */
export function buildEditDiff(oldString: string, newString: string): EditDiff {
  let oldLine = 1
  let newLine = 1
  let additions = 0
  let deletions = 0
  let hasSharedContext = false
  const lines: EditDiffLine[] = []

  for (const change of diffLines(oldString, newString)) {
    const changeLines = splitChangeLines(change.value)
    const kind: EditDiffLineKind = change.added
      ? "add"
      : change.removed
        ? "remove"
        : "context"

    for (const text of changeLines) {
      if (kind === "add") {
        lines.push({ kind, text, newLine: newLine++ })
        additions += 1
      } else if (kind === "remove") {
        lines.push({ kind, text, oldLine: oldLine++ })
        deletions += 1
      } else {
        lines.push({ kind, text, oldLine: oldLine++, newLine: newLine++ })
        if (text.trim() !== "") hasSharedContext = true
      }
    }
  }

  return { lines, hasSharedContext, additions, deletions }
}

/** Fold unchanged regions while retaining context around every edit. */
export function compactDiffLines(
  lines: readonly EditDiffLine[],
  contextLines = CONTEXT_LINES
): VisibleDiffRow[] {
  const visible = new Set<number>()
  lines.forEach((line, index) => {
    if (line.kind === "context") return
    for (
      let nearby = Math.max(0, index - contextLines);
      nearby <= Math.min(lines.length - 1, index + contextLines);
      nearby++
    ) {
      visible.add(nearby)
    }
  })

  const rows: VisibleDiffRow[] = []
  for (let index = 0; index < lines.length;) {
    if (visible.has(index)) {
      rows.push(lines[index])
      index += 1
      continue
    }

    const start = index
    while (index < lines.length && !visible.has(index)) index += 1
    rows.push({ kind: "collapsed", count: index - start })
  }
  return rows
}

function fileName(filePath: string): string {
  return filePath.split(/[\\/]/).at(-1) || filePath
}

function lineCount(value: string): number {
  if (value === "") return 0
  return value.split("\n").length
}

export interface EditToolCallProps extends ToolRendererProps {
  edit: TextEdit
}

/**
 * Shared presentation for exact-text replacement tools. Harness adapters only
 * need to validate and map their argument shape into `TextEdit`.
 */
export function EditToolCall({
  edit,
  trajectory: _trajectory,
  step: _step,
  toolCall,
  results,
  defaultOpen,
  className,
  ...props
}: EditToolCallProps) {
  const diff = buildEditDiff(edit.oldString, edit.newString)
  const summary = `${edit.filePath} · ${diff.deletions}− ${diff.additions}+`

  return (
    <ToolCallRoot
      toolCall={toolCall}
      results={results}
      defaultOpen={defaultOpen}
      className={className}
      {...props}
    >
      <ToolCallTrigger preview={summary} previewTitle={edit.filePath} />
      <CollapsibleContent>
        <div className="flex min-w-0 flex-col gap-3 border-t p-3">
          {diff.hasSharedContext ? (
            <UnifiedEditDiff
              filePath={edit.filePath}
              diff={diff}
              language={languageFromPath(edit.filePath)}
            />
          ) : (
            <SearchReplaceEdit
              filePath={edit.filePath}
              oldString={edit.oldString}
              newString={edit.newString}
              language={languageFromPath(edit.filePath)}
            />
          )}
          <ToolCallResults />
        </div>
      </CollapsibleContent>
    </ToolCallRoot>
  )
}

function UnifiedEditDiff({
  filePath,
  diff,
  language,
}: {
  filePath: string
  diff: EditDiff
  language: string
}) {
  const compact = React.useMemo(
    () => compactDiffLines(diff.lines),
    [diff.lines]
  )
  const canExpand = compact.some((line) => line.kind === "collapsed")
  const [expanded, setExpanded] = React.useState(false)
  const rows: VisibleDiffRow[] = expanded ? diff.lines : compact
  const code = rows
    .filter((row): row is EditDiffLine => row.kind !== "collapsed")
    .map((row) => row.text)
    .join("\n")

  return (
    <section
      data-slot="atif-edit-diff"
      className="min-w-0 overflow-hidden rounded-md border bg-muted/20"
    >
      <header className="flex min-w-0 items-center gap-2 border-b px-3 py-2">
        <FilePenIcon
          className="size-3.5 shrink-0 text-muted-foreground"
          aria-hidden
        />
        <span
          className="min-w-0 truncate font-mono text-xs font-medium"
          title={filePath}
        >
          {fileName(filePath)}
        </span>
        <span className="text-xs text-muted-foreground">Unified diff</span>
        <span className="ml-auto font-mono text-xs text-diff-deletion-foreground">
          −{diff.deletions}
        </span>
        <span className="font-mono text-xs text-diff-addition-foreground">
          +{diff.additions}
        </span>
        {canExpand && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 px-1.5 text-[11px] text-muted-foreground"
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? (
              <ChevronsDownUpIcon data-icon="inline-start" />
            ) : (
              <ChevronsUpDownIcon data-icon="inline-start" />
            )}
            {expanded ? "Less context" : "Full context"}
          </Button>
        )}
      </header>
      <pre className="max-h-[32rem] overflow-auto py-1 font-mono text-xs leading-5">
        <Highlight theme={SEMANTIC_THEME} code={code} language={language}>
          {({ tokens, getTokenProps }) => {
            let tokenLine = 0
            return (
              <code
                data-slot="atif-highlighted-code"
                className="block min-w-max"
              >
                {rows.map((row, index) => {
                  if (row.kind === "collapsed") {
                    return (
                      <span
                        key={`collapsed-${index}`}
                        className="grid min-h-7 grid-cols-[3rem_3rem_1.5rem_minmax(max-content,1fr)] items-center bg-muted/40 text-muted-foreground"
                      >
                        <span />
                        <span />
                        <span className="text-center">⋯</span>
                        <span>{row.count} unchanged lines</span>
                      </span>
                    )
                  }

                  const lineTokens = tokens[tokenLine++] ?? ([] as Token[])
                  return (
                    <DiffLine
                      key={`${row.kind}-${row.oldLine ?? "x"}-${row.newLine ?? "x"}-${index}`}
                      line={row}
                      tokens={lineTokens}
                      getTokenProps={getTokenProps}
                    />
                  )
                })}
              </code>
            )
          }}
        </Highlight>
      </pre>
    </section>
  )
}

function DiffLine({
  line,
  tokens,
  getTokenProps,
}: {
  line: EditDiffLine
  tokens: Token[]
  getTokenProps: (input: { token: Token }) => {
    className: string
    children: string
    style?: React.CSSProperties
  }
}) {
  const marker = line.kind === "add" ? "+" : line.kind === "remove" ? "−" : " "
  return (
    <span
      className={cn(
        "grid min-h-5 grid-cols-[3rem_3rem_1.5rem_minmax(max-content,1fr)]",
        line.kind === "add" && "bg-diff-addition",
        line.kind === "remove" && "bg-diff-deletion"
      )}
    >
      <span className="border-r px-2 text-right text-muted-foreground/55 select-none">
        {line.oldLine}
      </span>
      <span className="border-r px-2 text-right text-muted-foreground/55 select-none">
        {line.newLine}
      </span>
      <span
        className={cn(
          "text-center font-semibold select-none",
          line.kind === "add" && "text-diff-addition-foreground",
          line.kind === "remove" && "text-diff-deletion-foreground",
          line.kind === "context" && "text-muted-foreground/55"
        )}
      >
        {marker}
      </span>
      <span className="pr-4">
        {tokens.map((token, index) => {
          const { style: _style, ...props } = getTokenProps({ token })
          return <span key={index} {...props} />
        })}
      </span>
    </span>
  )
}

function SearchReplaceEdit({
  filePath,
  oldString,
  newString,
  language,
}: {
  filePath: string
  oldString: string
  newString: string
  language: string
}) {
  return (
    <section data-slot="atif-search-replace" className="min-w-0">
      <div className="mb-1.5 flex min-w-0 items-center gap-2">
        <FilePenIcon
          className="size-3.5 shrink-0 text-muted-foreground"
          aria-hidden
        />
        <span
          className="min-w-0 truncate font-mono text-xs text-muted-foreground"
          title={filePath}
        >
          {fileName(filePath)}
        </span>
      </div>
      <div className="grid min-w-0 gap-2 md:grid-cols-2">
        <CodePane
          label="Search"
          code={oldString}
          language={language}
          tone="deletion"
        />
        <CodePane
          label="Replace"
          code={newString}
          language={language}
          tone="addition"
        />
      </div>
    </section>
  )
}

function CodePane({
  label,
  code,
  language,
  tone,
}: {
  label: string
  code: string
  language: string
  tone: "addition" | "deletion"
}) {
  return (
    <div
      className={cn(
        "min-w-0 overflow-hidden rounded-md border",
        tone === "addition"
          ? "border-diff-addition-border bg-diff-addition"
          : "border-diff-deletion-border bg-diff-deletion"
      )}
    >
      <div
        className={cn(
          "flex items-center justify-between border-b px-3 py-1.5 font-mono text-[11px] font-semibold tracking-wider uppercase",
          tone === "addition"
            ? "border-diff-addition-border text-diff-addition-foreground"
            : "border-diff-deletion-border text-diff-deletion-foreground"
        )}
      >
        <span>{label}</span>
        <span className="font-normal tracking-normal text-muted-foreground normal-case">
          {lineCount(code)} lines
        </span>
      </div>
      <pre className="max-h-80 overflow-auto p-3 font-mono text-xs leading-5">
        <HighlightedCode code={code} language={language} showLineNumbers />
      </pre>
    </div>
  )
}
