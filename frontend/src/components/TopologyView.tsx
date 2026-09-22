import type { JSX } from "react";
import { useEffect, useRef } from "react";
import type { TopologyDocument } from "../api/types";
import "@couchbaselabs/topology-ui/styles.css";
// Side-effect import: the browser bundle registers window.couchbaseTopologyUi. We read the
// global instead of the package's "." entry, whose top-level await + dynamic import of the
// CommonJS fallback is awkward for Vite pre-bundling.
import "@couchbaselabs/topology-ui/browser";

interface TopologyRenderer {
  create_cluster: (
    container: HTMLElement,
    data: TopologyDocument,
    options?: { assetRoot?: string },
  ) => HTMLElement;
  render_cluster_html: (data: TopologyDocument, options?: { assetRoot?: string }) => string;
}

declare global {
  interface Window {
    couchbaseTopologyUi?: TopologyRenderer;
  }
}

export const TOPOLOGY_ASSET_ROOT = "/topology-ui/images";

export function TopologyView({ document }: { document: TopologyDocument }): JSX.Element {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = ref.current;
    const renderer = window.couchbaseTopologyUi;
    if (!container || !renderer) {
      return;
    }
    renderer.create_cluster(container, document, { assetRoot: TOPOLOGY_ASSET_ROOT });
    return () => {
      container.innerHTML = "";
    };
  }, [document]);

  return (
    <div className="overflow-x-auto rounded-md border border-border bg-surface p-2">
      <div ref={ref} data-testid="topology-view" />
    </div>
  );
}
