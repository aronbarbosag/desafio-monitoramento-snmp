import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, useNavigate } from "react-router-dom";
import { InventoryPage } from "./pages/InventoryPage";
import { DeviceDetailPage } from "./pages/DeviceDetailPage";

const queryClient = new QueryClient();

function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="page">
      <p>Página não encontrada.</p>
      <button className="btn btn-secondary" onClick={() => navigate("/")}>
        ← Inventário
      </button>
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<InventoryPage />} />
          <Route path="/devices/:id" element={<DeviceDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
