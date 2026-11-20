import { useState } from "react";
import { Loader2, CheckCircle, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const Footer = () => {
    const [email, setEmail] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [error, setError] = useState("");

    const isValidEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (!email.trim()) {
            setError("Enter your email address.");
            return;
        }
        if (!isValidEmail(email)) {
            setError("That email address doesn't look complete. Check it and try again.");
            return;
        }

        try {
            setIsLoading(true);
            const response = await fetch("https://formspree.io/f/mgvajnwk", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email }),
            });
            if (!response.ok) throw new Error("Submission failed");

            setIsSuccess(true);
            setEmail("");
            setTimeout(() => setIsSuccess(false), 3000);
        } catch (err) {
            console.error("Subscription error:", err);
            setError("We couldn't sign you up just now. Try again in a minute.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <footer className="border-t bg-muted">
            <div className="mx-auto max-w-6xl px-gutter md:px-gutter-lg py-12">
                <div className="flex flex-col gap-10 md:flex-row md:items-end md:justify-between">
                    <div className="max-w-md space-y-3">
                        <h2 className="text-heading font-semibold">Trip ideas by email</h2>
                        <p className="text-muted-foreground">
                            Occasional trip ideas and TravelBuddy updates.
                        </p>
                        <form onSubmit={handleSubmit} noValidate>
                            <label htmlFor="footer-email" className="sr-only">Email address</label>
                            <div className="flex gap-2">
                                <Input
                                    id="footer-email"
                                    type="email"
                                    name="email"
                                    autoComplete="email"
                                    placeholder="Your email address"
                                    aria-invalid={error ? true : undefined}
                                    aria-describedby={error ? "footer-email-error" : undefined}
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    disabled={isLoading || isSuccess}
                                    className="bg-background"
                                />
                                <Button type="submit" className="min-w-[7.5rem]" disabled={isLoading || isSuccess}>
                                    {isLoading ? (
                                        <Loader2 className="animate-spin" aria-label="Subscribing" />
                                    ) : isSuccess ? (
                                        <CheckCircle aria-label="Subscribed" />
                                    ) : (
                                        "Subscribe"
                                    )}
                                </Button>
                            </div>
                            <p className="mt-2 min-h-5 text-sm" role="status" aria-live="polite">
                                {error && <span id="footer-email-error" className="text-destructive">{error}</span>}
                                {isSuccess && <span className="text-success-ink">You're on the list. Thanks!</span>}
                            </p>
                        </form>
                    </div>
                </div>

                <div className="mt-10 flex flex-col gap-4 border-t pt-6 md:flex-row md:items-center md:justify-between">
                    <span className="text-sm text-muted-foreground">&copy; {new Date().getFullYear()} TravelBuddy</span>
                    <a
                        href="https://github.com/DAMG7245/Travel_Buddy"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex min-h-11 items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
                    >
                        Source on GitHub
                        <ExternalLink className="size-3.5" aria-hidden="true" />
                        <span className="sr-only">(opens in a new tab)</span>
                    </a>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
