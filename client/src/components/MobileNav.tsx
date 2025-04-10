import { CircleUserRound, Menu } from "lucide-react"
import { Sheet,SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "./ui/sheet"
import { Separator } from "@radix-ui/react-separator"
import { Button } from "./ui/button"
import { useAuth0 } from "@auth0/auth0-react"
import MobileNavLinks from "./MobileNavLinks.tsx"

 
const MobileNav = () => {
    const { loginWithRedirect, isAuthenticated ,user} = useAuth0();
    return (
        <Sheet>
            <SheetTrigger>
                <Menu className="text-#0A0A0A" />
            </SheetTrigger>

            <SheetContent className="space-y-3">
                <SheetTitle>
                    {isAuthenticated ? <span className="flex items-center font-bold gap-2">
                        <CircleUserRound className="text-black-500" />
                        {user?.name || user?.email}
                        </span>:
                     (<span>Welcome to TravelBuddy</span>)}

                  
                </SheetTitle>

                <Separator />

                <SheetDescription className="flex flex-col gap-4">
                    {isAuthenticated ? <MobileNavLinks/>:
                <Button 
                    style={{ 
                        backgroundColor: '#0A0A0A', 
                        color: '#fff' 
                    }} 
                    className="flex-1 font-bold"
                    onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#FFBD58'}
                    onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#0A0A0A'}
                    onClick={async () => await loginWithRedirect()}
                >
                        Log In
                </Button>}
                </SheetDescription>
            </SheetContent>

        </Sheet>
    );}
    export default MobileNav;