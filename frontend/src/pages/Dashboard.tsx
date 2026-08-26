import { useEffect, useState } from "react";
import CreateInstanceForm from "../components/CreateInstanceForm";
import InstanceRow from "../components/InstanceRow";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";
import type { Instance } from "../types";

export default function Dashboard() {
  const { user, refreshUser } = useAuth();
  const [instances, setInstances] = useState<Instance[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadInstances() {
    const data = await api.get<Instance[]>("/instances");
    setInstances(data);
    setLoading(false);
  }

  useEffect(() => {
    loadInstances();
    const interval = setInterval(loadInstances, 5000); // keep time-remaining/status fresh
    return () => clearInterval(interval);
  }, []);

  async function handleTerminate(id: string) {
    await api.delete(`/instances/${id}`);
    await loadInstances();
  }

  async function handleCreated(instance: Instance) {
    setInstances((prev) => [instance, ...prev]);
    await refreshUser(); // balance changed
  }

  const active = instances.filter((i) => i.status === "RUNNING" || i.status === "CREATING");
  const history = instances.filter((i) => !(i.status === "RUNNING" || i.status === "CREATING"));

  return (
    <div className="page">
      <div className="card">
        <p>User: {user?.username}</p>
        <p className="balance">Balance: {user?.credit_balance} credits</p>
      </div>

      <div className="card">
        <h2>Create Sandbox</h2>
        <CreateInstanceForm onCreated={handleCreated} />
      </div>

      <div className="card">
        <h2>Active Instances</h2>
        {loading ? (
          <p>Loading...</p>
        ) : active.length === 0 ? (
          <p>No active instances.</p>
        ) : (
          <div className="instance-list">
            {active.map((i) => (
              <InstanceRow key={i.id} instance={i} onTerminate={handleTerminate} />
            ))}
          </div>
        )}
      </div>

      {history.length > 0 && (
        <div className="card">
          <h2>Instance History</h2>
          <div className="instance-list">
            {history.map((i) => (
              <InstanceRow key={i.id} instance={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
