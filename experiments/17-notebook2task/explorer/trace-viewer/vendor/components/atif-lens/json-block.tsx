"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

/**
 * Tokenizes serialized JSON for display. Dependency-free by design: trace
 * arguments are small and regular enough that a full highlighter would be
 * dead weight for consumers of the registry.
 */
const JSON_TOKEN =
  /("(?:[^"\\]|\\.)*")(\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g

function highlightJson(source: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = []
  let cursor = 0
  let key = 0

  for (const match of source.matchAll(JSON_TOKEN)) {
    const index = match.index
    if (index > cursor) {
      nodes.push(
        <span key={key++} className="text-muted-foreground">
          {source.slice(cursor, index)}
        </span>
      )
    }

    const [token, string, colon] = match
    if (string != null) {
      nodes.push(
        <span
          key={key++}
          className={colon ? "text-foreground" : "text-foreground/80"}
        >
          {string}
        </span>
      )
      if (colon) {
        nodes.push(
          <span key={key++} className="text-muted-foreground">
            {colon}
          </span>
        )
      }
    } else {
      nodes.push(
        <span key={key++} className="text-primary">
          {token}
        </span>
      )
    }
    cursor = index + token.length
  }

  if (cursor < source.length) {
    nodes.push(
      <span key={key++} className="text-muted-foreground">
        {source.slice(cursor)}
      </span>
    )
  }
  return nodes
}

export interface JsonBlockProps extends React.ComponentProps<"pre"> {
  value: unknown
}

/** Pretty-printed, softly highlighted JSON. */
export function JsonBlock({ value, className, ...props }: JsonBlockProps) {
  const highlighted = React.useMemo(() => {
    const serialized = JSON.stringify(value, null, 2) ?? "undefined"
    return highlightJson(serialized)
  }, [value])

  return (
    <pre
      data-slot="atif-json-block"
      className={cn(
        "overflow-x-auto rounded-md bg-muted/50 p-3 font-mono text-xs leading-relaxed",
        className
      )}
      {...props}
    >
      <code>{highlighted}</code>
    </pre>
  )
}
