import { useEffect, useId, useRef, useState } from "react";
import axios from "axios";
import { addDays, format, isBefore, isEqual } from "date-fns";
import { ArrowRightLeft, ExternalLink, Plane, PlaneLanding, PlaneTakeoff, Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Notice } from "@/components/ui/notice";
import { EmptyState } from "@/components/ui/empty-state";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { InlineDatePicker } from "@/components/ui/inline-date-picker";
import { cn } from "@/lib/utils";

const API_BASE_URL = import.meta.env.VITE_BASE_URL;

/**
 * Shape returned by GET /api/flights/search (server/routes/flightRoute.py,
 * `FlightResult`). Rendered exactly as returned: nothing here is estimated or
 * filled in on the client.
 */
interface FlightSegment {
  airline?: string;
  flight_number?: string;
  origin?: string;
  destination?: string;
  departure_time?: string;
  arrival_time?: string;
  duration?: string;
  cabin_class?: string;
  departure_airport?: string;
  arrival_airport?: string;
}

interface FlightResult {
  price?: string;
  segments?: FlightSegment[];
  stops?: number;
  fareSourceCode?: string;
}

type TripType = "one-way" | "round-trip";

type SearchState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "done"; outbound: FlightResult[]; inbound: FlightResult[] | null };

type FieldErrors = Partial<Record<"origin" | "destination" | "departureDate" | "returnDate", string>>;

type SearchSnapshot = {
  tripType: TripType;
  origin: string;
  destination: string;
  departureDate: Date;
  returnDate?: Date;
};

function errorMessageFrom(err: unknown): string {
  if (axios.isAxiosError(err)) {
    if (!err.response) return "We couldn't reach the flight search service. Check your connection and try again.";
    const detail = (err.response.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (err.response.status >= 500) return "The flight search service had a problem. Try again in a moment.";
    return `The search request was rejected (error ${err.response.status}).`;
  }
  return "Something went wrong while searching. Try again.";
}

function parseDate(value?: string): Date | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function TimeLabel({ value }: { value?: string }) {
  const d = parseDate(value);
  if (!d) return <span className="text-muted-foreground">{value || "Time not provided"}</span>;
  return (
    <time dateTime={d.toISOString()} className="tabular">
      <span className="block text-lg font-semibold leading-tight text-foreground">{format(d, "h:mm a")}</span>
      <span className="block text-meta text-muted-foreground">{format(d, "EEE, MMM d")}</span>
    </time>
  );
}

function FlightRow({ flight }: { flight: FlightResult }) {
  const segments = flight.segments ?? [];
  const first = segments[0];
  const last = segments[segments.length - 1];
  const airlines = Array.from(new Set(segments.map((s) => s.airline).filter(Boolean))) as string[];
  const flightNumbers = segments.map((s) => s.flight_number).filter(Boolean).join(" · ");
  const durations = segments.map((s) => s.duration).filter(Boolean);
  const stops = typeof flight.stops === "number" ? flight.stops : Math.max(0, segments.length - 1);
  const cabin = first?.cabin_class;
  const airlineName = airlines.join(" + ");
  const airlineSite = airlines.length === 1
    ? `https://www.${airlines[0].toLowerCase().replace(/[^a-z0-9]/g, "")}.com`
    : null;

  return (
    <li className="rounded-surface border bg-card p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="flex min-w-0 items-center gap-3">
          <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-full bg-flight-tint" aria-hidden="true">
            <Plane className="size-4 text-flight-ink" />
          </span>
          <div className="min-w-0">
            <p className="truncate font-semibold text-foreground">{airlineName || "Airline not provided"}</p>
            {flightNumbers && <p className="text-meta text-muted-foreground tabular">{flightNumbers}</p>}
          </div>
        </div>
        <div className="text-right">
          {flight.price ? (
            <p className="text-xl font-semibold text-foreground tabular">{flight.price}</p>
          ) : (
            <p className="text-sm text-muted-foreground">Price not provided</p>
          )}
          {cabin && <p className="text-meta text-muted-foreground">{cabin}</p>}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <div>
          <p className="text-meta font-semibold text-muted-foreground tabular">{first?.origin || first?.departure_airport || "?"}</p>
          <TimeLabel value={first?.departure_time} />
        </div>
        <div className="flex flex-col items-center text-center">
          <span className="text-meta text-muted-foreground tabular">{durations.length === 1 ? durations[0] : durations.join(" + ")}</span>
          <span className="my-1 h-px w-12 bg-teal-blue sm:w-20" aria-hidden="true" />
          <Badge variant={stops === 0 ? "flight" : "neutral"}>
            {stops === 0 ? "Nonstop" : `${stops} stop${stops > 1 ? "s" : ""}`}
          </Badge>
        </div>
        <div className="text-right">
          <p className="text-meta font-semibold text-muted-foreground tabular">{last?.destination || last?.arrival_airport || "?"}</p>
          <TimeLabel value={last?.arrival_time} />
        </div>
      </div>

      {airlineSite && (
        <div className="mt-4 flex justify-end border-t pt-3">
          <a
            href={airlineSite}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            Book on airline site
            <ExternalLink aria-hidden="true" />
            <span className="sr-only">(opens in a new tab)</span>
          </a>
        </div>
      )}
    </li>
  );
}

function ResultsSkeleton() {
  return (
    <ul className="space-y-3" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <li key={i} className="rounded-surface border p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="size-9 rounded-full bg-muted animate-breathe" />
              <span className="h-4 w-32 rounded bg-muted animate-breathe" />
            </div>
            <span className="h-5 w-16 rounded bg-muted animate-breathe" />
          </div>
          <div className="mt-5 grid grid-cols-3 gap-4">
            <span className="h-8 rounded bg-muted animate-breathe" />
            <span className="h-8 rounded bg-muted animate-breathe" />
            <span className="h-8 rounded bg-muted animate-breathe" />
          </div>
        </li>
      ))}
    </ul>
  );
}

