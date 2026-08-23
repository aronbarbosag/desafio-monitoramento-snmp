import { useState } from "react";
import { useScanMutation } from "../api/queries";

export function ScanButton() {
  const scan = useScanMutation();
  const [showResult, setShowResult] = useState(false);

  return (
    <div className="scan-button">
      <button
        className="btn btn-primary"
        disabled={scan.isPending}
        onClick={() => {
          setShowResult(false);
          scan.mutate(undefined, { onSuccess: () => setShowResult(true) });
        }}
      >
        {scan.isPending ? "Executando scan..." : "Executar scan"}
      </button>
      {showResult && scan.data && (
        <div className="scan-result">
          {scan.data.devices_found} encontrados · {scan.data.devices_probed} sondados ·{" "}
          {scan.data.snmp_identified} identificados via SNMP
          {scan.data.subnet ? ` · ${scan.data.subnet}` : ""}
        </div>
      )}
      {scan.isError && <div className="scan-result scan-result--error">Falha ao executar scan.</div>}
    </div>
  );
}
