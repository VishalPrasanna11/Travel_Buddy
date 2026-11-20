import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { v4 as uuidv4 } from "uuid";
import { ArrowRight, ExternalLink, ImageOff } from "lucide-react";
import { useCreateMyUser } from "@/api/UserApi";
import { Button } from "@/components/ui/button";

import kyotoImg from "@/assets/kyoto.jpeg";
import barcelonaImg from "@/assets/barcelona.jpeg";
import newZealandImg from "@/assets/new-zealand.jpeg";
import marrakechImg from "@/assets/marrakech.jpeg";
import culturalImg from "@/assets/cultural.jpeg";
import adventureImg from "@/assets/adventure.jpeg";
import culinaryImg from "@/assets/culinary.jpeg";
import luxuryImg from "@/assets/luxury.jpeg";

/**
 * Contract with the chat page: we navigate to /chat/:id with
 * `location.state = { prompt: string }`. The chat page sends that prompt
 * as the first message, once.
 */
export type ChatLaunchState = { prompt: string };

const exampleTrips = [
  "4 days in Lisbon in May from Boston, two adults, mid-range, food and old neighborhoods",
  "A week in Japan in April from San Francisco: Tokyo then Kyoto, temples and food markets",
  "Family weekend in Chicago from Detroit in July with two kids, museums and the lakefront",
  "5 days in Mexico City in October from Austin, budget-friendly, street food and art",
];

const destinations = [
  { name: "Kyoto", country: "Japan", blurb: "Temples, gardens and quiet lanes", image: kyotoImg, guide: "https://kyoto.travel/en/", guideSource: "kyoto.travel" },
  { name: "Barcelona", country: "Spain", blurb: "Gaudí, beaches and late dinners", image: barcelonaImg, guide: "https://www.ricksteves.com/europe/spain/barcelona", guideSource: "ricksteves.com" },
  { name: "New Zealand", country: "Oceania", blurb: "Big landscapes and long drives", image: newZealandImg, guide: "https://www.petrinadarrah.com/new-zealand-travel-guide", guideSource: "petrinadarrah.com" },
  { name: "Marrakech", country: "Morocco", blurb: "Souks, riads and the Atlas nearby", image: marrakechImg, guide: "https://www.stokedtotravel.com/3-days-in-marrakech/", guideSource: "stokedtotravel.com" },
];

const travelStyles = [
  { name: "Cultural", image: culturalImg, link: "https://www.worldpackers.com/articles/cultural-travel", source: "worldpackers.com" },
  { name: "Adventure", image: adventureImg, link: "https://www.exploreworldwide.com/", source: "exploreworldwide.com" },
  { name: "Culinary", image: culinaryImg, link: "https://travelsquire.com/bringing-culinary-travel-inspiration-home/", source: "travelsquire.com" },
  { name: "Luxury", image: luxuryImg, link: "https://www.jacadatravel.com/experience-type/", source: "jacadatravel.com" },
];

const readingList = [
  { title: "Best time to visit Thailand", source: "enchantingtravels.com", url: "https://www.enchantingtravels.com/destinations/asia/thailand/best-time-to-visit-thailand/" },
  { title: "Hidden gems in Portugal", source: "europeanbestdestinations.com", url: "https://www.europeanbestdestinations.com/destinations/portugal/best-hidden-gems-in-portugal/" },
  { title: "Budget-friendly European cities", source: "travelbinger.com", url: "https://travelbinger.com/europe-budget/" },
];

/** Image with a fixed aspect ratio and a calm fallback if it fails to load. */
function IdeaImage({ src, alt, ratio }: { src: string; alt: string; ratio: string }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={`${ratio} w-full overflow-hidden rounded-lg bg-muted`}>
      {failed ? (
        <div className="flex h-full w-full items-center justify-center text-muted-foreground">
          <ImageOff className="size-6" aria-hidden="true" />
          <span className="sr-only">Image unavailable</span>
        </div>
      ) : (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          decoding="async"
          onError={() => setFailed(true)}
          className="h-full w-full object-cover transition-transform duration-300 ease-out group-hover:scale-[1.02]"
        />
      )}
    </div>
  );
}

function ExternalSource({ href, children, source }: { href: string; children: React.ReactNode; source: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex min-h-11 items-center gap-1.5 rounded-md text-sm text-muted-foreground hover:text-foreground"
    >
      {children}
      <ExternalLink className="size-3.5" aria-hidden="true" />
      <span className="sr-only">(opens {source} in a new tab)</span>
    </a>
  );
}

