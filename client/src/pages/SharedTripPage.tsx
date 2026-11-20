import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Eye } from "lucide-react";

import { Notice } from "@/components/ui/notice";
import { buttonVariants } from "@/components/ui/button";
import { AnswerMarkdown } from "@/components/chat/answer-markdown";
import { ItineraryView } from "@/components/chat/itinerary";
import { WeatherNote } from "@/components/chat/weather-note";
import { ResultCards } from "@/components/chat/result-cards";
import { getSharedTrip, type SharedTrip } from "@/api/AccountApi";
import { displayLocale } from "@/lib/format";

/** Public, read-only view of a shared itinerary (GET /api/shared/{token}). */
export default function SharedTripPage() {
  const { token = "" } = useParams();
  const [trip, setTrip] = useState<SharedTrip | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    getSharedTrip(token).then((t) => live && setTrip(t)).catch((e) => live && setError(e instanceof Error ? e.message : "This link isn't available."));
    return () => { live = false; };
  }, [token]);

  useEffect(() => {
    if (trip?.title) document.title = `${trip.title} · TravelBuddy`;
  }, [trip?.title]);

  if (error) {
    return (
      <div className="mx-auto w-full max-w-xl px-gutter py-16">
        <Notice tone="info" title="This trip link isn't available" description={error} actions={<Link to="/" className={buttonVariants({ size: "sm" })}>Plan your own trip</Link>} />
      </div>
    );
  }
  if (!trip) {
    return (
      <div className="mx-auto w-full max-w-3xl space-y-4 px-gutter py-10" aria-hidden="true">
        <div className="h-8 w-2/3 rounded bg-muted animate-breathe" />
        <div className="h-48 rounded-xl bg-muted animate-breathe" />
      </div>
    );
  }
  const it = trip.data.itinerary;
  return (
    <article className="mx-auto w-full max-w-3xl px-gutter py-10">
      <p className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-meta text-muted-foreground">
        <Eye className="size-3.5" aria-hidden="true" />Shared trip · read-only · {new Date(trip.shared_at).toLocaleDateString(displayLocale(), { month: "short", day: "numeric", year: "numeric" })}
      </p>
      <h1 className="font-display text-title font-semibold">{it?.trip?.destination?.name ? `Trip to ${it.trip.destination.name}` : trip.title}</h1>
      {it?.trip && <p className="mt-1 text-muted-foreground tabular">{it.trip.start_date} – {it.trip.end_date}</p>}
      {trip.answer && <div className="mt-6"><AnswerMarkdown>{trip.answer}</AnswerMarkdown></div>}
      <ItineraryView data={trip.data} />
      <WeatherNote data={trip.data} answer={trip.answer} />
      <ResultCards data={trip.data} />
      <div className="mt-10 border-t pt-6">
        <Link to="/" className={buttonVariants()}>Plan your own trip with TravelBuddy</Link>
      </div>
    </article>
  );
}
