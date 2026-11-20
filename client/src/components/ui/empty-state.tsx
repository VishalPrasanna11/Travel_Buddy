import * as React from "react"

import { cn } from "@/lib/utils"

/**
 * EmptyState: what to show when there is nothing yet (no trips, no results,
 * page not found). Title says what's going on; description and actions say
 * what to do next.
 */
type EmptyStateProps = Omit<React.ComponentProps<"div">, "title"> & {
  icon?: React.ComponentType<{ className?: string }>
  title: React.ReactNode
  description?: React.ReactNode
  actions?: React.ReactNode
  /** h2 by default; pass "h1" when the empty state is the whole page. */
  headingLevel?: "h1" | "h2" | "h3"
}

function EmptyState({
  icon: Icon,
  title,
  description,
  actions,
  headingLevel = "h2",
  className,
  children,
  ...props
}: EmptyStateProps) {
  const Heading = headingLevel
  return (
    <div
      data-slot="empty-state"
      className={cn("mx-auto flex w-full max-w-md flex-col items-center px-gutter py-12 text-center", className)}
      {...props}
    >
      {Icon && (
        <span className="mb-4 inline-flex size-12 items-center justify-center rounded-full bg-raspberry-tint text-raspberry">
          <Icon className="size-6" aria-hidden="true" />
        </span>
      )}
      <Heading className="text-title font-semibold">{title}</Heading>
      {description && <div className="mt-2 text-muted-foreground">{description}</div>}
      {actions && <div className="mt-6 flex flex-wrap justify-center gap-3">{actions}</div>}
      {children}
    </div>
  )
}

export { EmptyState }
