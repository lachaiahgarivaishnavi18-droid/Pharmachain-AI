import "@xyflow/react/dist/style.css";
import {
  ArrowRight,
  ArrowUpRight,
  Boxes,
  Download,
  Package,
  ShieldAlert,
  Sparkles,
  Thermometer,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { download } from "../api";
import {
  Metric,
  Notice,
  Panel,
  Status,
  Table,
  useData,
  type Row,
} from "../components";
import { Feedback, Heading, money, number, useAction } from "./shared";
export function Dashboard() {
  const { data: d, loading, error } = useData<Row>("/analytics/dashboard", {});
  const { data: sensors } = useData<Row[]>("/cold-chain/sensors", []);
  const { data: readings } = useData<Row[]>(
    "/cold-chain/readings?sensor_id=1&limit=48",
    [],
  );
  const { data: logs } = useData<Row[]>("/agents/executions", []);
  const a = useAction();
  return (
    <>
      <Heading
        tag="OPERATIONS / OVERVIEW"
        title="A clearer view of your supply chain"
        description="Inventory, conditions, and decisions. Connected in one workspace."
      >
        <button
          className="secondary"
          onClick={() =>
            a.run(() => download("inventory", "pdf"), "Report downloaded")
          }
        >
          <Download size={16} /> Export report
        </button>
        <Link className="primary" to="/agents">
          <Sparkles size={16} /> Run analysis
        </Link>
      </Heading>
      <Feedback action={a} />
      <Notice loading={loading} error={error} />
      <div className="overview-banner">
        <div>
          <span className="banner-icon">
            <ShieldAlert size={22} />
          </span>
          <div>
            <strong>Your attention makes the difference</strong>
            <p>
              {d.low_stock || 0} products below reorder levels ·{" "}
              {d.open_alerts || 0} open cold-chain alerts ·{" "}
              {d.pending_approvals || 0} purchase drafts awaiting review
            </p>
          </div>
        </div>
        <Link to="/risks">
          Review priorities <ArrowRight size={17} />
        </Link>
      </div>
      <div className="metrics">
        <Metric
          label="Available inventory"
          value={number(d.available_units)}
          note={`${d.products || 0} products across 5 warehouses`}
          icon={<Boxes size={19} />}
        />
        <Metric
          label="Usable inventory value"
          value={money(d.inventory_value)}
          note="Excludes expired and quarantined stock"
          icon={<Package size={19} />}
        />
        <Metric
          label="Low-stock products"
          value={number(d.low_stock)}
          note="Below configured reorder point"
          icon={<ShieldAlert size={19} />}
        />
        <Metric
          label="Cold-chain alerts"
          value={number(d.open_alerts)}
          note={`${number(d.quarantined)} units under quality hold`}
          icon={<Thermometer size={19} />}
        />
      </div>
      <div className="dashboard-grid">
        <Panel
          title="Inventory composition"
          subtitle="Available units by pharmaceutical category"
          actions={
            <Link className="subtle-link" to="/inventory">
              View inventory <ArrowUpRight size={15} />
            </Link>
          }
        >
          <div className="chart">
            <ResponsiveContainer>
              <BarChart
                data={d.categories || []}
                margin={{ top: 20, right: 24, left: 0, bottom: 10 }}
              >
                <CartesianGrid vertical={false} stroke="#edf0ef" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} />
                <Tooltip />
                <Bar
                  dataKey="value"
                  name="Usable units"
                  fill="#268774"
                  radius={[5, 5, 0, 0]}
                  maxBarSize={100}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-foot">
            <span>
              <i className="dot green" />
              Usable stock only
            </span>
            <span>Synthetic snapshot</span>
          </div>
        </Panel>
        <Panel
          title="Cold-chain pulse"
          subtitle="Refrigerator 01 · product-specific limits"
          actions={<span className="badge neutral">SYNTHETIC</span>}
        >
          <div className="temp-reading">
            <strong>
              {sensors[0]?.temperature?.toFixed(1) || "—"}
              <small>°C</small>
            </strong>
            <Status value={sensors[0]?.excursion ? "high" : "healthy"} />
          </div>
          <div className="chart compact">
            <ResponsiveContainer>
              <AreaChart
                data={readings.map((r) => ({
                  ...r,
                  time: r.timestamp.slice(11, 16),
                }))}
              >
                <defs>
                  <linearGradient id="tempfill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#d99451" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#d99451" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="time"
                  minTickGap={50}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 12]}
                  width={28}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip />
                <ReferenceLine y={8} stroke="#db9a61" strokeDasharray="4 4" />
                <Area
                  type="monotone"
                  dataKey="temperature"
                  stroke="#bc7a36"
                  fill="url(#tempfill)"
                  strokeWidth={2}
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-foot">
            <span>Configured range: 2–8 °C</span>
            <Link to="/cold-chain">
              Investigate <ArrowRight size={14} />
            </Link>
          </div>
        </Panel>
      </div>
      <div className="dashboard-grid bottom">
        <Panel
          title="Inventory requiring attention"
          subtitle="Prioritize shortages, shelf life, and quality holds"
          actions={
            <Link className="subtle-link" to="/inventory">
              All products <ArrowUpRight size={15} />
            </Link>
          }
        >
          <Table
            rows={(d.risk_products || []).slice(0, 6)}
            columns={[
              {
                key: "name",
                label: "Product",
                render: (r) => (
                  <div className="product-cell">
                    <span className="product-icon">
                      <Package size={16} />
                    </span>
                    <span>
                      <strong>{r.name}</strong>
                      <small>{r.category}</small>
                    </span>
                  </div>
                ),
              },
              {
                key: "available",
                label: "Usable units",
                render: (r) => number(r.available),
              },
              {
                key: "status",
                label: "Stock status",
                render: (r) => <Status value={r.status} />,
              },
              {
                key: "quarantined",
                label: "Quality hold",
                render: (r) => (r.quarantined ? number(r.quarantined) : "—"),
              },
            ]}
          />
        </Panel>
        <Panel
          title="Intelligence, coordinated"
          subtitle="Ten agents. One traceable workflow."
        >
          <div className="agent-illustration">
            <div className="agent-center">
              <Sparkles size={26} />
            </div>
            {["IN", "FC", "RL", "CC", "EX", "QA"].map((s, i) => (
              <span key={s} className={`agent-orbit orbit-${i}`}>
                {s}
              </span>
            ))}
          </div>
          <p className="agent-card-copy">
            Turn inventory, forecasts, and sensor evidence into explainable
            recommendations.
          </p>
          <div className="workflow-state">
            <span className="pulse" />
            {logs.length
              ? `${logs.filter((l) => l.status === "completed").length} recorded agent executions`
              : "Ready for your first analysis"}
          </div>
          <Link to="/agents" className="secondary full">
            Open agent workspace <ArrowRight size={16} />
          </Link>
        </Panel>
      </div>
    </>
  );
}
