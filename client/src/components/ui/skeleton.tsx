import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("bg-muted animate-breathe rounded-md [animation-duration:2.4s]", className)}
      {...props}
    />
  )
}

export { Skeleton }