function ResultsSection({
  title,
  direction,
  flights,
  route,
  date,
  onEdit,
}: {
  title: string;
  direction: "outbound" | "return";
  flights: FlightResult[];
  route: string;
  date: Date;
  onEdit: () => void;
}) {
  const Icon = direction === "outbound" ? PlaneTakeoff : PlaneLanding;
  return (
    <section aria-labelledby={`${direction}-heading`} className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id={`${direction}-heading`} className="flex items-center gap-2 text-title font-semibold">
          <Icon className="size-5 text-flight-ink" aria-hidden="true" />
          {title}
        </h2>
        <p className="text-sm text-muted-foreground">
          {route} · <time dateTime={format(date, "yyyy-MM-dd")}>{format(date, "EEE, MMM d")}</time>
          {flights.length > 0 && ` · ${flights.length} ${flights.length === 1 ? "option" : "options"}`}
        </p>
      </div>

      {flights.length === 0 ? (
        <Notice
          tone="info"
          title={`No flights found for ${route} on ${format(date, "MMM d")}`}
          description="Try a nearby date, a different airport code for the same city, or a one-way search."
          actions={<Button variant="outline" size="sm" onClick={onEdit}>Edit search</Button>}
        />
      ) : (
        <ul className="space-y-3">
          {flights.map((flight, i) => (
            <FlightRow key={flight.fareSourceCode || i} flight={flight} />
          ))}
        </ul>
      )}
    </section>
  );
}

