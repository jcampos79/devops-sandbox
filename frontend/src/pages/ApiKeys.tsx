import { useEffect, useState, type FormEvent } from "react";
import { api } from "../services/api";

interface ApiKeyOut {
  id: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKeyOut[]>([]);
  const [name, setName] = useState("");
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);

  async function load() {
    setKeys(await api.get<ApiKeyOut[]>("/me/api-keys"));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    const result = await api.post<{ api_key: string }>("/me/api-keys", { name });
    setNewlyCreatedKey(result.api_key);
    setName("");
    await load();
  }

  async function handleRevoke(id: string) {
    await api.delete(`/me/api-keys/${id}`);
    await load();
  }

  return (
    <div className="page">
      <div className="card">
        <h1>API Keys</h1>
        <p>Use API keys for programmatic access: <code>Authorization: Bearer &lt;API_KEY&gt;</code></p>

        {newlyCreatedKey && (
          <div className="card" style={{ borderColor: "#3a5fcd" }}>
            <p>
              <strong>Save this key now -- it won't be shown again:</strong>
            </p>
            <code>{newlyCreatedKey}</code>
          </div>
        )}

        <form onSubmit={handleCreate} className="create-form">
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <button type="submit">Create API Key</button>
        </form>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Created</th>
              <th>Last used</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k.id}>
                <td>{k.name}</td>
                <td>{new Date(k.created_at).toLocaleDateString()}</td>
                <td>{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "Never"}</td>
                <td>{k.revoked_at ? "Revoked" : "Active"}</td>
                <td>
                  {!k.revoked_at && (
                    <button className="danger" onClick={() => handleRevoke(k.id)}>
                      Revoke
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
