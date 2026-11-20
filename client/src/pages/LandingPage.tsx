import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ExamplePreview } from "@/components/marketing/ExamplePreview";
import { HowItWorks } from "@/components/marketing/HowItWorks";

const LandingPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();

  // Signed-in visitors go straight to their home screen.
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate("/home");
    }
  }, [isAuthenticated, navigate, isLoading]);

  const startPlanning = () =>
    loginWithRedirect({ authorizationParams: { screen_hint: "signup" } });

  return (
    <>
      {/* Hero */}
      <section aria-labelledby="hero-heading" className="border-b">
        <div className="mx-auto grid max-w-6xl items-start gap-12 px-gutter py-section md:px-gutter-lg lg:grid-cols-[1fr_minmax(0,28rem)] lg:gap-16">
          {/* Sticky on wide screens so the offer stays beside the long example. */}
          <div className="space-y-6 lg:sticky lg:top-[calc(var(--spacing-header)+3rem)] lg:pt-12">
            <h1 id="hero-heading" className="text-display font-semibold">
              Plan a whole trip in one conversation
            </h1>
            <p className="max-w-xl text-lg text-muted-foreground">
              Tell TravelBuddy where you're going and when. It looks up flights, hotels, things to see, places to eat
              and the weather, then gives you one itinerary you can act on.
            </p>
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Button size="lg" onClick={startPlanning}>
                Plan a trip
                <ArrowRight aria-hidden="true" />
              </Button>
              <Button size="lg" variant="ghost" asChild>
                <a href="#how-it-works">See how it works</a>
              </Button>
            </div>
          </div>

          <div>
            <ExamplePreview />
          </div>
        </div>
      </section>

      <HowItWorks />

      {/* Closing call to action */}
      <section aria-labelledby="cta-heading" className="border-t">
        <div className="mx-auto flex max-w-6xl flex-col items-start gap-6 px-gutter py-section md:flex-row md:items-center md:justify-between md:px-gutter-lg">
          <div className="space-y-2">
            <h2 id="cta-heading" className="text-title font-semibold">Where are you headed next?</h2>
            <p className="text-muted-foreground">Start with one sentence. You can change everything afterwards.</p>
          </div>
          <Button size="lg" onClick={startPlanning}>
            Plan a trip
            <ArrowRight aria-hidden="true" />
          </Button>
        </div>
      </section>
    </>
  );
};

export default LandingPage;
