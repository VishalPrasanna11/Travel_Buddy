import { AppSidebar } from "@/components/App-Sidebar";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import { SidebarProvider, Sidebar, SidebarInset } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

type Props = {
    children: React.ReactNode;
    showFooter?: boolean;
    showSidebar?: boolean;
    /**
     * "page": normal document that scrolls (landing, home).
     * "app": fixed viewport-height workspace whose panes scroll on their own (chat).
     */
    variant?: "page" | "app";
};

const Layout = ({ children, showFooter = false, showSidebar = true, variant = "page" }: Props) => {
    const isApp = variant === "app";

    return (
        <SidebarProvider className={cn(isApp && "h-dvh min-h-0 overflow-hidden")}>
            {/* First tab stop on every page, ahead of the sidebar. */}
            <a
                href="#main"
                className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:shadow-overlay"
            >
                Skip to content
            </a>
            {showSidebar && (
                <Sidebar>
                    <AppSidebar />
                </Sidebar>
            )}

            <SidebarInset className={cn("min-w-0", isApp && "h-dvh min-h-0 overflow-hidden")}>
                <Header showSidebar={showSidebar} />

                <main id="main" tabIndex={-1} className={cn("flex flex-1 flex-col outline-none", isApp && "min-h-0")}>
                    {children}
                </main>

                {showFooter && <Footer />}
            </SidebarInset>
        </SidebarProvider>
    );
};

export default Layout;
