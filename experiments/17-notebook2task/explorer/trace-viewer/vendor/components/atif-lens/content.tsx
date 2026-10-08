"use client"

import * as React from "react"
import { ChevronDownIcon, ChevronUpIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useAtifTrace } from "@/components/atif-lens/context"
import type { TextRenderContext } from "@/components/atif-lens/context"
import type { ImageSource, MessageContent } from "@/lib/atif/types"
import { toContentParts } from "@/lib/atif/utils"
import { cn } from "@/lib/utils"

const COLLAPSE_THRESHOLD = 1200
const COLLAPSE_PREVIEW = 800

export interface TraceTextProps extends React.ComponentProps<"div"> {
  text: string
  context: TextRenderContext
  /**
   * Character count above which the text renders collapsed with an
   * expand control. Pass `Infinity` to always show everything.
   */
  collapseAt?: number
}

/**
 * A block of trace text. Long content (system prompts, tool output)
 * collapses to a preview so hundred-step traces stay scannable.
 */
export function TraceText({
  text,
  context,
  collapseAt = COLLAPSE_THRESHOLD,
  className,
  ...props
}: TraceTextProps) {
  const { renderText } = useAtifTrace()
  const [expanded, setExpanded] = React.useState(false)
  const collapsible = text.length > collapseAt

  const visible =
    collapsible && !expanded ? text.slice(0, COLLAPSE_PREVIEW) : text

  return (
    <div
      data-slot="atif-trace-text"
      className={cn("min-w-0 text-sm", className)}
      {...props}
    >
      <div className={cn(collapsible && !expanded && "relative")}>
        {renderText(visible, context)}
        {collapsible && !expanded && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-background to-transparent" />
        )}
      </div>
      {collapsible && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="mt-1 h-7 text-xs text-muted-foreground"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? (
            <ChevronUpIcon data-icon="inline-start" />
          ) : (
            <ChevronDownIcon data-icon="inline-start" />
          )}
          {expanded
            ? "Show less"
            : `Show all ${text.length.toLocaleString()} characters`}
        </Button>
      )}
    </div>
  )
}

export interface TraceImageProps extends Omit<
  React.ComponentProps<"img">,
  "src" | "alt"
> {
  source: ImageSource
  alt?: string
}

/** An image content part, resolved through the trace's image resolver. */
export function TraceImage({
  source,
  alt,
  className,
  ...props
}: TraceImageProps) {
  const { resolveImageSrc } = useAtifTrace()
  return (
    <img
      data-slot="atif-trace-image"
      src={resolveImageSrc(source)}
      alt={alt ?? source.path}
      className={cn("max-h-96 max-w-full rounded-md border", className)}
      {...props}
    />
  )
}

export interface TraceContentProps extends Omit<
  React.ComponentProps<"div">,
  "content"
> {
  content: MessageContent
  context: TextRenderContext
  collapseAt?: number
}

/** Renders a message body — plain text or multimodal content parts. */
export function TraceContent({
  content,
  context,
  collapseAt,
  className,
  ...props
}: TraceContentProps) {
  const parts = toContentParts(content)
  return (
    <div
      data-slot="atif-trace-content"
      className={cn("flex min-w-0 flex-col gap-2", className)}
      {...props}
    >
      {parts.map((part, index) =>
        part.type === "text" ? (
          <TraceText
            key={index}
            text={part.text}
            context={context}
            collapseAt={collapseAt}
          />
        ) : (
          <TraceImage key={index} source={part.source} />
        )
      )}
    </div>
  )
}
