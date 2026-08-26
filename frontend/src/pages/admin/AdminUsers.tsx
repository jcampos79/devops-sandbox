import { useEffect, useState, type FormEvent } from "react";
import { api } from "../../services/api";

interface UserOut {
  id: string;
  username: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export default function AdminUsers() {
  const [users, setUsers] = useState<UserOut[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [creditAmounts, setCreditAmounts] = useState<Record<string, string>>({});

  async function load() {
    setUsers(await api.get<UserOut[]>("/admin/users"));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    await api.post("/admin/users", { username, password, is_admin: isAdmin });
    setUsername("");
    setPassword("");
    setIsAdmin(false);
    await load();
  }

  async function toggleActive(user: UserOut) {
    await api.post(`/admin/users/${user.id}/${user.is_active ? "disable" : "enable"}`);
    await load();
  }

  async function grantCredits(userId: string) {
    const amount = Number(creditAmounts[userId] || 0);
    if (!amount) return;
    await api.post(`/admin/users/${userId}/credits`, { amount, description: "Admin adjustment" });
    setCreditAmounts((prev) => ({ ...prev, [userId]: "" }));
  }

  return (
    <div className="page">
      <div className="card">
        <h1>Users</h1>
        <form onSubmit={handleCreate} className="create-form">
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          <label>
            <input
              type="checkbox"
              checked={isAdmin}
              onChange={(e) => setIsAdmin(e.target.checked)}
              style={{ marginRight: 6 }}
            />
            Admin
          </label>
          <button type="submit">Create User</button>
        </form>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Admin</th>
              <th>Status</th>
              <th>Grant/deduct credits</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.is_admin ? "Yes" : "No"}</td>
                <td>{u.is_active ? "Active" : "Disabled"}</td>
                <td>
                  <input
                    type="number"
                    style={{ width: 90 }}
                    value={creditAmounts[u.id] ?? ""}
                    onChange={(e) =>
                      setCreditAmounts((prev) => ({ ...prev, [u.id]: e.target.value }))
                    }
                  />
                  <button onClick={() => grantCredits(u.id)} style={{ marginLeft: 6 }}>
                    Apply
                  </button>
                </td>
                <td>
                  <button className="secondary" onClick={() => toggleActive(u)}>
                    {u.is_active ? "Disable" : "Enable"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
