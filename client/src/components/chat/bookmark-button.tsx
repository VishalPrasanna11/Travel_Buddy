import { Bookmark, BookmarkCheck } from "lucide-react"
import { toast } from "sonner"

import { cn } from "@/lib/utils"
import { useSavedPlaces, useToggleSaved, type SavedKind } from "@/api/AccountApi"
import type { Hotel, Place } from "./types"

/** Save / unsave a place, restaurant or hotel (POST/DELETE /api/saved-places). Hidden when signed out. */
export function BookmarkButton({ entity, kind, className }: { entity: Place | Hotel; kind: SavedKind; className?: string }) {
  const { data: saved, isSuccess } = useSavedPlaces()
  const toggle = useToggleSaved()
  if (!isSuccess || !entity.id) return null
  const isSaved = !!saved?.some((s) => s.entity_id === entity.id)
  const onClick = () =>
    toggle.mutate(
      { entity, kind, saved: isSaved },
      {
        onSuccess: () => toast.success(isSaved ? `Removed ${entity.name} from Saved` : `Saved ${entity.name}`),
        onError: () => toast.error("Couldn't update Saved. Try again."),
      }
    )
  const Icon = isSaved ? BookmarkCheck : Bookmark
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={toggle.isPending}
      aria-pressed={isSaved}
      aria-label={isSaved ? `Remove ${entity.name} from Saved` : `Save ${entity.name}`}
      className={cn(
        "inline-flex size-9 items-center justify-center rounded-full bg-background/90 text-ink shadow-sm transition-colors hover:bg-background hover:text-raspberry disabled:opacity-60 pointer-coarse:size-11",
        isSaved && "text-raspberry",
        className
      )}
    >
      <Icon className={cn("size-4", isSaved && "fill-raspberry/15")} aria-hidden="true" />
    </button>
  )
}
