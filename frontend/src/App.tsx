import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { InventoryPage } from "./pages/InventoryPage";
import { DeviceDetailPage } from "./pages/DeviceDetailPage";

const queryClient = new QueryClient();

function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="page">
      <p>Page not found.</p>
      <button className="btn btn-secondary" onClick={() => navigate("/")}>
        ← Inventory
      </button>
    </div>
  );
}

function RoutedContent() {
  // Key by pathname so navigating away from a crashed page clears the
  // boundary instead of stranding the user until a manual reload.
  const location = useLocation();
  return (
    <ErrorBoundary key={location.pathname}>
      <Routes>
        <Route path="/" element={<InventoryPage />} />
        <Route path="/devices/:id" element={<DeviceDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ErrorBoundary>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <RoutedContent />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
