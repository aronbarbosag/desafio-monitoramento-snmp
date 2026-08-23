export type DeviceStatus = "unknown" | "online" | "offline";
export type MetricValueType = "integer" | "counter" | "gauge" | "string";

export interface DeviceOut {
  id: number;
  ip: string;
  mac: string;
  vendor: string | null;
  device_type: string | null;
  hostname: string | null;
  sys_descr: string | null;
  model_name: string | null;
  sys_contact: string | null;
  sys_location: string | null;
  snmp_supported: boolean;
  status: DeviceStatus;
  poll_interval_seconds: number;
  consecutive_failures: number;
  last_checked_at: string | null;
}

export interface MetricHistoryOut {
  id: number;
  collected_at: string;
  metric_key: string;
  metric_name: string;
  metric_unit: string | null;
  value_type: MetricValueType;
  value_numeric: number | null;
  value_text: string | null;
  display_value: string | null;
}

export interface AvailabilityEventOut {
  id: number;
  status: DeviceStatus;
  started_at: string;
  ended_at: string | null;
}

export interface ScanResult {
  subnet: string | null;
  devices_found: number;
  devices_probed: number;
  snmp_identified: number;
}
