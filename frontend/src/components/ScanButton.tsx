import { useState } from "react";
import { useScanMutation } from "../api/queries";

export function ScanButton() {
  const scan = useScanMutation();
  const [showResult, setShowResult] = useState(false);
  const [subnet, setSubnet] = useState("");

  return (
    <div className="scan-button">
      <input
        className="input scan-button__subnet"
        placeholder="Subnet (optional, e.g. 192.168.1.0/24)"
        value={subnet}
        onChange={(e) => setSubnet(e.target.value)}
        title="Running inside Docker? The container can't autodetect your physical LAN — enter its CIDR here."
      />
      <button
        className="btn btn-primary"
        disabled={scan.isPending}
        onClick={() => {
          setShowResult(false);
          scan.mutate(subnet || undefined, { onSuccess: () => setShowResult(true) });
        }}
      >
        {scan.isPending ? "Scanning..." : "Run scan"}
      </button>
      {showResult && scan.data && (
        <div className="scan-result">
          {scan.data.devices_found} found · {scan.data.devices_probed} probed ·{" "}
          {scan.data.snmp_identified} identified via SNMP
          {scan.data.subnet ? ` · ${scan.data.subnet}` : ""}
          {scan.data.used_ping_sweep_fallback && (
            <>
              {" "}
              · <strong>ARP unavailable, used ICMP ping sweep</strong> — MAC/vendor not
              identified for these devices.
            </>
          )}
        </div>
      )}
      {scan.isError && <div className="scan-result scan-result--error">Scan failed.</div>}
    </div>
  );
}
