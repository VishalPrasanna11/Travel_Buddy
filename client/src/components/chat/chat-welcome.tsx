import { ArrowRight, Compass } from "lucide-react"

/**
 * First-visit empty state. Example trips are full, realistic requests the
 * user can send as-is; they contain no prices, ratings or availability.
 */
export const EXAMPLE_TRIPS = [
  {
    title: "Lisbon in spring",
    prompt: "Plan 4 days in Lisbon from Boston, March 12–16, for 2 adults. Mid-range hotels, good seafood, and a day trip to Sintra.",
  },
  {
    title: "Kyoto for the cherry blossoms",
    prompt: "5 days in Kyoto in early April for 2 people: temples, quiet gardens, a ryokan night, and where to see the cherry blossoms.",
  },
  {
    title: "Barcelona with kids",
    prompt: "A family week in Barcelona in July with two kids (8 and 11): beaches, Sagrada Família, easy restaurants, flying from London.",
  },
  {
    title: "Chicago long weekend",
    prompt: "Long weekend in Chicago from New York: architecture boat tour, deep-dish pizza, and a hotel near the Loop.",
  },
]

export function ChatWelcome({ onPick, disabled }: { onPick: (prompt: string) => void; disabled?: boolean }) {
  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-10 sm:py-14">
      <span className="inline-flex size-11 items-center justify-center rounded-full bg-raspberry-tint text-raspberry" aria-hidden="true">
        <Compass className="size-5" />
      </span>
      <h2 className="mt-4 text-title font-semibold">Where are you headed?</h2>
      <p className="mt-2 max-w-prose text-muted-foreground">
        Describe the whole trip in one message. TravelBuddy checks flights, hotels, places to see, restaurants and weather,
        then gives you one plan. Include where you're leaving from, your dates and who's going.
      </p>

      <h3 className="mt-8 text-sm font-semibold text-muted-foreground">Try one of these</h3>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {EXAMPLE_TRIPS.map((t) => (
          <li key={t.title}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onPick(t.prompt)}
              className="group flex h-full w-full flex-col items-start gap-1 rounded-xl border bg-card p-4 text-left transition-colors duration-150 hover:border-raspberry/40 hover:bg-raspberry-tint disabled:opacity-50"
            >
              <span className="flex w-full items-center justify-between gap-2 font-semibold text-ink">
                {t.title}
                <ArrowRight className="size-4 shrink-0 text-raspberry transition-transform duration-150 group-hover:translate-x-0.5" aria-hidden="true" />
              </span>
              <span className="text-sm text-muted-foreground">{t.prompt}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
