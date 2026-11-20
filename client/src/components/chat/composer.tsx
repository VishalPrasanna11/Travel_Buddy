import { forwardRef, useImperativeHandle, useRef, type ChangeEvent, type FormEvent, type KeyboardEvent } from "react"
import { ArrowUp, Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"
import { useAutosizeTextArea } from "@/hooks/use-autosize-textarea"

type ComposerProps = {
  value: string
  onChange: (e: ChangeEvent<HTMLTextAreaElement>) => void
  onSend: () => void
  pending: boolean
  disabled?: boolean
  placeholder?: string
}

export type ComposerHandle = { focus: () => void }

/**
 * Message composer. Enter sends, Shift+Enter adds a line, IME composition is
 * respected, and nothing can be sent while an answer is pending. There is no
 * fake Stop button: the API can't cancel a request once it has started.
 */
export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  { value, onChange, onSend, pending, disabled, placeholder = "Where to, when, and who's going?" },
  ref
) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  useImperativeHandle(ref, () => ({ focus: () => textareaRef.current?.focus() }))
  useAutosizeTextArea({ ref: textareaRef as React.RefObject<HTMLTextAreaElement>, maxHeight: 200, borderWidth: 0, dependencies: [value] })

  const canSend = value.trim().length > 0 && !pending && !disabled

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    if (canSend) onSend()
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Enter" || e.shiftKey || e.nativeEvent.isComposing || e.keyCode === 229) return
    e.preventDefault()
    submit()
  }

  return (
    <form onSubmit={submit} className="mx-auto w-full max-w-3xl" aria-busy={pending || undefined}>
      <label htmlFor="chat-composer" className="sr-only">Message TravelBuddy</label>
      <div
        className={cn(
          "flex items-end gap-2 rounded-2xl border border-input bg-background p-2 transition-[border-color,box-shadow] duration-150",
          "focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/20"
        )}
      >
        <textarea
          id="chat-composer"
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={onChange}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          aria-describedby="chat-composer-hint"
          enterKeyHint="send"
          className="max-h-[200px] min-h-11 flex-1 resize-none bg-transparent px-2 py-2.5 text-base text-ink placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!canSend}
          aria-label={pending ? "Waiting for the answer" : "Send"}
          className={cn(
            "inline-flex size-11 shrink-0 items-center justify-center rounded-xl transition-colors duration-150",
            canSend
              ? "bg-primary text-primary-foreground hover:bg-raspberry-hover active:bg-raspberry-pressed"
              : "bg-muted text-muted-foreground",
            "disabled:cursor-not-allowed"
          )}
        >
          {pending ? <Loader2 className="size-5 animate-spin motion-reduce:animate-none" aria-hidden="true" /> : <ArrowUp className="size-5" aria-hidden="true" />}
        </button>
      </div>
      <p id="chat-composer-hint" className="mt-1.5 px-2 text-meta text-muted-foreground">
        {pending ? (
          "Working on your answer. You can write your next message meanwhile."
        ) : (
          <>
            <span className="pointer-coarse:hidden">Enter to send · Shift+Enter for a new line · </span>
            Trips are saved on this device.
          </>
        )}
      </p>
    </form>
  )
})
