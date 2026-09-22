export type StateTone = "good" | "off" | "bad" | "warn";

/** Maps a Capella cluster / App Service state to a badge tone. */
export function stateTone(state: string | null | undefined): StateTone {
  const value = (state ?? "").toLowerCase();
  if (value === "healthy" || value === "online") {
    return "good";
  }
  if (value === "turnedoff" || value === "turned_off" || value === "offline") {
    return "off";
  }
  if (value.includes("degrad") || value.includes("fail") || value.includes("error")) {
    return "bad";
  }
  return "warn";
}
