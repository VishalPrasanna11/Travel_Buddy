import { Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { SidebarTrigger, useSidebar } from "./ui/sidebar";
import MainNav from "./MainNav";
import { cn } from "@/lib/utils";

type MainHeaderProps = {
    children?: React.ReactNode;
    showSidebar?: boolean;
};

/** Logo is only rendered when there is no sidebar showing its own. */
function HeaderLogo({ hidden }: { hidden: boolean }) {
    const { isAuthenticated } = useAuth0();
    return (
        <Link
            to={isAuthenticated ? "/home" : "/"}
            className={cn(
                "font-display text-lg font-semibold tracking-tight text-foreground rounded-md",
                hidden && "md:hidden"
            )}
        >
            TravelBuddy
        </Link>
    );
}

function SidebarHeaderControls() {
    const { open, isMobile } = useSidebar();
    return (
        <>
            <SidebarTrigger
                className="size-10 pointer-coarse:size-11 text-muted-foreground hover:text-foreground"
                aria-label={isMobile ? "Open menu" : open ? "Hide sidebar" : "Show sidebar"}
            />
            <HeaderLogo hidden={open && !isMobile} />
        </>
    );
}

const Header = ({ children, showSidebar = true }: MainHeaderProps) => {
    return (
        <header className="sticky top-0 z-20 flex h-header shrink-0 items-center border-b bg-background/95 px-gutter backdrop-blur-sm supports-[backdrop-filter]:bg-background/85 md:px-gutter-lg pt-[env(safe-area-inset-top)]">
            <div className="flex w-full items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                    {showSidebar ? <SidebarHeaderControls /> : <HeaderLogo hidden={false} />}
                </div>
                <MainNav />
            </div>
            {children}
        </header>
    );
};

export default Header;
