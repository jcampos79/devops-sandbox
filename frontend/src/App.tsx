import { Routes, Route } from "react-router-dom";
import TopBar from "./components/TopBar";
import RequireAuth from "./components/RequireAuth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import InstanceDetails from "./pages/InstanceDetails";
import CreditHistory from "./pages/CreditHistory";
import ApiKeys from "./pages/ApiKeys";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminInstances from "./pages/admin/AdminInstances";

export default function App() {
  return (
    <>
      <TopBar />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/instances/:instanceId"
          element={
            <RequireAuth>
              <InstanceDetails />
            </RequireAuth>
          }
        />
        <Route
          path="/credits"
          element={
            <RequireAuth>
              <CreditHistory />
            </RequireAuth>
          }
        />
        <Route
          path="/api-keys"
          element={
            <RequireAuth>
              <ApiKeys />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/users"
          element={
            <RequireAuth adminOnly>
              <AdminUsers />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/instances"
          element={
            <RequireAuth adminOnly>
              <AdminInstances />
            </RequireAuth>
          }
        />
      </Routes>
    </>
  );
}
