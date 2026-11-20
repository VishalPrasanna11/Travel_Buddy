import { useAuth0 } from "@auth0/auth0-react";
import { Button } from "./ui/button";

/** Header actions. Signed-out visitors get a quiet Log in; the page owns the primary CTA. */
const MainNav = () => {
  const { loginWithRedirect, isAuthenticated } = useAuth0();

  if (isAuthenticated) return null;

  return (
    <Button variant="outline" className="h-11" onClick={() => loginWithRedirect()}>
      Log in
    </Button>
  );
};

export default MainNav;
