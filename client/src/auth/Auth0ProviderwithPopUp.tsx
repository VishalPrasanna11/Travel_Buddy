import { AppState, Auth0Provider} from '@auth0/auth0-react';
import React from 'react';
import { useNavigate } from 'react-router-dom';
type Props = {
    children: React.ReactNode;
}; 

const Auth0ProviderWithPopup = ({ children }: Props) => {


const navigate = useNavigate();

const domain = import.meta.env.VITE_AUTH0_DOMAIN;
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID;
// Return to the site the user signed in from (travelbuddy.live, www, or the
// Heroku URL); each origin must be in Auth0's Allowed Callback URLs.
const redirectUri = window.location.origin;
const audience = import.meta.env.VITE_AUTH0_AUDIENCE;
if (!domain || !clientId || !audience) {
    throw new Error(
        "Please define the VITE_AUTH0_DOMAIN, VITE_AUTH0_CLIENT_ID and VITE_AUTH0_AUDIENCE environment variables"
    );
}
         

        const onRedirectCallback = (appState?:AppState) => {
            navigate(appState?.returnTo||"/home");
         
        }


        return (
            <Auth0Provider
                domain={domain}
                clientId={clientId}
                
                authorizationParams={{
                    redirect_uri: redirectUri,
                    audience,
                }}
                
                onRedirectCallback={onRedirectCallback}
                
                
            >
                {children}
            </Auth0Provider>
        );
    };

export default Auth0ProviderWithPopup;