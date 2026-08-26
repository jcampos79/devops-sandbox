import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Terminal from "../components/Terminal";
import { api } from "../services/api";
import type { Instance } from "../types";

export default function InstanceDetails() {
  const { instanceId } = useParams<{ instanceId: string }>();
  const [instance, setInstance] = useState<Instance | null>(null);

  useEffect(() => {
    if (!instanceId) return;
    api.get<Instance>(`/instances/${instanceId}`).then(setInstance);
  }, [instanceId]);

  if (!instance) return <div className="page">Loading...</div>;

  return (
    <div className="page">
      <p>
        <Link to="/">&larr; Back to dashboard</Link>
      </p>
      <div className="card">
        <h1>Instance {instance.id}</h1>
        <table>
          <tbody>
            <tr>
              <th>Distribution</th>
              <td>{instance.distribution}</td>
            </tr>
            <tr>
              <th>Status</th>
              <td>
                <span className={`status-badge status-${instance.status}`}>{instance.status}</span>
              </td>
            </tr>
            <tr>
              <th>Created</th>
              <td>{new Date(instance.created_at).toLocaleString()}</td>
            </tr>
            <tr>
              <th>Expires</th>
              <td>{new Date(instance.expires_at).toLocaleString()}</td>
            </tr>
            <tr>
              <th>Credits consumed</th>
              <td>{instance.credits_charged}</td>
            </tr>
            <tr>
              <th>Kubernetes namespace</th>
              <td>{instance.namespace}</td>
            </tr>
            <tr>
              <th>Pod name</th>
              <td>{instance.pod_name}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {instance.status === "RUNNING" ? (
        <div className="card">
          <h2>Terminal</h2>
          <Terminal instanceId={instance.id} />
        </div>
      ) : (
        <p>Terminal is only available while the instance is running.</p>
      )}
    </div>
  );
}
