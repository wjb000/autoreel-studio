import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/create", label: "Create" },
  { to: "/models", label: "Models" },
  { to: "/publish", label: "Publish" },
  { to: "/settings", label: "Settings" },
  { to: "/onboarding", label: "Onboarding" },
];

export default function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" />
          AutoReel Studio
        </div>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            {l.label}
          </NavLink>
        ))}
        <div className="spacer" />
        <div className="muted" style={{ padding: "0.75rem", fontSize: "0.75rem" }}>
          Wan 2.1 · shorts + multi-platform
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
