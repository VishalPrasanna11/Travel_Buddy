import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { LogIn } from "lucide-react";
import { useCreateMyUser } from "@/api/UserApi";
import { FullPageLoader } from "@/components/system/FullPageLoader";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";

const AuthCallbackPage = () => {
    const { user, isLoading, error, loginWithRedirect } = useAuth0();
    const { createUser } = useCreateMyUser();
    const navigate = useNavigate();
    const handled = useRef(false);

    useEffect(() => {
        if (isLoading || error || handled.current) return;
        handled.current = true;

        const finish = async () => {
            if (user?.sub && user.email) {
                try {
                    await createUser({ auth0id: user.sub, email: user.email });
                } catch (err) {
                    // Account record creation is best-effort; don't block sign-in.
                    console.error("Couldn't create user record:", err);
                }
            }
            navigate("/home", { replace: true, viewTransition: true });
        };
        void finish();
    }, [isLoading, error, user, createUser, navigate]);

    if (error) {
        return (
            <main id="main" className="flex min-h-dvh items-center justify-center">
                <EmptyState
                    icon={LogIn}
                    headingLevel="h1"
                    title="We couldn't sign you in"
                    description={
                        <>
                            <p>{error.message || "The sign-in service returned an error."}</p>
                            <p className="mt-1">Try again. If it keeps happening, close this tab and sign in from the home page.</p>
                        </>
                    }
                    actions={
                        <>
                            <Button onClick={() => loginWithRedirect()}>Try again</Button>
                            <Button variant="outline" onClick={() => navigate("/", { replace: true })}>Back to home</Button>
                        </>
                    }
                />
            </main>
        );
    }

    return <FullPageLoader label="Signing you in…" />;
};

export default AuthCallbackPage;
