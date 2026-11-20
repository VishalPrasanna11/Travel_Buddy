import { Plane, BedDouble, MapPin, CloudSun } from "lucide-react";

const sources = [
  { icon: Plane, label: "Flights", detail: "from RouteStack", tone: "bg-flight-tint text-flight-ink" },
  { icon: BedDouble, label: "Hotels", detail: "from RouteStack", tone: "bg-stay-tint text-stay-ink" },
  { icon: MapPin, label: "Places and restaurants", detail: "from Google Places", tone: "bg-raspberry-tint text-raspberry" },
  { icon: CloudSun, label: "Weather", detail: "from OpenWeather", tone: "bg-success-tint text-success-ink" },
] as const;

/** "How it works": one lead step with weight, two short follow-ups, then the sources. */
export function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-heading" className="scroll-mt-20 py-section">
      <div className="mx-auto max-w-6xl px-gutter md:px-gutter-lg">
        <h2 id="how-heading" className="text-title font-semibold md:text-3xl">How it works</h2>

        <ol className="mt-10 grid gap-10 md:grid-cols-[1.4fr_1fr] md:gap-16">
          <li className="space-y-3">
            <p className="text-meta font-semibold text-raspberry">Step 1</p>
            <h3 className="text-2xl font-semibold">Describe the trip the way you'd text a friend</h3>
            <p className="max-w-prose text-muted-foreground">
              Where, when, where you're leaving from, who's coming and what you enjoy. One message is enough. You can
              refine it afterwards.
            </p>
            <p className="max-w-prose rounded-xl bg-muted px-4 py-3 text-sm">
              “A long weekend in Mexico City in October from Chicago. Two adults, mid-range, mostly food and museums.”
            </p>
          </li>

          <li className="space-y-6 md:pt-8">
            <div className="space-y-2">
              <p className="text-meta font-semibold text-raspberry">Step 2</p>
              <h3 className="text-heading font-semibold">Give it a moment</h3>
              <p className="text-muted-foreground">
                TravelBuddy checks several sources at once. A full plan usually takes under a minute.
              </p>
            </div>
            <div className="space-y-2">
              <p className="text-meta font-semibold text-raspberry">Step 3</p>
              <h3 className="text-heading font-semibold">Read, adjust, go</h3>
              <p className="text-muted-foreground">
                Scan the days, compare flights and hotels, then ask for changes in the same conversation.
              </p>
            </div>
          </li>
        </ol>

        <div className="mt-14 border-t pt-8">
          <h3 className="text-heading font-semibold">Where the details come from</h3>
          <ul className="mt-4 flex flex-wrap gap-3">
            {sources.map(({ icon: Icon, label, detail, tone }) => (
              <li key={label} className="flex items-center gap-3 rounded-full border py-1.5 pl-1.5 pr-4">
                <span className={`inline-flex size-8 items-center justify-center rounded-full ${tone}`}>
                  <Icon className="size-4" aria-hidden="true" />
                </span>
                <span className="text-sm">
                  <span className="font-semibold">{label}</span>{" "}
                  <span className="text-muted-foreground">{detail}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-4 max-w-prose text-sm text-muted-foreground">
            Prices, ratings and availability are shown as those sources return them for your dates.
          </p>
        </div>
      </div>
    </section>
  );
}
