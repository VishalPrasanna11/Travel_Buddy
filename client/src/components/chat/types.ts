/**
 * Chat types. `data` holds the structured fields the ask endpoint returns
 * next to the text answer, so result cards and map pins can be rebuilt
 * from saved conversations. Nothing here is invented: every field is
 * optional and rendered only when the API returned it.
 */

export type LatLng = { lat: number; lng: number }

export type Place = {
  name: string
  address?: string
  rating?: number
  total_ratings?: number
  photo_url?: string
  location?: LatLng
  types?: string[]
}

export type Hotel = {
  name: string
  hotelId?: string
  rating?: number | string
  geoCode?: { latitude: number; longitude: number }
  address?: { countryCode?: string; cityName?: string; lines?: string[] }
}

export type Flight = {
  id?: string
  carrier?: string
  carrierName?: string
  flightNumber?: string
  departure?: { iataCode?: string; terminal?: string; at?: string }
  arrival?: { iataCode?: string; terminal?: string; at?: string }
  duration?: string
  price?: { currency?: string; total?: string; perAdult?: string }
  cabinClass?: string
}

export type WeatherReport = { report?: string }

export type ResponseData = {
  status?: string
  location?: string
  restaurants?: Place[]
  attractions?: Place[] | { attractions_list?: { attractions?: Place[] } }
  attractions_list?: { attractions?: Place[] }
  hotels?: { data?: Hotel[] }
  flights?: { data?: Flight[]; meta?: { origin?: string; destination?: string; departureDate?: string } }
  weather?: Record<string, WeatherReport>
}

export type ChatErrorKind = "timeout" | "network" | "server" | "incomplete"

export type ChatMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  createdAt?: Date | string
  /** Assistant only: structured API fields returned with this answer. */
  data?: ResponseData
  /** Assistant only: this turn failed. `content` is empty. */
  status?: "error"
  error?: { kind: ChatErrorKind; message: string }
  /** Error turns point at the user message they belong to. */
  replyTo?: string
}

export function attractionsOf(data?: ResponseData): Place[] {
  if (!data) return []
  const a = data.attractions
  if (Array.isArray(a)) return a
  return a?.attractions_list?.attractions ?? data.attractions_list?.attractions ?? []
}
