import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/**
 * Button. One primary (Raspberry) action per view; everything else is
 * secondary, outline, ghost or link. Sizes grow to 44px on touch screens.
 */
const buttonVariants = cva(
  [
    "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-control font-medium",
    "transition-[background-color,color,border-color,box-shadow,transform] duration-150 ease-out",
    "active:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
    "aria-invalid:border-destructive",
  ].join(" "),
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground hover:bg-raspberry-hover active:bg-raspberry-pressed",
        destructive:
          "bg-destructive text-destructive-foreground hover:brightness-95 active:brightness-90",
        outline:
          "border border-input bg-background text-foreground hover:border-gray-strong hover:bg-muted",
        secondary:
          "bg-secondary text-secondary-foreground hover:brightness-95 active:brightness-90",
        ghost:
          "text-foreground hover:bg-accent",
        link:
          "h-auto px-0 text-primary underline-offset-4 hover:text-raspberry-hover hover:underline",
      },
      size: {
        default: "h-10 px-4 text-sm pointer-coarse:h-11 has-[>svg]:px-3.5",
        sm: "h-9 gap-1.5 px-3 text-sm pointer-coarse:h-11 has-[>svg]:px-2.5",
        lg: "h-12 px-6 text-base has-[>svg]:px-5",
        icon: "size-10 pointer-coarse:size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
