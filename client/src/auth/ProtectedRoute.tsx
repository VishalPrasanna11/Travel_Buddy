import { useEffect, useRef } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Outlet, useLocation } from "react-router-dom";
import { FullPageLoader } from "@/components/system/FullPageLoader";

/**
 * Signed-in routes. While Auth0 checks the session we show a calm loader.
 * If there is no session (first visit, logged out, expired), we send the user
 * to sign in and bring them back to the exact page they asked for.
 */
const ProtectedRoute = () => {
    const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();
    const location = useLocation();
    const redirecting = useRef(false);

    useEffect(() => {
        if (isLoading || isAuthenticated || redirecting.current) return;
        redirecting.current = true;
        void loginWithRedirect({
            appState: { returnTo: location.pathname + location.search },
        });
    }, [isLoading, isAuthenticated, loginWithRedirect, location.pathname, location.search]);

    if (isAuthenticated) return <Outlet />;

    return <FullPageLoader label={isLoading ? "Checking your session…" : "Signing you in…"} />;
};

export default ProtectedRoute;
