import { Plane, BedDouble, MapPin, Utensils, CloudSun } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import kyotoImg from "@/assets/kyoto.jpeg";

/**
 * A static excerpt of what a TravelBuddy answer looks like.
 * It is labelled "Example" and deliberately shows no prices, ratings,
 * times or availability: those only ever come from live searches.
 */
export function ExamplePreview() {
  return (
    <figure
      aria-labelledby="example-caption"
      className="w-full overflow-hidden rounded-surface border bg-background shadow-raised"
    >
      <div className="flex items-center justify-between gap-3 border-b px-5 py-3">
        <figcaption id="example-caption" className="text-sm font-semibold">
          What an answer looks like
        </figcaption>
        <Badge variant="neutral">Example</Badge>
      </div>

      <div className="space-y-5 p-5">
        {/* The request */}
        <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-tr-md bg-soft-pink px-4 py-2.5 text-sm text-ink">
          5 days in Kyoto this April, flying from San Francisco. Two of us, mid-range, we love temples and food markets.
        </p>

        {/* Getting there + staying */}
        <dl className="divide-y border-y">
          <div className="flex items-start gap-3 py-3">
            <Badge variant="flight" className="mt-0.5"><Plane aria-hidden="true" />Flights</Badge>
            <div className="min-w-0 text-sm">
              <dt className="font-semibold">SFO → KIX</dt>
              <dd className="text-muted-foreground">Airline, times and fare for your dates, from a live search</dd>
            </div>
          </div>
          <div className="flex items-start gap-3 py-3">
            <Badge variant="stay" className="mt-0.5"><BedDouble aria-hidden="true" />Stay</Badge>
            <div className="min-w-0 text-sm">
              <dt className="font-semibold">Hotels near Gion and Downtown Kyoto</dt>
              <dd className="text-muted-foreground">Price, rating and address as the hotel search returns them</dd>
            </div>
          </div>
        </dl>

        {/* Day by day */}
        <div className="space-y-3">
          <p className="text-heading font-semibold">Day 1 · Eastern Kyoto</p>
          <img
            src={kyotoImg}
            alt="A five-story pagoda above the rooftops of eastern Kyoto"
            loading="lazy"
            decoding="async"
            width={640}
            height={240}
            className="aspect-[8/3] w-full rounded-lg bg-muted object-cover"
          />
          <ul className="space-y-2 text-sm">
            <li className="flex items-start gap-2">
              <MapPin className="mt-0.5 size-4 shrink-0 text-raspberry" aria-hidden="true" />
              <span><span className="font-semibold">Kiyomizu-dera</span> early, before the tour groups</span>
            </li>
            <li className="flex items-start gap-2">
              <MapPin className="mt-0.5 size-4 shrink-0 text-raspberry" aria-hidden="true" />
              <span><span className="font-semibold">Sannenzaka and Ninenzaka</span> on foot down to Gion</span>
            </li>
            <li className="flex items-start gap-2">
              <Utensils className="mt-0.5 size-4 shrink-0 text-raspberry" aria-hidden="true" />
              <span>Dinner picks nearby, with ratings from Google Places</span>
            </li>
          </ul>
        </div>

        <div className="flex items-start gap-3 border-t pt-4 text-sm">
          <CloudSun className="mt-0.5 size-4 shrink-0 text-teal-ink" aria-hidden="true" />
          <p>The weather outlook for Kyoto comes with the plan, so you can pack and plan around it.</p>
        </div>

        <p className="text-meta text-muted-foreground">Days 2–5 continue the same way.</p>
      </div>
    </figure>
  );
}
