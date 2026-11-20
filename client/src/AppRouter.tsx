import { lazy, Suspense, type ReactNode } from "react";
import { Route, Routes, Navigate, useParams } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";
import Layout from "./layouts/layout";
import ProtectedRoute from "./auth/ProtectedRoute";
import LandingPage from "./pages/LandingPage";
import { RouteLoader } from "./components/system/FullPageLoader";
import { PreferencesSync } from "./api/AccountApi";

// Everything except the landing page is split out, so first-time visitors
// don't download chat, Shiki, maps or flight search up front.
const HomePage = lazy(() => import("./pages/HomePage"));
const AuthCallbackPage = lazy(() => import("./pages/AuthCallbackPage"));
const ChatMainPage = lazy(() => import("./pages/ChatMainPage"));
const ChatMapsPage = lazy(() => import("./pages/ChatMapsRoute"));
const FlightSearchPage = lazy(() => import("./pages/FlightSearchPage"));
const WaitlistPage = lazy(() => import("./pages/WaitlistPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const SavedPage = lazy(() => import("./pages/SavedPage"));
const SharedTripPage = lazy(() => import("./pages/SharedTripPage"));

const Page = ({ children, label }: { children: ReactNode; label?: string }) => (
  <Suspense fallback={<RouteLoader label={label} />}>{children}</Suspense>
);

/** /chat with no id starts a fresh conversation. */
const NewChatRedirect = () => <Navigate to={`/chat/${uuidv4()}`} replace />;

/** Legacy /chatmain/:id links keep working. */
const LegacyChatRedirect = () => {
  const { id } = useParams();
  return <Navigate to={id ? `/chat/${id}` : "/chat"} replace />;
};

const AppRouter = () => {
  return (
    <>
    <PreferencesSync />
    <Routes>
      {/* Public */}
      <Route
        path="/"
        element={
          <Layout showFooter showSidebar={false}>
            <LandingPage />
          </Layout>
        }
      />

      <Route
        path="/auth-callback"
        element={
          <Page>
            <AuthCallbackPage />
          </Page>
        }
      />

      <Route
        path="/waitlist"
        element={
          <Layout showSidebar={false}>
            <Page>
              <WaitlistPage />
            </Page>
          </Layout>
        }
      />

      {/* Public, read-only shared itinerary */}
      <Route
        path="/share/:token"
        element={
          <Layout showSidebar={false} showFooter>
            <Page label="Opening the shared trip…">
              <SharedTripPage />
            </Page>
          </Layout>
        }
      />

      {/* Dev only (tree-shaken from production builds): the chat without the
          Auth0 gate, for running against a local fixture server. */}
      {import.meta.env.DEV && (
        <Route path="/dev/settings" element={<Layout showSidebar><Page><SettingsPage /></Page></Layout>} />
      )}
      {import.meta.env.DEV && (
        <Route path="/dev/saved" element={<Layout showSidebar><Page><SavedPage /></Page></Layout>} />
      )}
      {import.meta.env.DEV && (
        <Route
          path="/dev/chat/:id"
          element={
            <Layout variant="app" showSidebar>
              <Page label="Opening your trip…">
                <ChatMainPage />
              </Page>
            </Layout>
          }
        />
      )}

      {/* Signed in */}
      <Route element={<ProtectedRoute />}>
        <Route path="/chat" element={<NewChatRedirect />} />
        <Route
          path="/chat/:id"
          element={
            <Layout variant="app" showSidebar>
              <Page label="Opening your trip…">
                <ChatMainPage />
              </Page>
            </Layout>
          }
        />
        <Route path="/chatmain/:id" element={<LegacyChatRedirect />} />

        <Route
          path="/home"
          element={
            <Layout showFooter>
              <Page>
                <HomePage />
              </Page>
            </Layout>
          }
        />

        <Route
          path="/chatmaps"
          element={
            <Layout variant="app" showSidebar>
              <Page>
                <ChatMapsPage />
              </Page>
            </Layout>
          }
        />

        <Route
          path="/saved"
          element={
            <Layout showSidebar>
              <Page label="Loading your saved places…">
                <SavedPage />
              </Page>
            </Layout>
          }
        />
        <Route
          path="/settings"
          element={
            <Layout showSidebar>
              <Page label="Loading settings…">
                <SettingsPage />
              </Page>
            </Layout>
          }
        />

        <Route
          path="/flights"
          element={
            <Layout showSidebar>
              <Page label="Loading flight search…">
                <FlightSearchPage />
              </Page>
            </Layout>
          }
        />
      </Route>

      {/* Not found */}
      <Route
        path="*"
        element={
          <Layout showSidebar={false}>
            <Page>
              <NotFoundPage />
            </Page>
          </Layout>
        }
      />
    </Routes>
    </>
  );
};

export default AppRouter;
