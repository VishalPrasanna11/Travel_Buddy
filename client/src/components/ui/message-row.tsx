import * as React from "react"

import { cn } from "@/lib/utils"

/**
 * MessageRow: one turn in the conversation.
 * - user: compact Soft Pink bubble, right-aligned, so your own words are easy
 *   to find when scrolling back through a long itinerary.
 * - assistant: full reading width with no bubble, because answers are long-form.
 */
type MessageRowProps = React.ComponentProps<"div"> & {
  role: "user" | "assistant"
  /** User's initial; the assistant uses the TravelBuddy mark. */
  initial?: string
  footer?: React.ReactNode
}

function AssistantMark() {
  return (
    <span
      aria-hidden="true"
      className="inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-raspberry text-white"
    >
      <svg className="size-4" viewBox="0 0 24 24" fill="none">
        <path d="M12 2c-4.1 0-7.4 3.2-7.4 7.2C4.6 14.6 12 22 12 22s7.4-7.4 7.4-12.8C19.4 5.2 16.1 2 12 2Z" fill="currentColor" />
        <circle cx="12" cy="9.2" r="2.7" fill="var(--color-raspberry)" />
      </svg>
    </span>
  )
}

function MessageRow({ role, initial, footer, className, children, ...props }: MessageRowProps) {
  if (role === "user") {
    return (
      <div data-slot="message-row" data-role="user" className={cn("flex justify-end", className)} {...props}>
        <div className="flex max-w-[min(85%,36rem)] items-start gap-2">
          <div className="rounded-2xl rounded-tr-md bg-soft-pink px-4 py-2.5 text-base text-ink">
            <span className="sr-only">You said: </span>
            {children}
          </div>
          {initial && (
            <span
              aria-hidden="true"
              className="mt-0.5 hidden size-8 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold text-ink sm:inline-flex"
            >
              {initial}
            </span>
          )}
        </div>
      </div>
    )
  }

  return (
    <div data-slot="message-row" data-role="assistant" className={cn("flex items-start gap-3", className)} {...props}>
      <AssistantMark />
      <div className="min-w-0 flex-1">
        <span className="sr-only">TravelBuddy: </span>
        {children}
        {footer && <div className="mt-2">{footer}</div>}
      </div>
    </div>
  )
}

export { MessageRow, AssistantMark }
