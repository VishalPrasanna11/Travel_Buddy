import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/**
 * Badge / Chip. Text is always ink or white so every variant passes AA.
 * Category variants follow the palette roles in DESIGN.md:
 * flight = Teal Blue, stay = Amber, success = Leaf Green,
 * estimate = Sunshine Yellow, subtle = Soft Pink.
 */
const badgeVariants = cva(
  [
    "inline-flex w-fit shrink-0 items-center justify-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5",
    "text-xs font-medium transition-colors [&>svg]:pointer-events-none [&>svg]:size-3.5",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
  ].join(" "),
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground [a&]:hover:bg-raspberry-hover",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-danger-tint text-destructive",
        outline: "border-border bg-background text-foreground [a&]:hover:bg-muted",
        neutral: "border-transparent bg-muted text-foreground",
        flight: "border-transparent bg-flight-tint text-ink [&>svg]:text-flight-ink",
        stay: "border-transparent bg-stay-tint text-ink [&>svg]:text-stay-ink",
        success: "border-transparent bg-success-tint text-ink [&>svg]:text-success-ink",
        estimate: "border-transparent bg-estimate-tint text-ink",
        subtle: "border-transparent bg-soft-pink text-ink",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "span"

  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
