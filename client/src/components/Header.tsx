import { Link } from "react-router-dom";
import { Menu } from "lucide-react";
import { SidebarTrigger } from "./ui/sidebar";
import MainNav from "./MainNav";
import React, { useEffect } from "react";

type MainHeaderProps = {
    children?: React.ReactNode;
};

const Header = ({ children }: MainHeaderProps) => {
    // Reference to the sidebar trigger button
    const sidebarTriggerRef = React.useRef<HTMLButtonElement>(null);
    
    // Effect to auto-open the sidebar on component mount
    useEffect(() => {
        // Trigger the sidebar to open by default
        if (sidebarTriggerRef.current) {
            sidebarTriggerRef.current.click();
        }
    }, []);

    return (
        <header className="h-16 border-b flex items-center px-4 bg-white sticky top-0 z-10">
            <div className="container mx-auto flex justify-between items-center">
                <div className="flex items-center">
                    <SidebarTrigger 
                        ref={sidebarTriggerRef}
                        className="flex items-center justify-center w-10 h-10 rounded-md hover:bg-gray-100 mr-4"
                    >
                        <Menu className="h-5 w-5" />
                    </SidebarTrigger>
                    <Link to="/" className="font-medium text-xl">TravelBuddy</Link>
                </div>
                
                
                <div >
                    <MainNav />
                </div>
            </div>
            
            {children}
        </header>
    );
};

export default Header;