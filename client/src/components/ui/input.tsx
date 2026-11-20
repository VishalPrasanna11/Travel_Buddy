import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        // 16px text on phones prevents iOS zoom-on-focus.
        "file:text-foreground placeholder:text-muted-foreground border-input flex h-10 pointer-coarse:h-11 w-full min-w-0 rounded-control border bg-background px-3 py-1 text-base transition-[border-color,box-shadow] duration-150 outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        "hover:border-gray-strong focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/25",
        "aria-invalid:border-destructive aria-invalid:focus-visible:ring-destructive/25",
        className
      )}
      {...props}
    />
  )
}

export { Input }
