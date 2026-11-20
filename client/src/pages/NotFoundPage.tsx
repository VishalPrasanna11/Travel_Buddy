import { Link, useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { v4 as uuidv4 } from "uuid";
import { MapPinOff } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { Button, buttonVariants } from "@/components/ui/button";

const NotFoundPage = () => {
  const { isAuthenticated } = useAuth0();
  const navigate = useNavigate();
  const canGoBack = typeof window !== "undefined" && window.history.length > 1;

  return (
    <div className="flex flex-1 items-center justify-center py-16">
      <EmptyState
        icon={MapPinOff}
        headingLevel="h1"
        title="We couldn't find that page"
        description="The link may be old or mistyped. You can head home or start planning a new trip."
        actions={
          <>
            {isAuthenticated ? (
              <Link to={`/chat/${uuidv4()}`} viewTransition className={buttonVariants()}>
                Start a trip
              </Link>
            ) : (
              <Link to="/" viewTransition className={buttonVariants()}>
                Go to home
              </Link>
            )}
            {canGoBack ? (
              <Button variant="outline" onClick={() => navigate(-1)}>Go back</Button>
            ) : (
              isAuthenticated && (
                <Link to="/home" viewTransition className={buttonVariants({ variant: "outline" })}>Go to home</Link>
              )
            )}
          </>
        }
      />
    </div>
  );
};

export default NotFoundPage;
