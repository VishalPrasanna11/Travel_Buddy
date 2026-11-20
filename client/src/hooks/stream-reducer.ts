import type { StreamEvent, TravelResponse } from "@/api/LLMApi";
import type { ChatMessage, ResponseData, SectionKey, SectionStatus } from "@/components/chat/types";

const DATA_KEYS = ["status", "reason", "suggestions", "location", "trip", "itinerary", "sections", "restaurants", "attractions", "attractions_list", "hotels", "flights", "cars", "weather"] as const;

/** Keep only the structured fields we render; never the raw blob. */
export function pickData(response: TravelResponse | Record<string, unknown>): ResponseData | undefined {
  const data: Record<string, unknown> = {};
  for (const key of DATA_KEYS) {
    const v = (response as Record<string, unknown>)[key];
    if (v !== undefined && v !== null) data[key] = v;
  }
  return Object.keys(data).length ? (data as ResponseData) : undefined;
}

/** Fold one SSE event into the streaming assistant turn. Pure. */
export function applyStreamEvent(msg: ChatMessage, ev: StreamEvent): ChatMessage {
  switch (ev.event) {
    case "meta":
      return { ...msg, requestId: ev.data.request_id };
    case "agent":
      return { ...msg, progress: { ...msg.progress, [ev.data.agent]: { state: ev.data.state, count: ev.data.count, message: ev.data.message } } };
    case "plan": {
      const trip = (ev.data.trip ?? {}) as ResponseData["trip"];
      return { ...msg, data: { ...msg.data, trip: { ...msg.data?.trip, ...trip } } };
    }
    case "trip": {
      const { destination, start_date, end_date } = ev.data as { destination?: NonNullable<ResponseData["trip"]>["destination"]; start_date?: string; end_date?: string };
      return { ...msg, data: { ...msg.data, trip: { ...msg.data?.trip, ...(destination ? { destination } : {}), ...(start_date ? { start_date } : {}), ...(end_date ? { end_date } : {}) } } };
    }
    case "section": {
      const { type, section } = ev.data;
      const status: SectionStatus = { status: section.status as SectionStatus["status"], count: section.count, message: section.message };
      const data: ResponseData = { ...msg.data, sections: { ...msg.data?.sections, [type]: status } };
      if (type === "weather") {
        if (section.forecast) data.weather = section.forecast as ResponseData["weather"];
      } else if (section.items) {
        (data as Record<SectionKey, unknown>)[type] = section.items;
      }
      return { ...msg, data };
    }
    case "clarification":
      return { ...msg, status: undefined, content: String(ev.data.question ?? ""), clarification: ev.data as unknown as ChatMessage["clarification"] };
    case "delta":
      return { ...msg, content: msg.content + ev.data.text };
    case "final": {
      const data = pickData(ev.data);
      return {
        ...msg,
        status: undefined,
        content: ev.data.answer || msg.content,
        data: data ? { ...msg.data, ...data } : msg.data,
        requestId: ev.data.request_id || msg.requestId,
        serverId: (ev.data as { message_id?: string }).message_id || msg.serverId,
      };
    }
    default:
      return msg;
  }
}
