import { AlertTriangle } from "lucide-react";
import type { JSX } from "react";

export function SetupBanner({ mock }: { mock: boolean }): JSX.Element {
  return (
    <div
      role="status"
      className="mb-4 flex items-start gap-3 rounded-md border border-warning bg-surface-accent px-4 py-3 text-body-sm"
    >
      <AlertTriangle size={18} className="mt-0.5 shrink-0 text-warning-text" aria-hidden="true" />
      <div>
        <p className="text-label-md text-warning-text">Backend not configured</p>
        <p className="text-on-surface">
          Set <code className="font-mono">CAPELLA_API_KEY</code> in{" "}
          <code className="font-mono">.env</code> (or{" "}
          <code className="font-mono">CAPELLA_MOCK=true</code> for the fixture demo) and restart{" "}
          <code className="font-mono">docker compose</code>. Sync is disabled until then.
          {mock ? " Mock mode is on." : ""}
        </p>
      </div>
    </div>
  );
}
