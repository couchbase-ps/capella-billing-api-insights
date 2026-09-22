import {
  BarChart3,
  FileText,
  LayoutDashboard,
  Server,
  Smartphone,
  TableProperties,
} from "lucide-react";
import type { JSX } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useHealth, useOrganization } from "../api/hooks";
import capellaLogo from "../assets/capella-logo.svg";
import { SetupBanner } from "./SetupBanner";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/clusters", label: "Clusters", icon: Server, end: false },
  { to: "/appservices", label: "App Services", icon: Smartphone, end: false },
  { to: "/analytics", label: "Analytics", icon: BarChart3, end: false },
  { to: "/insights", label: "Insights", icon: TableProperties, end: false },
  { to: "/reports", label: "Reports", icon: FileText, end: false },
];

export function Layout(): JSX.Element {
  const org = useOrganization();
  const health = useHealth();
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-surface">
        <div className="border-b border-border px-4 py-4">
          <div className="flex flex-col gap-1">
            <img src={capellaLogo} alt="Capella" className="h-6 w-auto self-start" />
            <span className="text-label-upper uppercase text-text-muted">Billing insights</span>
          </div>
          <p
            className="mt-2 truncate text-heading-sm text-on-surface-strong"
            title={org.data?.name}
          >
            {org.data?.name ?? (org.isError ? "Organization unavailable" : "Loading…")}
          </p>
          {org.data && (
            <p className="text-caption text-text-muted">
              {org.data.billingMode} · {org.data.billingCurrency}
              {health.data?.mock ? " · mock" : ""}
            </p>
          )}
        </div>
        <nav className="flex flex-col gap-0.5 p-2" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-sm px-2 py-1.5 text-label-md ${
                  isActive
                    ? "bg-surface-accent text-on-surface-strong"
                    : "text-on-surface hover:bg-surface-alt"
                }`
              }
            >
              <Icon size={16} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-7xl px-6 py-5">
          {health.data && !health.data.configured && <SetupBanner mock={health.data.mock} />}
          <Outlet />
        </div>
      </main>
    </div>
  );
}
