import { AssistantMark } from "@/components/ui/message-row";

/**
 * Calm full-page wait used for Auth0 redirects and lazy route loads.
 * Shows the TravelBuddy mark and a plain sentence, never a bare spinner.
 */
export function FullPageLoader({ label = "Loading TravelBuddy…" }: { label?: string }) {
  return (
    <div className="flex min-h-dvh flex-1 flex-col items-center justify-center gap-4 px-gutter text-center" role="status" aria-live="polite">
      <span className="animate-breathe">
        <AssistantMark />
      </span>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

/** Smaller variant for in-layout lazy routes (keeps header/sidebar visible). */
export function RouteLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-1 items-center justify-center py-24" role="status" aria-live="polite">
      <span className="flex items-center gap-3 text-sm text-muted-foreground">
        <span className="animate-breathe"><AssistantMark /></span>
        {label}
      </span>
    </div>
  );
}
