import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { InventoryPage } from "./pages/InventoryPage";
import { DeviceDetailPage } from "./pages/DeviceDetailPage";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<InventoryPage />} />
          <Route path="/devices/:id" element={<DeviceDetailPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
