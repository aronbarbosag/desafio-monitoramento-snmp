import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Unhandled error in UI:", error, errorInfo);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="page">
          <p className="banner banner--warning">
            Something went wrong while rendering this page.
            <button
              className="btn btn-secondary"
              style={{ marginLeft: "var(--space-4)" }}
              onClick={() => window.location.reload()}
            >
              Reload
            </button>
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
