import {
  Activity,
  ArrowRight,
  Bell,
  Boxes,
  BrainCircuit,
  ChartNoAxesCombined,
  ChevronRight,
  ClipboardCheck,
  LayoutDashboard,
  LogOut,
  Menu,
  Network,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Thermometer,
  TrendingUp,
  Truck,
} from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { api, errorText } from "./api";
import { Notice } from "./components";
import {
  Agents,
  ColdChain,
  Dashboard,
  Forecast,
  Inventory,
  Orders,
  Reports,
  Risks,
  RLWorkspace,
  SettingsPage,
  Suppliers,
} from "./pages";
const nav = [
  ["/", "Overview", LayoutDashboard],
  ["/inventory", "Inventory", Boxes],
  ["/forecast", "Demand forecasting", TrendingUp],
  ["/optimization", "RL optimization", BrainCircuit],
  ["/cold-chain", "Cold chain", Thermometer],
  ["/suppliers", "Suppliers", Truck],
  ["/orders", "Purchase orders", ClipboardCheck],
  ["/agents", "Agent workflow", Network],
  ["/risks", "Risk assessment", ShieldAlert],
  ["/reports", "Reports & analytics", ChartNoAxesCombined],
  ["/settings", "Settings", Settings],
] as const;

function Login({ onLogin }: { onLogin: () => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    setBusy(true);
    try {
      const r = await api.post("/auth/login", {
        username: data.get("username"),
        password: data.get("password"),
      });
      sessionStorage.setItem("token", r.data.access_token);
      sessionStorage.setItem("user", JSON.stringify(r.data.user));
      onLogin();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-page">
      <div className="login-story">
        <div className="brand">
          <span className="brand-mark">
            <Activity />
          </span>{" "}
          PharmaChain<span>AI</span>
        </div>
        <div className="story-copy">
          <span className="eyebrow">INTELLIGENCE THROUGH THE SUPPLY CHAIN</span>
          <h1>
            Every dose.
            <br />
            Every degree.
            <br />
            <em>Better decisions.</em>
          </h1>
          <p>
            Inventory intelligence and cold-chain visibility, connected by an
            agentic research framework.
          </p>
          <div className="story-features">
            <span>
              <ShieldCheck /> Human-controlled decisions
            </span>
            <span>
              <Network /> Ten specialized agents
            </span>
          </div>
        </div>
        <small>SYNTHETIC RESEARCH ENVIRONMENT · VERSION 0.1</small>
      </div>
      <div className="login-form-wrap">
        <div className="login-form">
          <span className="eyebrow">WELCOME TO PHARMACHAIN</span>
          <h2>
            Your operations,
            <br />
            in perspective.
          </h2>
          <p>Sign in to your research workspace.</p>
          <form onSubmit={submit}>
            <label>
              Username
              <input
                name="username"
                autoComplete="username"
                defaultValue="admin"
                required
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                required
              />
            </label>
            <Notice error={error} />
            <button className="primary" disabled={busy}>
              {busy ? "Signing in…" : "Enter workspace"}
              <ArrowRight size={18} />
            </button>
          </form>
          <div className="demo-note">
            <ShieldCheck size={19} />
            <div>
              <strong>Local demonstration access</strong>
              <p>
                Use the demo username and password configured by your administrator.
                <br />
                All inventory, demand, and sensor data is synthetic. Change
                these credentials before any deployment.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [logged, setLogged] = useState(!!sessionStorage.getItem("token"));
  const [menu, setMenu] = useState(false);
  const location = useLocation();
  useEffect(() => {
    const reset = () => setLogged(false);
    window.addEventListener("session-expired", reset);
    return () => window.removeEventListener("session-expired", reset);
  }, []);
  if (!logged) return <Login onLogin={() => setLogged(true)} />;
  const user = JSON.parse(sessionStorage.getItem("user") || "{}");
  const title = nav.find((n) => n[0] === location.pathname)?.[1] || "Workspace";
  return (
    <div className="app-shell">
      <aside className={menu ? "sidebar mobile-open" : "sidebar"}>
        <NavLink to="/" className="brand">
          <span className="brand-mark">
            <Activity />
          </span>
          <div>
            PharmaChain<span>AI</span>
            <small>OPERATIONS INTELLIGENCE</small>
          </div>
        </NavLink>
        <div className="workspace-label">
          WORKSPACE <span>DEMO</span>
        </div>
        <nav>
          {nav.map(([path, label, Icon], i) => (
            <NavLink
              key={path}
              to={path}
              end={path === "/"}
              onClick={() => setMenu(false)}
            >
              {i === 6 && <span className="nav-separator" />}
              <Icon size={18} />
              <span>{label}</span>
              {path === "/agents" && <b>10</b>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="research-card">
            <span className="pulse" />
            <strong>Research environment</strong>
            <p>Simulated data. Real decision support.</p>
          </div>
          <button
            className="profile"
            onClick={() => {
              sessionStorage.clear();
              setLogged(false);
            }}
          >
            <span className="avatar">
              {user.username?.slice(0, 2).toUpperCase()}
            </span>
            <span>
              <strong>{user.username}</strong>
              <small>{user.role}</small>
            </span>
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <button
              className="icon-btn mobile-toggle"
              onClick={() => setMenu(!menu)}
              aria-label="Toggle navigation"
            >
              <Menu />
            </button>
            <span className="breadcrumb">
              Workspace <ChevronRight size={14} />
              <strong>{title}</strong>
            </span>
          </div>
          <div className="topbar-right">
            <span className="demo-chip">
              <span className="pulse" />
              Synthetic demo
            </span>
            <NavLink
              to="/cold-chain"
              className="icon-btn"
              aria-label="View alerts"
            >
              <Bell size={19} />
            </NavLink>
            <span className="avatar">
              {user.username?.slice(0, 2).toUpperCase()}
            </span>
          </div>
        </header>
        <div className="page-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/optimization" element={<RLWorkspace />} />
            <Route path="/cold-chain" element={<ColdChain />} />
            <Route path="/suppliers" element={<Suppliers />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/risks" element={<Risks />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
        <footer>
          PharmaChain AI{" "}
          <span>
            Research decision support · Synthetic data · Human approval required
          </span>
          <span>v0.1.0</span>
        </footer>
      </main>
    </div>
  );
}
