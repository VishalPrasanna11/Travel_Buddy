import { CircleUserRound } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { useAuth0 } from "@auth0/auth0-react";
import { Link } from "react-router-dom";
import { Separator } from "./ui/separator";
import { Button } from "./ui/button";

const UsernameMenu = () => {
  const { user, logout } = useAuth0();

return (
    <DropdownMenu>
        <DropdownMenuTrigger
        className="flex items-center px-3 font-boldgap-2"
        style={{color:"#0A0A0A"}}
        onMouseOver={(e) => e.currentTarget.style.color = '#FFBD58'}
        onMouseOut={(e) => e.currentTarget.style.color = '#0A0A0A'}
        >
            <CircleUserRound className="text-black-500" />
            {user?.name || user?.email}
        </DropdownMenuTrigger>
        <DropdownMenuContent>
            <DropdownMenuItem>
                {/* <Link
                    to="/manage-restaurant"
                    className="font-bold"
                    onMouseOver={(e) => e.currentTarget.style.color = '#FFBD58'}
                    onMouseOut={(e) => e.currentTarget.style.color = '#0A0A0A'}
                >
                    Manage Restaurant
                </Link> */}
            </DropdownMenuItem>
            <DropdownMenuItem>
                <Link to="/profile" 
                className="font-bold"
                onMouseOver={(e) => e.currentTarget.style.color = '#FFBD58'}
                onMouseOut={(e) => e.currentTarget.style.color = '#0A0A0A'}
                >
                    User Profile
                </Link>
            </DropdownMenuItem>
            <DropdownMenuItem>
                <Link to="/restaurant" 
                className="font-bold"
                onMouseOver={(e) => e.currentTarget.style.color = '#FFBD58'}
                onMouseOut={(e) => e.currentTarget.style.color = '#0A0A0A'}
                >
                   My Restaurant
                </Link>
            </DropdownMenuItem>
            <Separator />
            <DropdownMenuItem>
                <Button
                    onClick={() => logout()}
                    className="flex flex-1 font-bold bg-black text-white"
                    onMouseOver={(e) => {
                        e.currentTarget.style.backgroundColor = 'white';
                        e.currentTarget.style.color = '#0A0A0A';
                    }}
                    onMouseOut={(e) => {
                        e.currentTarget.style.backgroundColor = '#0A0A0A';
                        e.currentTarget.style.color = 'white';
                    }}
                    style={{backgroundColor: '#0A0A0A'}}
                >
                    Log Out
                </Button>
            </DropdownMenuItem>
        </DropdownMenuContent>
    </DropdownMenu>
);
};

export default UsernameMenu;