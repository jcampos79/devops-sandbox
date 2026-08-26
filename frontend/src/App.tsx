import { Routes, Route } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import InstanceDetails from "./pages/InstanceDetails";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Dashboard />} />
      <Route path="/instances/:instanceId" element={<InstanceDetails />} />
    </Routes>
  );
}
