import { useAuth0 } from "@auth0/auth0-react";
import { Button } from "./ui/button";

const MainNav = () => {
  const { loginWithRedirect, isAuthenticated } = useAuth0();

  return (
    <span className="flex space-x-2 items-center">
    {isAuthenticated ? (
        <>
       
        </>
    ) : (
        <Button
            variant="ghost"
            className="text-lg font-bold hover:text-orange-500 hover:bg-white transition-colors duration-200 px-6 py-2"
            onClick={async () => await loginWithRedirect()}
        >
            Log In
        </Button>
    )}
    </span>
  );
};

export default MainNav;