import { NavLink } from "react-router-dom";
import { Bell, BookmarkIcon, Lightbulb, Plane, Plus, Search, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSidebar } from "@/components/ui/sidebar";

/**
 * Sidebar navigation. Flights, Saved and Settings are working pages. The other
 * destinations are not built yet; they lead to the waitlist and say so
 * ("Soon") instead of pretending to be pages.
 */
const LINKS = [
  { to: "/flights", label: "Flight search", icon: Plane, iconClass: "text-flight-ink" },
  { to: "/saved", label: "Saved", icon: BookmarkIcon, iconClass: "text-raspberry" },
  { to: "/settings", label: "Settings", icon: Settings, iconClass: "text-muted-foreground" },
];

const SOON = [
  { label: "Explore", icon: Search },
  { label: "Updates", icon: Bell },
  { label: "Inspiration", icon: Lightbulb },
  { label: "Create", icon: Plus },
];

const rowClass =
  "flex min-h-10 items-center gap-3 rounded-md px-2.5 text-sm text-ink transition-colors duration-150 hover:bg-muted pointer-coarse:min-h-11";

const MenuItem = () => {
  const { isMobile, setOpenMobile } = useSidebar();
  const close = () => isMobile && setOpenMobile(false);

  return (
    <nav aria-label="Main" className="px-2 py-2">
      <ul className="space-y-0.5">
        {LINKS.map(({ to, label, icon: Icon, iconClass }) => (
          <li key={to}>
            <NavLink
              to={to}
              viewTransition
              onClick={close}
              className={({ isActive }) => cn(rowClass, isActive && "bg-raspberry-tint font-semibold")}
            >
              <Icon className={`size-4 ${iconClass}`} aria-hidden="true" />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>

      <details className="group/soon mt-2">
        <summary className="flex min-h-9 cursor-pointer list-none items-center justify-between rounded-md px-2.5 text-meta font-semibold text-muted-foreground hover:bg-muted pointer-coarse:min-h-11 [&::-webkit-details-marker]:hidden">
          Coming soon
          <span className="text-meta font-normal group-open/soon:hidden">Show</span>
          <span className="hidden text-meta font-normal group-open/soon:inline">Hide</span>
        </summary>
        <ul className="mt-0.5 space-y-0.5">
          {SOON.map(({ label, icon: Icon }) => (
            <li key={label}>
              <NavLink to="/waitlist" onClick={close} className={rowClass}>
                <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
                <span className="flex-1">{label}</span>
                <span className="rounded-full bg-muted px-2 py-0.5 text-meta text-muted-foreground">Soon</span>
                <span className="sr-only">: join the waitlist</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </details>
    </nav>
  );
};

export default MenuItem;
