import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function TopBar() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="topbar">
      <nav>
        <Link to="/">Dashboard</Link>
        <Link to="/credits">Credit History</Link>
        <Link to="/api-keys">API Keys</Link>
        {user.is_admin && (
          <>
            <Link to="/admin/users">Admin: Users</Link>
            <Link to="/admin/instances">Admin: Instances</Link>
          </>
        )}
      </nav>
      <div>
        <span style={{ marginRight: 12 }}>{user.username}</span>
        <button className="secondary" onClick={logout}>
          Log out
        </button>
      </div>
    </div>
  );
}
