import { useEffect, useId, useState } from "react";
import { Loader2, Settings } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { usePreferences, useSavePreferences, type Preferences } from "@/api/AccountApi";

const CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "INR", "CHF", "MXN", "BRL"];
const LOCALES = [
  { value: "", label: "Match my browser" },
  { value: "en-US", label: "English (US)" },
  { value: "en-GB", label: "English (UK)" },
  { value: "es-ES", label: "Español" },
  { value: "fr-FR", label: "Français" },
  { value: "de-DE", label: "Deutsch" },
  { value: "pt-PT", label: "Português" },
  { value: "it-IT", label: "Italiano" },
  { value: "ja-JP", label: "日本語" },
  { value: "hi-IN", label: "हिन्दी" },
];

const selectClass =
  "h-10 w-full rounded-md border border-input bg-background px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring pointer-coarse:h-11";

/** Locale, currency, units, home airport and traveler defaults (GET/PATCH /api/users/preferences). */
export default function SettingsPage() {
  const id = useId();
  const { data, isLoading, isError } = usePreferences();
  const save = useSavePreferences();
  const [form, setForm] = useState<Preferences | null>(null);

  useEffect(() => {
    if (data && !form) setForm(data);
  }, [data, form]);

  const set = <K extends keyof Preferences>(key: K, value: Preferences[K]) => setForm((f) => (f ? { ...f, [key]: value } : f));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;
    save.mutate(
      {
        locale: form.locale || null,
        currency: form.currency,
        units: form.units,
        home_airport: form.home_airport?.trim() || null,
        default_adults: form.default_adults,
        default_children: form.default_children,
      },
      {
        onSuccess: () => toast.success("Preferences saved", { description: "New searches will use them." }),
        onError: (err) => toast.error(err instanceof Error ? err.message : "Couldn't save preferences."),
      }
    );
  };

  return (
    <div className="mx-auto w-full max-w-xl px-gutter py-10 md:py-14">
      <h1 className="flex items-center gap-2 font-display text-title font-semibold">
        <Settings className="size-5 text-raspberry" aria-hidden="true" />
        Settings
      </h1>
      <p className="mt-1 text-muted-foreground">How TravelBuddy searches and shows prices, temperatures and dates.</p>

      {isError && <Notice tone="error" className="mt-6" title="Couldn't load your preferences" description="Check your connection and reload the page." />}
      {isLoading || !form ? (
        !isError && (
          <div className="mt-8 space-y-4" aria-hidden="true">
            {[0, 1, 2, 3].map((i) => <div key={i} className="h-16 rounded-lg bg-muted animate-breathe" />)}
          </div>
        )
      ) : (
        <form onSubmit={submit} className="mt-8 space-y-6">
          <fieldset className="grid gap-4 sm:grid-cols-2">
            <legend className="mb-2 text-heading font-semibold">Display</legend>
            <div>
              <label htmlFor={`${id}-locale`} className="mb-1.5 block text-sm font-semibold">Language & region</label>
              <select id={`${id}-locale`} className={selectClass} value={form.locale ?? ""} onChange={(e) => set("locale", e.target.value || null)}>
                {LOCALES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
              </select>
              <p className="mt-1 text-meta text-muted-foreground">Formats dates and numbers.</p>
            </div>
            <div>
              <label htmlFor={`${id}-currency`} className="mb-1.5 block text-sm font-semibold">Currency</label>
              <select id={`${id}-currency`} className={selectClass} value={form.currency} onChange={(e) => set("currency", e.target.value)}>
                {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <p className="mt-1 text-meta text-muted-foreground">Hotel prices are requested in this currency.</p>
            </div>
            <div className="sm:col-span-2">
              <span className="mb-1.5 block text-sm font-semibold" id={`${id}-units`}>Temperature</span>
              <div role="radiogroup" aria-labelledby={`${id}-units`} className="inline-flex rounded-lg border p-0.5">
                {(["metric", "imperial"] as const).map((u) => (
                  <button
                    key={u}
                    type="button"
                    role="radio"
                    aria-checked={form.units === u}
                    onClick={() => set("units", u)}
                    className={`min-h-9 rounded-md px-4 text-sm font-medium transition-colors pointer-coarse:min-h-11 ${form.units === u ? "bg-raspberry text-white" : "text-ink hover:bg-muted"}`}
                  >
                    {u === "metric" ? "°C (metric)" : "°F (imperial)"}
                  </button>
                ))}
              </div>
            </div>
          </fieldset>

          <fieldset className="grid gap-4 sm:grid-cols-3">
            <legend className="mb-2 text-heading font-semibold">Trips</legend>
            <div className="sm:col-span-3">
              <label htmlFor={`${id}-home`} className="mb-1.5 block text-sm font-semibold">Home airport</label>
              <Input id={`${id}-home`} placeholder="e.g. BOS or Boston" maxLength={80} value={form.home_airport ?? ""} onChange={(e) => set("home_airport", e.target.value)} />
              <p className="mt-1 text-meta text-muted-foreground">Used for flights when you don't say where you're leaving from.</p>
            </div>
            <div>
              <label htmlFor={`${id}-adults`} className="mb-1.5 block text-sm font-semibold">Adults</label>
              <Input id={`${id}-adults`} type="number" min={1} max={9} value={form.default_adults} onChange={(e) => set("default_adults", Math.max(1, Math.min(9, Number(e.target.value) || 1)))} />
            </div>
            <div>
              <label htmlFor={`${id}-children`} className="mb-1.5 block text-sm font-semibold">Children</label>
              <Input id={`${id}-children`} type="number" min={0} max={9} value={form.default_children} onChange={(e) => set("default_children", Math.max(0, Math.min(9, Number(e.target.value) || 0)))} />
            </div>
          </fieldset>

          <Button type="submit" disabled={save.isPending}>
            {save.isPending && <Loader2 className="motion-safe:animate-spin" aria-hidden="true" />}
            Save preferences
          </Button>
        </form>
      )}
    </div>
  );
}
