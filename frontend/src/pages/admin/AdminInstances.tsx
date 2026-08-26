import { useEffect, useState } from "react";
import { api } from "../../services/api";
import type { Instance } from "../../types";

export default function AdminInstances() {
  const [instances, setInstances] = useState<Instance[]>([]);

  async function load() {
    setInstances(await api.get<Instance[]>("/admin/instances"));
  }

  useEffect(() => {
    load();
  }, []);

  async function terminate(id: string) {
    await api.delete(`/admin/instances/${id}`);
    await load();
  }

  return (
    <div className="page">
      <div className="card">
        <h1>All Instances</h1>
        <table>
          <thead>
            <tr>
              <th>Distribution</th>
              <th>Status</th>
              <th>Namespace</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {instances.map((i) => (
              <tr key={i.id}>
                <td>{i.distribution}</td>
                <td>
                  <span className={`status-badge status-${i.status}`}>{i.status}</span>
                </td>
                <td>{i.namespace}</td>
                <td>{new Date(i.created_at).toLocaleString()}</td>
                <td>
                  {(i.status === "RUNNING" || i.status === "CREATING") && (
                    <button className="danger" onClick={() => terminate(i.id)}>
                      Terminate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
