import { Link, useNavigate } from "react-router-dom";
import { LogIn, Plus } from "lucide-react";
import { useAuth0 } from "@auth0/auth0-react";
import { v4 as uuidv4 } from "uuid";

import { UsernameMenu } from "./UsernameMenu";
import MenuItem from "./MenuItem";
import { TripHistory } from "./TripHistory";
import { Button } from "./ui/button";
import { useSidebar } from "./ui/sidebar";

export function AppSidebar() {
    const { isAuthenticated, loginWithRedirect, user } = useAuth0();
    const navigate = useNavigate();
    const { isMobile, setOpenMobile } = useSidebar();

    const newTrip = () => {
        if (isMobile) setOpenMobile(false);
        navigate(`/chat/${uuidv4()}`, { viewTransition: true });
    };

    return (
        <div className="flex h-full min-h-0 flex-col">
            <div className="flex h-header shrink-0 items-center border-b px-4">
                <Link to="/home" viewTransition className="inline-flex min-h-11 items-center font-display text-lg font-semibold tracking-tight rounded-md">
                    TravelBuddy
                </Link>
            </div>

            <div className="px-3 pt-3">
                <Button className="w-full" onClick={newTrip}>
                    <Plus aria-hidden="true" />
                    New trip
                </Button>
            </div>

            <TripHistory />

            <div className="border-t">
                <MenuItem />
            </div>

            <div className="border-t p-2">
                {isAuthenticated && user ? (
                    <UsernameMenu user={{
                        name: user.name || user.nickname || "Traveler",
                        email: user.email || ""
                    }}/>
                ) : (
                    <Button variant="outline" className="w-full" onClick={() => loginWithRedirect()}>
                        <LogIn aria-hidden="true" />
                        Log in
                    </Button>
                )}
            </div>
        </div>
    );
}
