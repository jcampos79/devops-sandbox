import { Link } from "react-router-dom";
import type { Instance } from "../types";

function formatTimeRemaining(expiresAt: string): string {
  const ms = new Date(expiresAt).getTime() - Date.now();
  if (ms <= 0) return "0:00";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export default function InstanceRow({
  instance,
  onTerminate,
}: {
  instance: Instance;
  onTerminate?: (id: string) => void;
}) {
  const isActive = instance.status === "RUNNING" || instance.status === "CREATING";

  return (
    <div className="instance-row">
      <div>
        <strong>{instance.distribution}</strong>{" "}
        <span className={`status-badge status-${instance.status}`}>{instance.status}</span>
        <div className="cost-line">
          {isActive
            ? `Time remaining: ${formatTimeRemaining(instance.expires_at)}`
            : `Created ${new Date(instance.created_at).toLocaleString()}`}
          {" · "}
          {instance.credits_charged} credits
        </div>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {instance.status === "RUNNING" && (
          <Link to={`/instances/${instance.id}`}>
            <button>Open Terminal</button>
          </Link>
        )}
        {isActive && onTerminate && (
          <button className="danger" onClick={() => onTerminate(instance.id)}>
            Terminate
          </button>
        )}
        {!isActive && (
          <Link to={`/instances/${instance.id}`}>
            <button className="secondary">Details</button>
          </Link>
        )}
      </div>
    </div>
  );
}
