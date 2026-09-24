import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Create from "./pages/Create";
import Models from "./pages/Models";
import PublishPage from "./pages/Publish";
import SettingsPage from "./pages/Settings";
import Onboarding from "./pages/Onboarding";

import { ONBOARD_KEY } from "./constants";

function RequireOnboard({ children }: { children: React.ReactNode }) {
  const done = localStorage.getItem(ONBOARD_KEY) === "1";
  if (!done) return <Navigate to="/onboarding" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route
        element={
          <RequireOnboard>
            <Layout />
          </RequireOnboard>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/create" element={<Create />} />
        <Route path="/models" element={<Models />} />
        <Route path="/publish" element={<PublishPage />} />
        <Route path="/youtube" element={<Navigate to="/publish" replace />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
