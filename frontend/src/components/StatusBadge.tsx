import type { DeviceStatus } from "../api/types";

export const STATUS_LABEL: Record<DeviceStatus, string> = {
  online: "Online",
  offline: "Offline",
  unknown: "Unknown",
};

export function StatusBadge({ status }: { status: DeviceStatus }) {
  return <span className={`status-badge status-badge--${status}`}>{STATUS_LABEL[status]}</span>;
}
