import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { AlertTriangle, CheckCircle2, Info, CloudSun } from "lucide-react"

import { cn } from "@/lib/utils"

/**
 * Notice: an inline status block for errors, partial results, estimates and
 * confirmations. Always says what happened and, through `actions`, what to do
 * next (Retry, Edit query, Start a new trip).
 */
const noticeVariants = cva(
  "flex gap-3 rounded-xl border p-4 text-sm text-ink [&_svg.notice-icon]:mt-0.5 [&_svg.notice-icon]:size-5 [&_svg.notice-icon]:shrink-0",
  {
    variants: {
      tone: {
        info: "border-border bg-muted [&_svg.notice-icon]:text-muted-foreground",
        error: "border-red/30 bg-danger-tint [&_svg.notice-icon]:text-destructive",
        success: "border-leaf-green/40 bg-success-tint [&_svg.notice-icon]:text-success-ink",
        estimate: "border-sunshine-yellow/60 bg-estimate-tint [&_svg.notice-icon]:text-amber-ink",
      },
    },
    defaultVariants: { tone: "info" },
  }
)

const toneIcon = {
  info: Info,
  error: AlertTriangle,
  success: CheckCircle2,
  estimate: CloudSun,
} as const

type NoticeProps = Omit<React.ComponentProps<"div">, "title"> &
  VariantProps<typeof noticeVariants> & {
    title: React.ReactNode
    description?: React.ReactNode
    actions?: React.ReactNode
    icon?: React.ComponentType<{ className?: string }>
  }

function Notice({ tone = "info", title, description, actions, icon, className, ...props }: NoticeProps) {
  const Icon = icon ?? toneIcon[tone ?? "info"]
  return (
    <div
      data-slot="notice"
      role={tone === "error" ? "alert" : "status"}
      className={cn(noticeVariants({ tone }), className)}
      {...props}
    >
      <Icon className="notice-icon" aria-hidden="true" />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="font-semibold">{title}</p>
        {description && <div className="text-ink">{description}</div>}
        {actions && <div className="flex flex-wrap gap-2 pt-2">{actions}</div>}
      </div>
    </div>
  )
}

export { Notice, noticeVariants }
