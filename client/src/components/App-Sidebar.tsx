import { Link } from "react-router-dom";
import { MessageSquare, Search, BookmarkIcon, Bell, Lightbulb, Plus, LogIn, Menu } from "lucide-react";
import { useAuth0 } from "@auth0/auth0-react";
import { UsernameMenu } from "./UsernameMenu";
import MenuItem from "./MenuItem";
import { buttonVariants } from "./ui/button";
import {v4 as uuidv4} from "uuid";


export function AppSidebar() {
    const { isAuthenticated, loginWithRedirect, user } = useAuth0();
    
    const generateUniqueId = () => {
        return uuidv4();
    };
    return (
        <div className="flex h-full min-h-0 flex-col">
            {/* Logo at top */}
            <div className="flex h-header shrink-0 items-center border-b px-4">
                <Link to="/home" className="font-display text-lg font-semibold tracking-tight rounded-md">
                    TravelBuddy
                </Link>
            </div>
            
            {/* Navigation items */}
            <MenuItem />
            
            {/* New chat button */}
            <div className="p-4">
                <Link
                    to={`/chat/${generateUniqueId()}`}
                    className={buttonVariants({ variant: "outline", className: "w-full" })}
                >
                    <Plus aria-hidden="true" />
                    New chat
                </Link>
</div>
            
            {/* User profile or login button at bottom - fixed position */}
            <div className="mt-auto p-4 border-t">
                {isAuthenticated && user ? (
                    <UsernameMenu user={{
                        name: user.name || user.nickname || 'User',
                        email: user.email || 'No email provided'
                    }}/>
                ) : (
                    <button 
                        onClick={() => loginWithRedirect()}
                        className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-md hover:bg-raspberry-hover flex items-center justify-center"
                    >
                        <LogIn className="mr-2 h-4 w-4" />
                        Log In
                    </button>
                )}
            </div>
            
       
        </div>
    );
}