import { useState } from "react";
import { Link } from "react-router-dom";
import { Globe, MessageCircle, Share2, Loader2, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// TODO(Phase 3, clarify): legal links point at routes that don't exist yet and
// the social links are placeholders. Content is unchanged here; only styling.

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
            setError("Email is required");
            return;
        }
        if (!isValidEmail(email)) {
            setError("Please enter a valid email address");
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
            setError("Failed to subscribe. Please try again later.");
        } finally {
            setIsLoading(false);
        }
    };

    const linkClass =
        "text-sm text-muted-foreground hover:text-foreground transition-colors inline-flex items-center min-h-11";
    const iconLinkClass =
        "inline-flex size-11 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors";

    return (
        <footer className="border-t bg-muted">
            <div className="mx-auto max-w-6xl px-gutter md:px-gutter-lg py-12">
                <div className="flex flex-col gap-10 md:flex-row md:items-end md:justify-between">
                    <div className="max-w-md space-y-3">
                        <h2 className="text-2xl font-semibold">Stay inspired</h2>
                        <p className="text-muted-foreground">
                            Subscribe to receive AI travel insights and personalized destination recommendations
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
                                {isSuccess && <span className="text-success-ink">Successfully subscribed!</span>}
                            </p>
                        </form>
                    </div>

                    <div className="flex gap-1">
                        <a href="https://instagram.com" target="_blank" rel="noopener noreferrer" aria-label="Instagram" className={iconLinkClass}>
                            <Globe size={20} />
                        </a>
                        <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" aria-label="Twitter" className={iconLinkClass}>
                            <MessageCircle size={20} />
                        </a>
                        <a href="https://facebook.com" target="_blank" rel="noopener noreferrer" aria-label="Facebook" className={iconLinkClass}>
                            <Share2 size={20} />
                        </a>
                    </div>
                </div>

                <div className="mt-10 flex flex-col gap-4 border-t pt-6 md:flex-row md:items-center md:justify-between">
                    <span className="text-sm text-muted-foreground">&copy; {new Date().getFullYear()} TravelBuddy</span>
                    <nav aria-label="Footer" className="flex flex-wrap gap-x-6">
                        <Link to="/about" className={linkClass}>About</Link>
                        <Link to="/contact" className={linkClass}>Contact</Link>
                        <Link to="/privacy" className={linkClass}>Privacy Policy</Link>
                        <Link to="/terms" className={linkClass}>Terms of Service</Link>
                    </nav>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
