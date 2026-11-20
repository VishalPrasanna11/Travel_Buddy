/**
 * Chat types. `data` holds the structured fields the ask endpoint returns
 * next to the text answer, so result cards and map pins can be rebuilt
 * from saved conversations. Nothing here is invented: every field is
 * optional and rendered only when the API returned it.
 *
 * Entities follow the server schemas (server/schemas/entities.py): each has
 * id, source, fetched_at and is_estimate. Older saved conversations used
 * looser shapes; the *Of() readers below accept both.
 */

export type LatLng = { lat: number; lng: number }

export type Source = "routestack" | "google_places" | "openweather" | "simulated"

type Entity = { id?: string; source?: Source; fetched_at?: string; is_estimate?: boolean }

export type Price = {
  amount: number
  currency: string
  basis?: "total" | "per_night" | "per_person" | "per_day" | "per_trip"
  total?: number
  per_traveler?: number
  taxes_included?: boolean
  published?: number
  saving?: number
  as_of?: string
}

export type Photo = {
  ref?: string
  url?: string
  width?: number
  height?: number
  attributions?: { name?: string; uri?: string }[]
}

export type OpeningHours = { open_now?: boolean; weekday_descriptions?: string[] }

export type Place = Entity & {
  kind?: "attraction" | "restaurant" | "destination" | "other"
  place_id?: string
  name: string
  address?: string
  rating?: number
  total_ratings?: number
  /** Legacy single photo URL. */
  photo_url?: string
  photos?: Photo[]
  location?: LatLng
  types?: string[]
  primary_type?: string
  price_level?: number
  editorial_summary?: string
  opening_hours?: OpeningHours
  website?: string
  google_maps_uri?: string
  phone?: string
  reviews?: { author?: string; rating?: number; text?: string; relative_time?: string }[]
}

export type FlightEndpoint = { airport?: string; airport_name?: string; terminal?: string; at?: string; utc_offset?: string }

export type FlightSegment = {
  carrier?: string
  carrier_name?: string
  flight_number?: string
  departure: FlightEndpoint
  arrival: FlightEndpoint
  duration_minutes?: number
  duration?: string
  cabin_class?: string
  layover_minutes?: number
}

export type Flight = Entity & {
  carrier?: string
  carrier_name?: string
  origin?: string
  destination?: string
  departure_at?: string
  arrival_at?: string
  duration_minutes?: number
  duration?: string
  stops?: number
  cabin_class?: string
  segments?: FlightSegment[]
  return_segments?: FlightSegment[]
  price?: Price
  baggage?: { checked?: string; cabin?: string }
  refundable?: boolean
  booking_url?: string
}

export type Hotel = Entity & {
  name: string
  address?: string
  location?: LatLng
  star_rating?: number
  guest_rating?: number
  review_count?: number
  price?: Price
  nightly_price?: Price
  nights?: number
  check_in?: string
  check_out?: string
  check_in_time?: string
  check_out_time?: string
  amenities?: string[]
  amenity_names?: string[]
  photos?: Photo[]
  cancellation_policy?: string
  refundable?: boolean
  provider?: string
  booking_url?: string
}

export type CarRental = Entity & {
  vendor?: string
  name: string
  category?: string
  transmission?: string
  seats?: number
  bags?: number
  air_conditioning?: boolean
  image_url?: string
  pickup_location?: string
  dropoff_location?: string
  pickup_at?: string
  dropoff_at?: string
  price?: Price
  booking_url?: string
}

export type WeatherDay = Entity & {
  date: string
  temp_min?: number
  temp_max?: number
  units?: "metric" | "imperial"
  condition_id?: number
  condition?: string
  icon?: string
  pop?: number
  uvi?: number
  sunrise?: string
  sunset?: string
  kind?: "forecast" | "day_summary" | "simulated"
}

export type WeatherForecast = Entity & {
  location: string
  units?: "metric" | "imperial"
  is_simulated?: boolean
  reason?: string
  timezone?: string
  days?: WeatherDay[]
  alerts?: { event: string; sender?: string; start?: string; end?: string; description?: string }[]
  report?: string
}

