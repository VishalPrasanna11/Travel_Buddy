import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { v4 as uuidv4 } from "uuid";

import { chatDb, CONVERSATIONS_CHANGED, type Conversation } from "@/db/indexedDb";
import { cn } from "@/lib/utils";
import { useSidebar } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle, DialogClose } from "@/components/ui/dialog";

type Summary = Pick<Conversation, "id" | "title" | "updated_at"> & { turns: number };

function useConversations() {
  const [items, setItems] = useState<Summary[] | null>(null);
  const load = useCallback(async () => {
    try {
      const all = await chatDb.getAllConversations();
      setItems(
        all
          .filter((c) => c.messages?.some((m) => m.role === "user"))
          .map((c) => ({ id: c.id, title: c.title, updated_at: c.updated_at, turns: c.messages.length }))
      );
    } catch (err) {
      console.error("Could not list trips", err);
      setItems([]);
    }
  }, []);
  useEffect(() => {
    load();
    window.addEventListener(CONVERSATIONS_CHANGED, load);
    return () => window.removeEventListener(CONVERSATIONS_CHANGED, load);
  }, [load]);
  return items;
}

const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
function when(ts: number) {
  const days = Math.round((ts - Date.now()) / 86_400_000);
  if (days === 0) return "Today";
  if (days > -7) return rtf.format(days, "day");
  return new Date(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Saved trips (IndexedDB, this device only) with rename and delete. */
export function TripHistory() {
  const items = useConversations();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { isMobile, setOpenMobile } = useSidebar();
  const [renaming, setRenaming] = useState<Summary | null>(null);
  const [deleting, setDeleting] = useState<Summary | null>(null);
  const [draft, setDraft] = useState("");
  const lastTrigger = useRef<string | null>(null);

  // Dialogs open from a menu that has already closed, so send focus back to
  // that trip's options button (or the trip list if the trip was deleted).
  const returnFocus = (e: Event, id: string | null) => {
    e.preventDefault();
    const trigger = id ? document.querySelector<HTMLElement>(`[data-trip-trigger="${id}"]`) : null;
    (trigger ?? document.getElementById("trip-history-heading"))?.focus();
  };

  const activeId = pathname.startsWith("/chat/") ? pathname.slice(6) : null;
  const close = () => isMobile && setOpenMobile(false);

  const confirmDelete = async () => {
    if (!deleting) return;
    const wasActive = deleting.id === activeId;
    await chatDb.deleteConversation(deleting.id);
    setDeleting(null);
    if (wasActive) navigate(`/chat/${uuidv4()}`, { replace: true });
  };

  const saveRename = async (e: React.FormEvent) => {
    e.preventDefault();
    const title = draft.trim();
    if (renaming && title) await chatDb.renameConversation(renaming.id, title.slice(0, 80));
    setRenaming(null);
  };

  return (
    <section aria-labelledby="trip-history-heading" className="flex min-h-0 flex-1 flex-col">
      <h2 id="trip-history-heading" tabIndex={-1} className="outline-none px-4 pb-1 pt-4 font-sans text-meta font-semibold text-muted-foreground">
        Your trips
      </h2>

      {items === null ? (
        <div className="space-y-2 px-4 py-2" aria-hidden="true">
          {[0, 1, 2].map((i) => <div key={i} className="h-9 rounded-md bg-muted" />)}
        </div>
      ) : items.length === 0 ? (
        <p className="px-4 py-2 text-sm text-muted-foreground">
          No trips yet. Conversations you start are saved on this device.
        </p>
      ) : (
        <ul className="scroll-thin min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
          {items.map((c) => {
            const active = c.id === activeId;
            return (
              <li key={c.id} className="group/trip relative">
                <Link
                  to={`/chat/${c.id}`}
                  viewTransition
                  onClick={close}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex min-h-10 flex-col justify-center rounded-md py-1.5 pl-2.5 pr-10 text-sm transition-colors duration-150 pointer-coarse:min-h-11",
                    active ? "bg-raspberry-tint text-ink" : "text-ink hover:bg-muted"
                  )}
                >
                  <span className={cn("truncate", active && "font-semibold")} title={c.title}>{c.title}</span>
                  <span className="text-meta text-muted-foreground">{when(c.updated_at)}</span>
                </Link>
                <DropdownMenu>
                  <DropdownMenuTrigger
                    data-trip-trigger={c.id}
                    aria-label={`Options for ${c.title}`}
                    className="absolute right-1 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground opacity-100 hover:bg-background hover:text-foreground data-[state=open]:opacity-100 sm:opacity-0 sm:group-hover/trip:opacity-100 sm:focus-visible:opacity-100 pointer-coarse:size-10"
                  >
                    <MoreHorizontal className="size-4" aria-hidden="true" />
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" side="right" className="w-40">
                    <DropdownMenuItem onSelect={() => { lastTrigger.current = c.id; setDraft(c.title); setRenaming(c); }}>
                      <Pencil aria-hidden="true" />Rename
                    </DropdownMenuItem>
                    <DropdownMenuItem onSelect={() => { lastTrigger.current = c.id; setDeleting(c); }} className="text-destructive focus:text-destructive">
                      <Trash2 aria-hidden="true" />Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </li>
            );
          })}
        </ul>
      )}

      <Dialog open={renaming !== null} onOpenChange={(o) => !o && setRenaming(null)}>
        <DialogContent onCloseAutoFocus={(e) => returnFocus(e, lastTrigger.current)}>
          <form onSubmit={saveRename}>
            <DialogTitle>Rename trip</DialogTitle>
            <DialogDescription>Give it a name you'll recognise later.</DialogDescription>
            <label htmlFor="rename-trip" className="sr-only">Trip name</label>
            <Input id="rename-trip" className="mt-4" value={draft} maxLength={80} onChange={(e) => setDraft(e.target.value)} autoFocus />
            <DialogFooter>
              <DialogClose asChild><Button type="button" variant="outline">Cancel</Button></DialogClose>
              <Button type="submit" disabled={!draft.trim()}>Save name</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={deleting !== null} onOpenChange={(o) => !o && setDeleting(null)}>
        <DialogContent role="alertdialog" onCloseAutoFocus={(e) => returnFocus(e, lastTrigger.current)}>
          <DialogTitle>Delete this trip?</DialogTitle>
          <DialogDescription>
            "{deleting?.title}" and its answers will be removed from this device. This can't be undone.
          </DialogDescription>
          <DialogFooter>
            <DialogClose asChild><Button variant="outline">Keep it</Button></DialogClose>
            <Button variant="destructive" onClick={confirmDelete}>Delete trip</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