const FlightSearchPage = () => {
  const formId = useId();
  const originRef = useRef<HTMLInputElement>(null);

  const [tripType, setTripType] = useState<TripType>("one-way");
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [departureDate, setDepartureDate] = useState<Date | undefined>(addDays(new Date(), 7));
  const [returnDate, setReturnDate] = useState<Date | undefined>(undefined);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [state, setState] = useState<SearchState>({ status: "idle" });
  const [lastSearch, setLastSearch] = useState<SearchSnapshot | null>(null);

  const loading = state.status === "loading";

  // Keep the return date after the departure date.
  useEffect(() => {
    if (departureDate && returnDate && (isBefore(returnDate, departureDate) || isEqual(returnDate, departureDate))) {
      setReturnDate(addDays(departureDate, 7));
    }
  }, [departureDate, returnDate]);

  const handleTripTypeChange = (value: string) => {
    const next = value as TripType;
    setTripType(next);
    if (next === "one-way") {
      setReturnDate(undefined);
      setFieldErrors((e) => ({ ...e, returnDate: undefined }));
    } else if (!returnDate) {
      setReturnDate(departureDate ? addDays(departureDate, 7) : addDays(new Date(), 14));
    }
  };

  const handleSwap = () => {
    setOrigin(destination);
    setDestination(origin);
  };

  const validate = (): FieldErrors => {
    const errors: FieldErrors = {};
    if (!origin.trim()) errors.origin = "Enter where you're flying from, like BOS.";
    if (!destination.trim()) errors.destination = "Enter where you're flying to, like LIS.";
    else if (destination.trim() === origin.trim()) errors.destination = "Destination must be different from origin.";
    if (!departureDate) errors.departureDate = "Choose a departure date.";
    if (tripType === "round-trip" && !returnDate) errors.returnDate = "Choose a return date, or switch to one way.";
    return errors;
  };

  const runSearch = async (snapshot: SearchSnapshot) => {
    setState({ status: "loading" });
    setLastSearch(snapshot);
    const query = (from: string, to: string, date: Date) =>
      axios.get<FlightResult[]>(`${API_BASE_URL}/api/flights/search`, {
        params: { origin_id: from, destination_id: to, departure_date: format(date, "yyyy-MM-dd") },
      });

    try {
      const [out, back] = await Promise.all([
        query(snapshot.origin, snapshot.destination, snapshot.departureDate),
        snapshot.tripType === "round-trip" && snapshot.returnDate
          ? query(snapshot.destination, snapshot.origin, snapshot.returnDate)
          : Promise.resolve(null),
      ]);
      if (!Array.isArray(out.data) || (back && !Array.isArray(back.data))) {
        setState({ status: "error", message: "The flight search service sent a response we couldn't read." });
        return;
      }
      setState({ status: "done", outbound: out.data, inbound: back ? back.data : null });
    } catch (err) {
      console.error("Flight search failed:", err);
      setState({ status: "error", message: errorMessageFrom(err) });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      const firstKey = Object.keys(errors)[0];
      document.getElementById(`${formId}-${firstKey}`)?.focus();
      return;
    }
    void runSearch({
      tripType,
      origin: origin.trim(),
      destination: destination.trim(),
      departureDate: departureDate!,
      returnDate: tripType === "round-trip" ? returnDate : undefined,
    });
  };

  const focusForm = () => {
    originRef.current?.focus();
    originRef.current?.scrollIntoView({ block: "center" });
  };

  const fieldError = (key: keyof FieldErrors) =>
    fieldErrors[key] ? (
      <p id={`${formId}-${key}-error`} className="mt-1.5 text-sm text-destructive">
        {fieldErrors[key]}
      </p>
    ) : null;

  const codeInputProps = (key: "origin" | "destination") => ({
    id: `${formId}-${key}`,
    autoCapitalize: "characters" as const,
    autoComplete: "off",
    spellCheck: false,
    maxLength: 40,
    "aria-invalid": fieldErrors[key] ? true : undefined,
    "aria-describedby": [`${formId}-${key}-hint`, fieldErrors[key] ? `${formId}-${key}-error` : ""].filter(Boolean).join(" "),
    disabled: loading,
  });

  return (
    <div className="mx-auto w-full max-w-4xl px-gutter py-8 md:px-gutter-lg md:py-12">
      <header className="mb-6 space-y-2">
        <h1 className="text-3xl font-semibold">Search flights</h1>
        <p className="max-w-prose text-muted-foreground">
          Search one way or round trip by airport or city code. Results come straight from our flight data provider.
        </p>
      </header>

      <form onSubmit={handleSubmit} noValidate aria-label="Flight search" className="rounded-surface border bg-muted p-4 sm:p-6">
        <Tabs value={tripType} onValueChange={handleTripTypeChange}>
          <TabsList className="grid w-full grid-cols-2 sm:w-72" aria-label="Trip type">
            <TabsTrigger value="one-way">One way</TabsTrigger>
            <TabsTrigger value="round-trip">Round trip</TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="mt-5 grid grid-cols-1 items-start gap-3 md:grid-cols-[1fr_auto_1fr]">
          <div>
            <label htmlFor={`${formId}-origin`} className="mb-1.5 block text-sm font-medium">From</label>
            <Input
              ref={originRef}
              value={origin}
              onChange={(e) => setOrigin(e.target.value.toUpperCase())}
              placeholder="BOS"
              {...codeInputProps("origin")}
            />
            <p id={`${formId}-origin-hint`} className="sr-only">Airport or city code</p>
            {fieldError("origin")}
          </div>

          <div className="flex justify-center md:pt-7">
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={handleSwap}
              disabled={loading}
              aria-label="Swap origin and destination"
              className="rotate-90 rounded-full bg-background md:rotate-0"
            >
              <ArrowRightLeft aria-hidden="true" />
            </Button>
          </div>

          <div>
            <label htmlFor={`${formId}-destination`} className="mb-1.5 block text-sm font-medium">To</label>
            <Input
              value={destination}
              onChange={(e) => setDestination(e.target.value.toUpperCase())}
              placeholder="LIS"
              {...codeInputProps("destination")}
            />
            <p id={`${formId}-destination-hint`} className="sr-only">Airport or city code</p>
            {fieldError("destination")}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <span id={`${formId}-departureDate-label`} className="mb-1.5 block text-sm font-medium">Departure date</span>
            <div id={`${formId}-departureDate`} tabIndex={-1} aria-labelledby={`${formId}-departureDate-label`} className="rounded-control">
              <InlineDatePicker
                date={departureDate}
                setDate={(date) => date && setDepartureDate(date)}
                placeholder="Choose a date"
                minDate={new Date()}
                disabled={loading}
                className={cn("bg-background", fieldErrors.departureDate && "border-destructive")}
              />
            </div>
            {fieldError("departureDate")}
          </div>

          <div>
            <span id={`${formId}-returnDate-label`} className="mb-1.5 block text-sm font-medium">
              Return date {tripType === "one-way" && <span className="font-normal text-muted-foreground">(round trip only)</span>}
            </span>
            <div id={`${formId}-returnDate`} tabIndex={-1} aria-labelledby={`${formId}-returnDate-label`} className="rounded-control">
              <InlineDatePicker
                date={returnDate}
                setDate={(date) => date && setReturnDate(date)}
                placeholder={tripType === "one-way" ? "Not needed for one way" : "Choose a date"}
                minDate={departureDate ?? new Date()}
                disabled={loading || tripType === "one-way"}
                className={cn("bg-background", fieldErrors.returnDate && "border-destructive")}
              />
            </div>
            {fieldError("returnDate")}
          </div>
        </div>

        <div className="mt-6">
          <Button type="submit" size="lg" disabled={loading} className="w-full sm:w-auto">
            <Search aria-hidden="true" />
            {loading ? "Searching…" : "Search flights"}
          </Button>
        </div>
      </form>

      <div className="mt-8" aria-live="polite" aria-busy={loading}>
        {state.status === "idle" && (
          <EmptyState
            icon={Plane}
            title="Where are you flying?"
            description="Enter airport or city codes and a date to see available flights."
          />
        )}

        {state.status === "loading" && (
          <div>
            <p className="mb-3 text-sm text-muted-foreground" role="status">
              Searching flights{lastSearch ? ` from ${lastSearch.origin} to ${lastSearch.destination}` : ""}. This can take a few seconds.
            </p>
            <ResultsSkeleton />
          </div>
        )}

        {state.status === "error" && (
          <Notice
            tone="error"
            title="We couldn't load flights"
            description={state.message}
            actions={
              <>
                <Button size="sm" onClick={() => lastSearch && runSearch(lastSearch)} disabled={!lastSearch}>
                  Try again
                </Button>
                <Button size="sm" variant="outline" onClick={focusForm}>Edit search</Button>
              </>
            }
          />
        )}

        {state.status === "done" && lastSearch && (
          <div className="space-y-10">
            <ResultsSection
              title="Outbound"
              direction="outbound"
              flights={state.outbound}
              route={`${lastSearch.origin} → ${lastSearch.destination}`}
              date={lastSearch.departureDate}
              onEdit={focusForm}
            />
            {state.inbound && lastSearch.returnDate && (
              <ResultsSection
                title="Return"
                direction="return"
                flights={state.inbound}
                route={`${lastSearch.destination} → ${lastSearch.origin}`}
                date={lastSearch.returnDate}
                onEdit={focusForm}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default FlightSearchPage;
