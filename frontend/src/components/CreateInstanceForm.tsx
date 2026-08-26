import { useState, type FormEvent } from "react";
import { api, ApiError } from "../services/api";
import type { Distribution, Instance } from "../types";

const DISTRIBUTIONS: { value: Distribution; label: string }[] = [
  { value: "ubuntu", label: "Ubuntu 24.04" },
  { value: "rocky", label: "Rocky Linux 9" },
  { value: "debian", label: "Debian 13" },
  { value: "alpine", label: "Alpine" },
];

const MAX_DURATION = 30;

export default function CreateInstanceForm({ onCreated }: { onCreated: (i: Instance) => void }) {
  const [distribution, setDistribution] = useState<Distribution>("ubuntu");
  const [duration, setDuration] = useState(10);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const instance = await api.post<Instance>("/instances", {
        distribution,
        duration_minutes: duration,
      });
      onCreated(instance);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create instance");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="create-form">
      <label>
        Distribution
        <select value={distribution} onChange={(e) => setDistribution(e.target.value as Distribution)}>
          {DISTRIBUTIONS.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Duration (minutes)
        <input
          type="number"
          min={1}
          max={MAX_DURATION}
          value={duration}
          onChange={(e) =>
            setDuration(Math.min(MAX_DURATION, Math.max(1, Number(e.target.value) || 1)))
          }
        />
      </label>
      <div className="cost-line">Cost: {duration} credits</div>
      <button type="submit" disabled={submitting}>
        {submitting ? "Creating..." : "Create Instance"}
      </button>
      {error && <p className="error-text">{error}</p>}
    </form>
  );
}
