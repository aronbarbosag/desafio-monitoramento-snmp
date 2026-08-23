import { parseApiDate } from "../api/dates";
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
          <th>Tipo</th>
          <th>Vendor / modelo</th>
          <th>IP</th>
          <th>Status</th>
          <th>SNMP</th>
          <th>Última checagem</th>
        </tr>
      </thead>
      <tbody>
        {devices.map((d) => (
          <tr key={d.id} onClick={() => onSelect(d.id)} style={{ cursor: "pointer" }}>
            <td>{d.hostname ?? d.ip}</td>
            <td>{d.device_type ?? "—"}</td>
            <td>{[d.vendor, d.model_name].filter(Boolean).join(" ") || "—"}</td>
            <td>{d.ip}</td>
            <td>
              <StatusBadge status={d.status} />
            </td>
            <td>{d.snmp_supported ? "Sim" : "Não"}</td>
            <td>{d.last_checked_at ? parseApiDate(d.last_checked_at).toLocaleString() : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
