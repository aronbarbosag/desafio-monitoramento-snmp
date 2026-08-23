import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

const DEVICES_REFETCH_MS = 30_000;

export function useDevices() {
  return useQuery({
    queryKey: ["devices"],
    queryFn: apiClient.listDevices,
    refetchInterval: DEVICES_REFETCH_MS,
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

export function useScanMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: apiClient.scanDevices,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
    },
  });
}