const HomePage = () => {
  const { user } = useAuth0();
  const { createUser } = useCreateMyUser();
  const navigate = useNavigate();
  const hasCreatedUser = useRef(false);
  const [prompt, setPrompt] = useState("");

  // Make sure the signed-in user exists in our database (once per visit).
  useEffect(() => {
    if (user?.sub && user.email && !hasCreatedUser.current) {
      hasCreatedUser.current = true;
      createUser({ auth0id: user.sub, email: user.email }).catch((err) =>
        console.error("Could not register user:", err)
      );
    }
  }, [createUser, user]);

  const startTrip = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const state: ChatLaunchState = { prompt: trimmed };
    navigate(`/chat/${uuidv4()}`, { state });
  };

  const firstName = user?.given_name || (user?.name && !user.name.includes("@") ? user.name.split(" ")[0] : "");

  return (
    <div className="mx-auto w-full max-w-6xl px-gutter md:px-gutter-lg">
      {/* Launcher */}
      <section aria-labelledby="home-heading" className="py-section">
        <div className="mx-auto max-w-2xl">
          <h1 id="home-heading" className="text-display font-semibold">
            {firstName ? `Where to next, ${firstName}?` : "Where to next?"}
          </h1>
          <p className="mt-3 text-lg text-muted-foreground">
            Describe the trip in a sentence or two. TravelBuddy will put together flights, hotels, things to do and
            the weather.
          </p>

          <form
            className="mt-8"
            onSubmit={(e) => {
              e.preventDefault();
              startTrip(prompt);
            }}
          >
            <label htmlFor="trip-prompt" className="text-sm font-semibold">
              Describe your trip
            </label>
            <div className="mt-2 rounded-surface border border-input bg-background p-2 transition-[border-color,box-shadow] duration-150 focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/25">
              <textarea
                id="trip-prompt"
                rows={3}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    startTrip(prompt);
                  }
                }}
                placeholder="Where, when, from where, who's coming, what you enjoy"
                aria-describedby="trip-prompt-hint"
                className="block w-full resize-none bg-transparent px-2 py-1.5 text-base outline-none placeholder:text-muted-foreground"
              />
              <div className="flex items-center justify-between gap-3 px-2 pb-1">
                <p id="trip-prompt-hint" className="text-meta text-muted-foreground">
                  Enter to start · Shift + Enter for a new line
                </p>
                <Button type="submit" disabled={!prompt.trim()}>
                  Plan this trip
                  <ArrowRight aria-hidden="true" />
                </Button>
              </div>
            </div>
          </form>

          <div className="mt-8">
            <h2 className="text-sm font-semibold">Or start from an example</h2>
            <ul className="mt-3 flex flex-col gap-2">
              {exampleTrips.map((trip) => (
                <li key={trip}>
                  <button
                    type="button"
                    onClick={() => startTrip(trip)}
                    className="group flex min-h-11 w-full items-center justify-between gap-3 rounded-control border px-4 py-2.5 text-left text-sm hover:border-gray-strong hover:bg-muted"
                  >
                    <span>{trip}</span>
                    <ArrowRight className="size-4 shrink-0 text-muted-foreground transition-transform duration-150 group-hover:translate-x-0.5" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Ideas */}
      <section aria-labelledby="ideas-heading" className="border-t pb-section pt-12">
        <h2 id="ideas-heading" className="text-title font-semibold">Ideas to explore</h2>
        <p className="mt-1 text-muted-foreground">Not sure yet? Start from a place, or read a guide first.</p>

        <ul className="mt-8 grid gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          {destinations.map((d) => (
            <li key={d.name} className="group flex flex-col">
              <IdeaImage src={d.image} alt={`${d.name}, ${d.country}`} ratio="aspect-[4/5]" />
              <h3 className="mt-3 text-heading font-semibold">{d.name}</h3>
              <p className="text-sm text-muted-foreground">{d.country} · {d.blurb}</p>
              <div className="mt-2 flex flex-wrap items-center gap-x-4">
                <Button
                  variant="link"
                  className="min-h-11"
                  onClick={() => startTrip(`Plan a trip to ${d.name}, ${d.country}. Ask me for dates, origin and budget if you need them.`)}
                >
                  Plan a trip here
                </Button>
                <ExternalSource href={d.guide} source={d.guideSource}>Guide</ExternalSource>
              </div>
            </li>
          ))}
        </ul>

        <div className="mt-14 grid gap-10 lg:grid-cols-[1fr_20rem]">
          <div>
            <h3 className="text-heading font-semibold">By travel style</h3>
            <ul className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
              {travelStyles.map((s) => (
                <li key={s.name}>
                  <a
                    href={s.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group block rounded-lg"
                  >
                    <IdeaImage src={s.image} alt="" ratio="aspect-square" />
                    <span className="mt-2 flex items-center gap-1.5 text-sm font-semibold">
                      {s.name}
                      <ExternalLink className="size-3.5 text-muted-foreground" aria-hidden="true" />
                    </span>
                    <span className="sr-only">(opens {s.source} in a new tab)</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-heading font-semibold">Worth a read</h3>
            <ul className="mt-2 divide-y">
              {readingList.map((r) => (
                <li key={r.url} className="py-2">
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex min-h-11 items-start justify-between gap-3 rounded-md py-1"
                  >
                    <span>
                      <span className="block font-semibold group-hover:text-raspberry">{r.title}</span>
                      <span className="text-meta text-muted-foreground">{r.source}</span>
                    </span>
                    <ExternalLink className="mt-1 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                    <span className="sr-only">(opens in a new tab)</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
