import { Notice } from "@/components/ui/notice"
import type { ResponseData } from "./types"

/**
 * Weather honesty. When OpenWeather isn't available the backend returns one
 * fixed sentence ("…currently 22°C (72°F) with clear skies. The humidity is
 * around 65% with light winds.") with no flag. Until the API marks simulated
 * data (see report), we recognise that template and label it as an estimate.
 */
const SIMULATED = /currently 22°C \(72°F\) with clear skies\. The humidity is around 65% with light winds/i

export function isSimulatedWeather(text: string) {
  return SIMULATED.test(text)
}

export function WeatherNote({ data, answer }: { data?: ResponseData; answer: string }) {
  const reports = Object.values(data?.weather ?? {}).map((w) => w?.report ?? "")
  const simulated = reports.some(isSimulatedWeather) || isSimulatedWeather(answer)
  if (!simulated) return null

  return (
    <Notice
      tone="estimate"
      className="mt-6 max-w-prose"
      title="Weather is an estimate"
      description="Live weather wasn't available for this answer, so any temperature or conditions mentioned are placeholders, not a forecast. Check a weather service before you pack."
    />
  )
}
