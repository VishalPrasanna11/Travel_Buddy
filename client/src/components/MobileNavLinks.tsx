import { Link } from "react-router-dom";
import { Button } from "./ui/button";
import { useAuth0 } from "@auth0/auth0-react";

const   MobileNavLinks = () => {
    const { logout } = useAuth0();
    return (
        <>
        <Link to="/profile" 
                className="font-bold flex bg-white items-center text-align-center text-black gap-2"
                onMouseOver={(e) => e.currentTarget.style.color = '#FFBD58'}
                onMouseOut={(e) => e.currentTarget.style.color = '#0A0A0A'}

        >
                    User Profile
        </Link>
        <Link to="/restaurant" 
                className="font-bold flex bg-white items-center text-align-center text-black gap-2"
                onMouseOver={(e) => e.currentTarget.style.color = '#FFBD58'}
                onMouseOut={(e) => e.currentTarget.style.color = '#0A0A0A'}

        >
                    My Restaurant
        </Link>
        <Button
                    onClick={() => logout()}
                    className="flex items-center px-3 font-bold bg-black text-white"
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

        </>
    );
    }   
export default MobileNavLinks;