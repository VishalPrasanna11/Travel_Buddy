import { useId, useState } from "react"
import { ArrowRight, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react"
import { toast } from "sonner"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Notice } from "@/components/ui/notice"
import type { Clarification, ClarificationField, ChatMessage } from "./types"

/**
 * Everything that turns an answer into the next question: clarifying
 * questions (quick-reply chips + a mini form), follow-up suggestion chips,
 * out-of-scope redirects and thumbs feedback.
 */

const chip =
  "inline-flex min-h-9 items-center gap-1.5 rounded-full border px-3 text-sm font-medium text-ink transition-colors duration-150 hover:border-raspberry hover:bg-accent disabled:pointer-events-none disabled:opacity-50 pointer-coarse:min-h-11"

function fmtDate(d: string) {
  const t = new Date(`${d}T12:00:00`)
  return Number.isNaN(t.getTime()) ? d : t.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

type Answers = { destination?: string; origin?: string; start_date?: string; end_date?: string; skip?: string[] }

function summarize(a: Answers) {
  const parts: string[] = []
  if (a.destination) parts.push(a.destination)
  if (a.start_date) parts.push(a.end_date && a.end_date !== a.start_date ? `${fmtDate(a.start_date)}–${fmtDate(a.end_date)}` : fmtDate(a.start_date))
  if (a.origin) parts.push(`from ${a.origin}`)
  if (a.skip?.includes("origin")) parts.push("no flights")
  return parts.join(", ") || "Go ahead"
}

function FieldInput({ field, value, onChange, disabled }: { field: ClarificationField; value: Answers; onChange: (v: Answers) => void; disabled: boolean }) {
  const id = useId()
  if (field.type === "date_range") {
    const picked = (o: NonNullable<ClarificationField["options"]>[number]) => value.start_date === o.start_date && value.end_date === o.end_date
    return (
      <fieldset disabled={disabled}>
        <legend className="mb-1.5 text-sm font-semibold text-ink">{field.label}</legend>
        <div className="flex flex-wrap gap-2">
          {field.options?.map((o) => (
            <button key={o.label} type="button" aria-pressed={picked(o)} onClick={() => onChange({ ...value, start_date: o.start_date, end_date: o.end_date })}
              className={cn(chip, picked(o) && "border-raspberry bg-raspberry-tint")}>
              {o.label}
            </button>
          ))}
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <label htmlFor={`${id}-s`} className="text-muted-foreground">Or pick dates</label>
          <Input id={`${id}-s`} type="date" className="h-9 w-auto" value={value.start_date ?? ""} onChange={(e) => onChange({ ...value, start_date: e.target.value })} aria-label="Start date" />
          <span aria-hidden="true">–</span>
          <Input type="date" className="h-9 w-auto" min={value.start_date} value={value.end_date ?? ""} onChange={(e) => onChange({ ...value, end_date: e.target.value })} aria-label="End date" />
        </div>
      </fieldset>
    )
  }
  if (field.type === "choice") {
    return (
      <fieldset disabled={disabled}>
        <legend className="mb-1.5 text-sm font-semibold text-ink">{field.label}</legend>
        <div className="flex flex-wrap gap-2">
          {field.options?.map((o) => {
            const v = o.value ?? o.label
            const on = value[field.name as "destination"] === v
            return (
              <button key={v} type="button" aria-pressed={on} onClick={() => onChange({ ...value, [field.name]: v })} className={cn(chip, on && "border-raspberry bg-raspberry-tint")}>
                {o.label}
              </button>
            )
          })}
        </div>
      </fieldset>
    )
  }
  const key = field.name as "origin" | "destination"
  const skipped = value.skip?.includes(field.name)
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-ink">{field.label}</label>
      <div className="flex flex-wrap items-center gap-2">
        <Input id={id} className="h-9 max-w-64" placeholder={field.placeholder} value={value[key] ?? ""} disabled={disabled || skipped}
          onChange={(e) => onChange({ ...value, [key]: e.target.value, skip: (value.skip ?? []).filter((s) => s !== field.name) })} />
        {field.options?.map((o) => (
          <button key={o.label} type="button" disabled={disabled} onClick={() => onChange({ ...value, [key]: o.value ?? o.label })} className={chip}>{o.label}</button>
        ))}
        {field.optional && field.skip_label && (
          <button type="button" disabled={disabled} aria-pressed={!!skipped}
            onClick={() => onChange({ ...value, [key]: undefined, skip: skipped ? (value.skip ?? []).filter((s) => s !== field.name) : [...(value.skip ?? []), field.name] })}
            className={cn(chip, skipped && "border-raspberry bg-raspberry-tint")}>
            {field.skip_label}
          </button>
        )}
      </div>
    </div>
  )
}

