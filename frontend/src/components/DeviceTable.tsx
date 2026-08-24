import { formatApiDate } from "../api/dates";
import type { DeviceOut } from "../api/types";
import { StatusBadge } from "./StatusBadge";

interface DeviceTableProps {
  devices: DeviceOut[];
  onSelect: (id: number) => void;
}

export function DeviceTable({ devices, onSelect }: DeviceTableProps) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Device</th>
          <th>Type</th>
          <th>Vendor / model</th>
          <th>IP</th>
          <th>Status</th>
          <th>SNMP</th>
          <th>Last checked</th>
        </tr>
      </thead>
      <tbody>
        {devices.length === 0 && (
          <tr>
            <td colSpan={7} className="table__empty">
              No devices match the current filters.
            </td>
          </tr>
        )}
        {devices.map((d) => (
          <tr key={d.id} onClick={() => onSelect(d.id)} style={{ cursor: "pointer" }}>
            <td>{d.hostname ?? d.ip}</td>
            <td>{d.device_type ?? "—"}</td>
            <td>{[d.vendor, d.model_name].filter(Boolean).join(" ") || "—"}</td>
            <td>{d.ip}</td>
            <td>
              <StatusBadge status={d.status} />
            </td>
            <td>{d.snmp_supported ? "Yes" : "No"}</td>
            <td>{d.last_checked_at ? formatApiDate(d.last_checked_at) : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
