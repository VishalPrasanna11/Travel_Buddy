import { AppSidebar } from "@/components/App-Sidebar";
import Footer from "@/components/Footer";
import Hero from "@/components/Hero";
import { SidebarProvider, SidebarTrigger, Sidebar } from "@/components/ui/sidebar";
import { Menu } from "lucide-react";

import Header from "@/components/Header";
type Props = {
    children: React.ReactNode;
    showHero?: boolean;
    showFooter?: boolean;
};

const Layout = ({ children, showHero = false, showFooter = false }: Props) => {
    return (
        <div className="flex h-screen">
            <SidebarProvider>
                {/* This is where we implement the actual shadcn Sidebar component */}
                <Sidebar className="border-r h-screen">
                    <div className="w-[240px]">
                        <AppSidebar />
                    </div>
                </Sidebar>
                
                {/* Main Content Area */}
                <div className="flex-1 flex flex-col h-screen overflow-hidden">
                    {/* Header with trigger button */}
                    <Header/>
                    
                    {/* Content Area */}
                    <div className="flex-1 overflow-auto">
                        {showHero && <Hero />}
                        <div className="container mx-auto py-6">
                            {children}
                        </div>
                        {showFooter && <Footer />}
                    </div>
                </div>
            </SidebarProvider>
        </div>
    );
}

export default Layout;