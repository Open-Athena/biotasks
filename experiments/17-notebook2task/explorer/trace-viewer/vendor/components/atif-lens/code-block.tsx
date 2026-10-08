"use client"

import * as React from "react"
import { Highlight } from "prism-react-renderer"
import type { PrismTheme } from "prism-react-renderer"

import { cn } from "@/lib/utils"

/** A colorless theme lets the app's semantic CSS tokens own light/dark mode. */
const SEMANTIC_THEME: PrismTheme = {
  plain: {},
  styles: [],
}

const LANGUAGE_BY_EXTENSION: Record<string, string> = {
  c: "c",
  cc: "cpp",
  cpp: "cpp",
  cs: "csharp",
  css: "css",
  go: "go",
  h: "c",
  hpp: "cpp",
  html: "markup",
  java: "java",
  js: "javascript",
  json: "json",
  jsx: "jsx",
  md: "markdown",
  mjs: "javascript",
  py: "python",
  rb: "ruby",
  rs: "rust",
  sh: "bash",
  sql: "sql",
  ts: "typescript",
  tsx: "tsx",
  xml: "markup",
  yaml: "yaml",
  yml: "yaml",
  zsh: "bash",
}

/** Best-effort Prism language inferred from a file path. */
export function languageFromPath(filePath: string): string {
  const fileName = filePath.split(/[\\/]/).at(-1)?.toLowerCase() ?? ""
  if (fileName === "dockerfile") return "docker"
  if (fileName === "makefile") return "makefile"

  const extension = fileName.includes(".") ? fileName.split(".").at(-1) : null
  return (extension && LANGUAGE_BY_EXTENSION[extension]) || "text"
}

export interface HighlightedCodeProps extends React.ComponentProps<"code"> {
  code: string
  language: string
  showLineNumbers?: boolean
}

/**
 * Syntax-highlighted code with semantic token colors. This is intentionally
 * presentation-only so diff renderers can wrap it in any surface they need.
 */
export function HighlightedCode({
  code,
  language,
  showLineNumbers = false,
  className,
  ...props
}: HighlightedCodeProps) {
  return (
    <Highlight theme={SEMANTIC_THEME} code={code} language={language}>
      {({ tokens, getLineProps, getTokenProps }) => (
        <code
          data-slot="atif-highlighted-code"
          className={cn("block min-w-max", className)}
          {...props}
        >
          {tokens.map((line, lineIndex) => {
            const { style: _lineStyle, ...lineProps } = getLineProps({ line })
            return (
              <span
                key={lineIndex}
                {...lineProps}
                className={cn("block min-h-[1lh]", lineProps.className)}
              >
                {showLineNumbers && (
                  <span
                    className="mr-4 inline-block w-8 text-right text-muted-foreground/55 select-none"
                    aria-hidden
                  >
                    {lineIndex + 1}
                  </span>
                )}
                {line.map((token, tokenIndex) => {
                  const { style: _tokenStyle, ...tokenProps } = getTokenProps({
                    token,
                  })
                  return <span key={tokenIndex} {...tokenProps} />
                })}
              </span>
            )
          })}
        </code>
      )}
    </Highlight>
  )
}
