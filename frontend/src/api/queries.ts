import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

const DEVICES_REFETCH_MS = 30_000;

export function useDevices() {
  return useQuery({
    queryKey: ["devices"],
    queryFn: apiClient.listDevices,
    retry: 1,
    refetchInterval: (query) =>
      query.state.status === "success" ? DEVICES_REFETCH_MS : false,
  });
}

export function useDeviceHistory(id: number) {
  return useQuery({
    queryKey: ["devices", id, "history"],
    queryFn: () => apiClient.getDeviceHistory(id),
  });
}

export function useDeviceEvents(id: number) {
  return useQuery({
    queryKey: ["devices", id, "events"],
    queryFn: () => apiClient.getDeviceEvents(id),
  });
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: apiClient.getDashboardSummary,
    retry: 1,
    refetchInterval: (query) =>
      query.state.status === "success" ? DEVICES_REFETCH_MS : false,
  });
}

export function useDeviceAvailability(id: number) {
  return useQuery({
    queryKey: ["devices", id, "availability"],
    queryFn: () => apiClient.getDeviceAvailability(id),
  });
}

export function useScanMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (subnet?: string) => apiClient.scanDevices(subnet),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
    },
  });
}
