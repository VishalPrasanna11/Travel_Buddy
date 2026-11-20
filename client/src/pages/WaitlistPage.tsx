import { useId, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { ArrowLeft, CheckCircle2, Loader2 } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";

type FormData = { name: string; email: string; interests: string };
type Errors = Partial<Record<keyof FormData | "form", string>>;

const isValidEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

const WaitlistPage = () => {
  const id = useId();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth0();
  const [formData, setFormData] = useState<FormData>({ name: "", email: "", interests: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errors, setErrors] = useState<Errors>({});

  const canGoBack = window.history.length > 1;
  const homeHref = isAuthenticated ? "/home" : "/";

  const validate = (): Errors => {
    const next: Errors = {};
    if (!formData.name.trim()) next.name = "Enter your name.";
    else if (formData.name.trim().length < 2) next.name = "Name must be at least 2 characters.";
    if (!formData.email.trim()) next.email = "Enter your email address.";
    else if (!isValidEmail(formData.email)) next.email = "Enter an email like name@example.com.";
    return next;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name as keyof FormData]) setErrors((prev) => ({ ...prev, [name]: undefined, form: undefined }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;
    const next = validate();
    setErrors(next);
    const firstInvalid = (["name", "email"] as const).find((k) => next[k]);
    if (firstInvalid) {
      document.getElementById(`${id}-${firstInvalid}`)?.focus();
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch("https://formspree.io/f/meoabraq", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      if (!response.ok) throw new Error("Submission failed");
      setIsSuccess(true);
      setFormData({ name: "", email: "", interests: "" });
    } catch (err) {
      console.error("Waitlist submission error:", err);
      setErrors({ form: "Your request didn't go through. Check your connection and try again." });
    } finally {
      setIsLoading(false);
    }
  };

  const describedBy = (key: keyof FormData, hint?: boolean) =>
    [hint ? `${id}-${key}-hint` : "", errors[key] ? `${id}-${key}-error` : ""].filter(Boolean).join(" ") || undefined;

  const fieldError = (key: keyof FormData) =>
    errors[key] ? (
      <p id={`${id}-${key}-error`} className="mt-1.5 text-sm text-destructive">{errors[key]}</p>
    ) : null;

  return (
    <div className="mx-auto w-full max-w-lg px-gutter py-10 md:py-16">
      {canGoBack ? (
        <Button variant="ghost" size="sm" className="-ml-3 mb-6" onClick={() => navigate(-1)}>
          <ArrowLeft aria-hidden="true" /> Back
        </Button>
      ) : (
        <Link to={homeHref} viewTransition className={buttonVariants({ variant: "ghost", size: "sm", className: "-ml-3 mb-6" })}>
          <ArrowLeft aria-hidden="true" /> Back to home
        </Link>
      )}

      <h1 className="text-3xl font-semibold">This part of TravelBuddy isn't built yet</h1>
      <p className="mt-3 text-muted-foreground">
        Explore, Saved trips, Updates, Inspiration and Create are on the way. Leave your email and we'll
        tell you when they're ready. Trip planning in chat works today.
      </p>

      {isSuccess ? (
        <div className="mt-8 space-y-4">
          <Notice
            tone="success"
            icon={CheckCircle2}
            title="You're on the list"
            description="We'll email you when these features launch. No other emails."
          />
          <div className="flex flex-wrap gap-3">
            <Link to={homeHref} viewTransition className={buttonVariants()}>
              {isAuthenticated ? "Plan a trip" : "Back to home"}
            </Link>
            <Button variant="outline" onClick={() => setIsSuccess(false)}>Add another email</Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate className="mt-8 space-y-5">
          <div>
            <label htmlFor={`${id}-name`} className="mb-1.5 block text-sm font-medium">Name</label>
            <Input
              id={`${id}-name`}
              name="name"
              autoComplete="name"
              value={formData.name}
              onChange={handleChange}
              disabled={isLoading}
              aria-invalid={errors.name ? true : undefined}
              aria-describedby={describedBy("name")}
            />
            {fieldError("name")}
          </div>

          <div>
            <label htmlFor={`${id}-email`} className="mb-1.5 block text-sm font-medium">Email</label>
            <Input
              id={`${id}-email`}
              name="email"
              type="email"
              inputMode="email"
              autoComplete="email"
              value={formData.email}
              onChange={handleChange}
              disabled={isLoading}
              aria-invalid={errors.email ? true : undefined}
              aria-describedby={describedBy("email")}
            />
            {fieldError("email")}
          </div>

          <div>
            <label htmlFor={`${id}-interests`} className="mb-1.5 block text-sm font-medium">
              What would you use first? <span className="font-normal text-muted-foreground">(optional)</span>
            </label>
            <Input
              id={`${id}-interests`}
              name="interests"
              value={formData.interests}
              onChange={handleChange}
              disabled={isLoading}
              aria-describedby={describedBy("interests", true)}
            />
            <p id={`${id}-interests-hint`} className="mt-1.5 text-sm text-muted-foreground">
              For example: saved trips, price alerts, trip ideas.
            </p>
          </div>

          <div role="status" aria-live="polite">
            {errors.form && <Notice tone="error" title="Couldn't join the waitlist" description={errors.form} />}
          </div>

          <Button type="submit" size="lg" disabled={isLoading} className="w-full sm:w-auto">
            {isLoading ? <><Loader2 className="animate-spin" aria-hidden="true" /> Joining…</> : "Join the waitlist"}
          </Button>
          <p className="text-sm text-muted-foreground">We only use your email to tell you about these features.</p>
        </form>
      )}
    </div>
  );
};

export default WaitlistPage;
