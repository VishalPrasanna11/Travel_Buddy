import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

type Props = { children: ReactNode };
type State = { error: Error | null; showDetails: boolean };

/**
 * App-wide safety net: a render error shows a friendly page instead of a blank
 * screen. Details are only available in development.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, showDetails: false };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled UI error:", error, info.componentStack);
  }

  render() {
    const { error, showDetails } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="flex min-h-dvh items-center justify-center bg-background">
        <EmptyState
          icon={AlertTriangle}
          headingLevel="h1"
          title="Something broke on this page"
          description="It's not something you did. Reloading usually fixes it. Your saved trips are stored on this device and won't be lost."
          actions={
            <>
              <Button onClick={() => window.location.reload()}>Reload page</Button>
              <Button variant="outline" onClick={() => window.location.assign("/")}>Go to home</Button>
            </>
          }
        >
          {import.meta.env.DEV && (
            <div className="mt-6 w-full text-left">
              <Button
                variant="link"
                size="sm"
                aria-expanded={showDetails}
                onClick={() => this.setState({ showDetails: !showDetails })}
              >
                {showDetails ? "Hide details" : "Show details (dev only)"}
              </Button>
              {showDetails && (
                <pre className="mt-2 max-h-64 overflow-auto rounded-control border bg-muted p-3 font-mono text-xs whitespace-pre-wrap">
                  {error.stack || error.message}
                </pre>
              )}
            </div>
          )}
        </EmptyState>
      </div>
    );
  }
}
