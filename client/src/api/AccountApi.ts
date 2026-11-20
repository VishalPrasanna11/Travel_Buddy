import { useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, useApiToken } from "@/api/ConversationsApi";
import { setDisplayLocale } from "@/lib/format";
import type { Hotel, Place, ResponseData } from "@/components/chat/types";

const API_BASE_URL = import.meta.env.VITE_BASE_URL ?? "";

export type Preferences = {
  locale: string | null;
  currency: string;
  units: "metric" | "imperial";
  home_airport: string | null;
  default_adults: number;
  default_children: number;
};

function useSignedIn() {
  const { isAuthenticated } = useAuth0();
  return isAuthenticated || (import.meta.env.DEV && !!import.meta.env.VITE_DEV_BEARER);
}

export function usePreferences() {
  const getToken = useApiToken();
  const enabled = useSignedIn();
  return useQuery({
    queryKey: ["preferences"],
    enabled,
    staleTime: 5 * 60_000,
    queryFn: async () => api<Preferences>("/api/users/preferences", await getToken()),
  });
}

export function useSavePreferences() {
  const getToken = useApiToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Partial<Preferences>) =>
      api<Preferences>("/api/users/preferences", await getToken(), { method: "PATCH", body: JSON.stringify(patch) }),
    onSuccess: (prefs) => qc.setQueryData(["preferences"], prefs),
  });
}

/** Applies the saved locale to all number/date formatting. Mount once. */
export function PreferencesSync() {
  const { data } = usePreferences();
  useEffect(() => {
    setDisplayLocale(data?.locale);
  }, [data?.locale]);
  return null;
}

// ----------------------------------------------------------------- saved
export type SavedKind = "place" | "restaurant" | "hotel";
export type SavedItem = { id: string; entity_id: string; kind: SavedKind; name: string; entity: Place & Hotel; conversation_id?: string; created_at?: string };

export function useSavedPlaces() {
  const getToken = useApiToken();
  const enabled = useSignedIn();
  return useQuery({
    queryKey: ["saved-places"],
    enabled,
    staleTime: 60_000,
    queryFn: async () => (await api<{ items: SavedItem[] }>("/api/saved-places", await getToken())).items,
  });
}

export function useToggleSaved() {
  const getToken = useApiToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ entity, kind, saved, conversationId }: { entity: Place | Hotel; kind: SavedKind; saved: boolean; conversationId?: string }) => {
      const token = await getToken();
      if (saved) {
        await api<void>(`/api/saved-places/${encodeURIComponent(entity.id!)}`, token, { method: "DELETE" });
        return null;
      }
      return api<SavedItem>("/api/saved-places", token, { method: "POST", body: JSON.stringify({ entity, kind, conversation_id: conversationId }) });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["saved-places"] }),
  });
}

// ----------------------------------------------------------------- trips
export async function downloadTripFile(tripId: string, format: "ics" | "pdf", token?: string) {
  if (!token) throw new Error("Sign in to download.");
  const res = await fetch(`${API_BASE_URL}/api/trips/${encodeURIComponent(tripId)}/export?format=${format}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message || body?.detail || "Download failed.");
  }
  const blob = await res.blob();
  const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") || "")?.[1] || `trip.${format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function shareTrip(tripId: string, token?: string) {
  return api<{ token: string; url: string }>(`/api/trips/${encodeURIComponent(tripId)}/share`, token);
}

export type SharedTrip = { title: string; answer: string; data: ResponseData; shared_at: string; token: string };

export async function getSharedTrip(token: string): Promise<SharedTrip> {
  const res = await fetch(`${API_BASE_URL}/api/shared/${encodeURIComponent(token)}`);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body?.error?.message || body?.detail || "This link isn't available.");
  return body as SharedTrip;
}