/** Legacy: { [location]: { report } } */
export type WeatherReport = { report?: string; is_simulated?: boolean; forecast?: WeatherForecast }

export type SectionKey = "flights" | "hotels" | "attractions" | "restaurants" | "weather" | "cars"

export type SectionStatus = {
  status: "ok" | "empty" | "failed" | "skipped" | "estimate"
  count?: number
  message?: string
  reason?: string
  alternatives?: string[]
  code?: string
}

export type TripDestination = {
  name: string
  formatted_name?: string
  address?: string
  place_id?: string
  lat?: number
  lng?: number
  timezone?: string
  viewport?: { low: LatLng; high: LatLng }
}

export type Trip = {
  intent?: string
  formatted_name?: string
  destination?: string | TripDestination
  origin?: string
  start_date?: string
  end_date?: string
  adults?: number
  children?: number
  sections?: string[]
}

export type ItineraryItem = {
  slot: "morning" | "afternoon" | "evening" | "night"
  kind: "place" | "restaurant" | "hotel" | "flight" | "car" | "transit" | "free" | "note"
  ref?: string | null
  title: string
  note?: string | null
  start_time?: string | null
  duration_minutes?: number | null
}

export type Itinerary = {
  trip: {
    destination: TripDestination
    origin?: string | null
    start_date: string
    end_date: string
    travelers?: { adults: number; children: number }
  }
  days: { date: string; title: string; items: ItineraryItem[] }[]
  summary?: string
}

export type ResponseData = {
  status?: string
  itinerary?: Itinerary
  location?: string
  trip?: Trip
  sections?: Partial<Record<SectionKey, SectionStatus>>
  restaurants?: Place[]
  attractions?: Place[] | { attractions_list?: { attractions?: Place[] } }
  attractions_list?: { attractions?: Place[] }
  hotels?: Hotel[] | { data?: LegacyHotel[] }
  flights?: Flight[] | { data?: LegacyFlight[] }
  cars?: CarRental[]
  weather?: WeatherForecast | Record<string, WeatherReport>
}

// ------------------------------------------------------- legacy shapes
type LegacyHotel = {
  name: string
  hotelId?: string
  rating?: number | string
  geoCode?: { latitude: number; longitude: number }
  address?: { countryCode?: string; cityName?: string; lines?: string[] }
}

type LegacyFlight = {
  id?: string
  carrier?: string
  carrierName?: string
  flightNumber?: string
  departure?: { iataCode?: string; at?: string }
  arrival?: { iataCode?: string; at?: string }
  duration?: string
  price?: { currency?: string; total?: string }
  cabinClass?: string
}

// --------------------------------------------------------------- agents
export type AgentKey = "intake" | SectionKey | "compose"
export type AgentState = "queued" | "running" | "done" | "empty" | "failed" | "skipped"
export type AgentProgressMap = Partial<Record<AgentKey, { state: AgentState; count?: number; message?: string }>>

export type ChatErrorKind = "timeout" | "network" | "server" | "incomplete" | "rate_limited" | "cancelled"

export type ChatMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  createdAt?: Date | string
  /** Assistant only: structured API fields returned with this answer. */
  data?: ResponseData
  /** Assistant only: error = this turn failed; streaming = still arriving. */
  status?: "error" | "streaming"
  error?: { kind: ChatErrorKind; message: string; code?: string; requestId?: string; retryAfter?: number }
  /** Error turns point at the user message they belong to. */
  replyTo?: string
  /** Streaming progress, per agent. */
  progress?: AgentProgressMap
  requestId?: string
}

// -------------------------------------------------------------- readers
export function attractionsOf(data?: ResponseData): Place[] {
  if (!data) return []
  const a = data.attractions
  if (Array.isArray(a)) return a
  return a?.attractions_list?.attractions ?? data.attractions_list?.attractions ?? []
}

