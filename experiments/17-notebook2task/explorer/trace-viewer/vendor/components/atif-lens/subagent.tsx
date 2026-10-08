"use client"

import * as React from "react"
import { BotIcon, ChevronRightIcon, FileOutputIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { useAtifTrace } from "@/components/atif-lens/context"
import type { SubagentTrajectoryRef } from "@/lib/atif/types"
import { resolveSubagentRef } from "@/lib/atif/utils"
import { cn } from "@/lib/utils"

export interface SubagentRefItemProps extends React.ComponentProps<"div"> {
  subagentRef: SubagentTrajectoryRef
  defaultOpen?: boolean
}

/**
 * A delegated subagent. Embedded trajectories expand inline as a nested
 * trace; external file references render as a labelled chip.
 */
export function SubagentRefItem({
  subagentRef,
  defaultOpen,
  className,
  ...props
}: SubagentRefItemProps) {
  const context = useAtifTrace()
  const resolved = resolveSubagentRef(context.trajectory, subagentRef)

  if (!resolved) {
    const label =
      subagentRef.trajectory_path ??
      subagentRef.trajectory_id ??
      subagentRef.session_id ??
      "unknown"
    return (
      <div
        data-slot="atif-subagent-ref"
        className={cn(
          "flex min-w-0 items-center gap-2 rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground",
          className
        )}
        title="Subagent trajectory stored outside this file"
        {...props}
      >
        <FileOutputIcon className="size-3.5 shrink-0" aria-hidden />
        <span className="truncate font-mono">{label}</span>
        <Badge variant="outline" className="ml-auto shrink-0">
          external
        </Badge>
      </div>
    )
  }

  return (
    <Collapsible
      defaultOpen={defaultOpen ?? context.defaultOpen}
      data-slot="atif-subagent"
      render={
        <div
          className={cn("min-w-0 rounded-md border", className)}
          {...props}
        />
      }
    >
      <CollapsibleTrigger className="group flex w-full min-w-0 items-center gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-muted/50">
        <ChevronRightIcon
          className="size-4 shrink-0 text-muted-foreground transition-transform group-data-[panel-open]:rotate-90"
          aria-hidden
        />
        <BotIcon
          className="size-4 shrink-0 text-muted-foreground"
          aria-hidden
        />
        <span className="truncate font-mono font-medium">
          {resolved.agent.name}
        </span>
        <span className="text-xs text-muted-foreground">
          {resolved.steps.length} steps
        </span>
        <Badge variant="secondary" className="ml-auto shrink-0">
          subagent
        </Badge>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="border-t px-3 py-3 pl-4">
          {context.renderSubagentTrajectory(resolved)}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

export interface SubagentRefsProps extends React.ComponentProps<"div"> {
  refs: SubagentTrajectoryRef[]
}

/** The list of subagent references attached to an observation result. */
export function SubagentRefs({ refs, className, ...props }: SubagentRefsProps) {
  if (refs.length === 0) return null
  return (
    <div
      data-slot="atif-subagent-refs"
      className={cn("flex min-w-0 flex-col gap-2", className)}
      {...props}
    >
      {refs.map((ref, index) => (
        <SubagentRefItem
          key={ref.trajectory_id ?? ref.trajectory_path ?? index}
          subagentRef={ref}
        />
      ))}
    </div>
  )
}
