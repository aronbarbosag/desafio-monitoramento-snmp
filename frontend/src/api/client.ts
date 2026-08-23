import type { AvailabilityEventOut, DeviceOut, MetricHistoryOut, ScanResult } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const DEFAULT_LIST_LIMIT = 100;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new ApiError(res.status, detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const apiClient = {
  listDevices: () => request<DeviceOut[]>("/devices"),
  getDevice: (id: number) => request<DeviceOut>(`/devices/${id}`),
  getDeviceHistory: (id: number, limit = DEFAULT_LIST_LIMIT) =>
    request<MetricHistoryOut[]>(`/devices/${id}/history?limit=${limit}`),
  getDeviceEvents: (id: number, limit = DEFAULT_LIST_LIMIT) =>
    request<AvailabilityEventOut[]>(`/devices/${id}/events?limit=${limit}`),
  scanDevices: () => request<ScanResult>("/devices/scan", { method: "POST" }),
};