export function restaurantsOf(data?: ResponseData): Place[] {
  return Array.isArray(data?.restaurants) ? data!.restaurants : []
}

export function hotelsOf(data?: ResponseData): Hotel[] {
  const h = data?.hotels
  if (!h) return []
  if (Array.isArray(h)) return h
  return (h.data ?? []).map((l) => ({
    id: l.hotelId,
    name: l.name,
    star_rating: typeof l.rating === "string" ? Number.parseFloat(l.rating) || undefined : l.rating,
    address: [l.address?.cityName, l.address?.countryCode].filter(Boolean).join(", ") || undefined,
    location: l.geoCode ? { lat: l.geoCode.latitude, lng: l.geoCode.longitude } : undefined,
  }))
}

export function flightsOf(data?: ResponseData): Flight[] {
  const f = data?.flights
  if (!f) return []
  if (Array.isArray(f)) return f
  return (f.data ?? []).map((l) => {
    const amount = l.price?.total ? Number.parseFloat(l.price.total) : NaN
    const seg: FlightSegment = {
      carrier: l.carrier,
      carrier_name: l.carrierName,
      flight_number: l.flightNumber,
      departure: { airport: l.departure?.iataCode, at: l.departure?.at },
      arrival: { airport: l.arrival?.iataCode, at: l.arrival?.at },
      duration: l.duration,
    }
    return {
      id: l.id,
      carrier: l.carrier,
      carrier_name: l.carrierName,
      origin: l.departure?.iataCode,
      destination: l.arrival?.iataCode,
      departure_at: l.departure?.at,
      arrival_at: l.arrival?.at,
      duration: l.duration,
      cabin_class: l.cabinClass,
      stops: 0,
      segments: [seg],
      price: Number.isNaN(amount) ? undefined : { amount, currency: l.price?.currency || "USD" },
    }
  })
}

/** Typed forecast, or a legacy report flagged as simulated when it matches the old template. */
export function weatherOf(data?: ResponseData): WeatherForecast | null {
  const w = data?.weather
  if (!w) return null
  if ("location" in w && typeof (w as WeatherForecast).location === "string") return w as WeatherForecast
  const first = Object.entries(w as Record<string, WeatherReport>)[0]
  if (!first) return null
  const [location, report] = first
  if (report?.forecast) return report.forecast
  const simulated = report?.is_simulated ?? /currently 22°C \(72°F\) with clear skies/i.test(report?.report ?? "")
  return { location, report: report?.report, is_simulated: simulated, days: [] }
}

export function carsOf(data?: ResponseData): CarRental[] {
  return Array.isArray(data?.cars) ? data!.cars : []
}

export function destinationOf(data?: ResponseData): TripDestination | null {
  const d = data?.trip?.destination
  if (!d) return null
  return typeof d === "string" ? { name: d } : d
}

/** Every entity in a response by id, for itinerary refs. */
export function entityIndex(data?: ResponseData): Map<string, { kind: string; entity: Place | Hotel | Flight | CarRental }> {
  const out = new Map<string, { kind: string; entity: Place | Hotel | Flight | CarRental }>()
  const add = (kind: string, list: (Place | Hotel | Flight | CarRental)[]) => list.forEach((e) => e.id && out.set(e.id, { kind, entity: e }))
  add("flight", flightsOf(data))
  add("hotel", hotelsOf(data))
  add("place", attractionsOf(data))
  add("restaurant", restaurantsOf(data))
  add("car", carsOf(data))
  return out
}

const API_BASE_URL = import.meta.env.VITE_BASE_URL ?? ""

/** Photo through the server proxy (no API key in the browser). */
export function photoSrc(photos?: Photo[], legacyUrl?: string, width = 400): string | undefined {
  const ref = photos?.find((p) => p.ref)?.ref
  if (ref) return `${API_BASE_URL}/api/places/photo/${ref}?w=${width}`
  const url = photos?.find((p) => p.url)?.url ?? legacyUrl
  if (!url) return undefined
  return url.startsWith("/") ? `${API_BASE_URL}${url}` : url
}