export function ClarificationCard({ c, onAnswer, busy }: { c: Clarification; onAnswer: (answers: Answers, summary: string) => void; busy: boolean }) {
  const [value, setValue] = useState<Answers>({})
  const ready = c.fields.every((f) => {
    if (f.optional) return true
    if (f.type === "date_range") return !!value.start_date
    return !!value[f.name as "origin" | "destination"]?.trim() || value.skip?.includes(f.name)
  })
  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!ready || busy || c.answered) return
    const clean: Answers = { ...value, origin: value.origin?.trim() || undefined, destination: value.destination?.trim() || undefined }
    onAnswer(clean, summarize(clean))
  }
  return (
    <form onSubmit={submit} className="mt-3 max-w-prose space-y-4 rounded-xl border border-raspberry/30 bg-card p-4" aria-label="Answer to continue">
      {c.fields.map((f) => <FieldInput key={f.name} field={f} value={value} onChange={setValue} disabled={busy || !!c.answered} />)}
      {!c.answered && (
        <Button type="submit" size="sm" disabled={!ready || busy}>
          Continue<ArrowRight aria-hidden="true" />
        </Button>
      )}
      {c.answered && <p className="text-meta text-muted-foreground">Answered.</p>}
    </form>
  )
}

export function SuggestionChips({ suggestions, onPick, disabled }: { suggestions?: string[]; onPick: (s: string) => void; disabled: boolean }) {
  if (!suggestions?.length) return null
  return (
    <div className="mt-6">
      <p className="mb-2 flex items-center gap-1.5 text-meta font-semibold text-muted-foreground"><Sparkles className="size-3.5 text-amber-ink" aria-hidden="true" />Next steps</p>
      <ul className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <li key={s}>
            <button type="button" className={chip} disabled={disabled} onClick={() => onPick(s)}>{s}</button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function OutOfScope({ reason, suggestions, onPick, disabled }: { reason?: string; suggestions?: string[]; onPick: (s: string) => void; disabled: boolean }) {
  return (
    <Notice
      tone="info"
      className="max-w-prose"
      title="That's outside what I plan"
      description={
        <>
          <p>{reason}</p>
          {!!suggestions?.length && (
            <ul className="mt-3 flex flex-wrap gap-2" aria-label="Try one of these instead">
              {suggestions.map((s) => (
                <li key={s}><button type="button" className={cn(chip, "bg-background")} disabled={disabled} onClick={() => onPick(s)}>{s}</button></li>
              ))}
            </ul>
          )}
        </>
      }
    />
  )
}

const REASONS = ["Wrong or made-up details", "Missing what I asked for", "Too long", "Out of date"]

export function FeedbackButtons({ message, onFeedback }: { message: ChatMessage; onFeedback: (rating: "up" | "down", reason?: string) => Promise<boolean> }) {
  const [asking, setAsking] = useState(false)
  const [other, setOther] = useState("")
  if (!message.serverId) return null
  const send = async (rating: "up" | "down", reason?: string) => {
    setAsking(false)
    const ok = await onFeedback(rating, reason)
    if (ok) toast.success(rating === "up" ? "Thanks for the feedback" : "Thanks — that helps us improve")
    else toast.error("Couldn't send feedback")
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <button type="button" aria-pressed={message.feedback === "up"} aria-label="Good answer" onClick={() => send("up")}
        className={cn("inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-ink pointer-coarse:size-11", message.feedback === "up" && "text-success-ink")}>
        <ThumbsUp className={cn("size-4", message.feedback === "up" && "fill-current")} aria-hidden="true" />
      </button>
      <button type="button" aria-pressed={message.feedback === "down"} aria-label="Bad answer" aria-expanded={asking} onClick={() => setAsking((v) => !v)}
        className={cn("inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-ink pointer-coarse:size-11", message.feedback === "down" && "text-destructive")}>
        <ThumbsDown className={cn("size-4", message.feedback === "down" && "fill-current")} aria-hidden="true" />
      </button>
      {asking && (
        <span className="flex w-full flex-wrap items-center gap-1.5 pt-1" role="group" aria-label="What went wrong?">
          {REASONS.map((r) => <button key={r} type="button" className={cn(chip, "min-h-8 text-meta")} onClick={() => send("down", r)}>{r}</button>)}
          <form className="flex items-center gap-1.5" onSubmit={(e) => { e.preventDefault(); void send("down", other.trim() || undefined) }}>
            <Input className="h-8 w-48 text-sm" placeholder="Something else…" value={other} maxLength={500} onChange={(e) => setOther(e.target.value)} aria-label="Other reason" />
            <Button size="sm" variant="outline" type="submit">Send</Button>
          </form>
        </span>
      )}
    </span>
  )
}
