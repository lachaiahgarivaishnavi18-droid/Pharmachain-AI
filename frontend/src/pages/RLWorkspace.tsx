import "@xyflow/react/dist/style.css";
import { ArrowRight, Play, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import {
  Evidence,
  Panel,
  Status,
  Table,
  useData,
  type Row,
} from "../components";
import {
  Feedback,
  Heading,
  money,
  number,
  ProductSelect,
  useAction,
} from "./shared";
export function RLWorkspace() {
  const { data: products } = useData<Row[]>("/products", []);
  const { data: capabilities } = useData<Row>("/health/models", {});
  const [pid, setPid] = useState(1),
    [rec, setRec] = useState<Row | null>(null),
    [refresh, setRefresh] = useState(0),
    [algorithm, setAlgorithm] = useState("PPO"),
    [steps, setSteps] = useState(4096);
  const { data: runs } = useData<Row[]>("/rl/training-history", [], refresh);
  const { data: performance } = useData<Row | null>(
    "/rl/policy-performance",
    null,
    refresh,
  );
  const a = useAction();
  useEffect(() => {
    setRec(null);
  }, [pid]);
  useEffect(() => {
    if (!runs.some((r) => ["queued", "running"].includes(r.status))) return;
    const t = setInterval(() => setRefresh((x) => x + 1), 3000);
    return () => clearInterval(t);
  }, [runs]);
  return (
    <>
      <Heading
        tag="RESEARCH / REINFORCEMENT LEARNING"
        title="Explore a better replenishment policy"
        description="Train, evaluate, and inspect decisions in a reproducible synthetic environment."
      />
      <div className="two-col">
        <Panel
          title="Policy training"
          subtitle="CPU job · seeded simulation · versioned checkpoints"
        >
          <div className="control-bar">
            <select
              aria-label="Algorithm"
              value={algorithm}
              onChange={(e) => setAlgorithm(e.target.value)}
            >
              <option>PPO</option>
              <option>DQN</option>
            </select>
            <select
              aria-label="Training timesteps"
              value={steps}
              onChange={(e) => setSteps(+e.target.value)}
            >
              {[4096, 10000, 50000].map((x) => (
                <option key={x} value={x}>
                  {number(x)} steps
                </option>
              ))}
            </select>
            <button
              className="primary"
              disabled={
                capabilities.training_enabled === false ||
                a.busy ||
                runs.some((r) => ["queued", "running"].includes(r.status))
              }
              onClick={() =>
                a.run(async () => {
                  await api.post("/rl/train", {
                    algorithm,
                    timesteps: steps,
                    seed: 42,
                  });
                  setRefresh((x) => x + 1);
                }, "Training job submitted")
              }
            >
              <Play size={16} /> Train policy
            </button>
          </div>
          <div className="panel-note">
            {capabilities.training_enabled === false && <p>Hosted mode supports policy inference and evaluation. Run PPO/DQN training locally using the README commands.</p>}
            Short training runs validate the pipeline. They do not establish
            convergence or superiority.
          </div>
          <Table
            rows={runs}
            columns={[
              { key: "id", label: "Run" },
              {
                key: "config",
                label: "Algorithm",
                render: (r) => r.config.algorithm,
              },
              {
                key: "status",
                label: "Status",
                render: (r) => <Status value={r.status} />,
              },
              {
                key: "result",
                label: "Result",
                render: (r) =>
                  r.result.error || `${r.result.timesteps || 0} steps`,
              },
            ]}
          />
        </Panel>
        <Panel
          title="Decision inspection"
          subtitle="Inference uses a saved model; baseline is explicit when none exists"
        >
          <div className="control-bar">
            <ProductSelect products={products} value={pid} onChange={setPid} />
            <button
              className="primary"
              disabled={a.busy}
              onClick={() =>
                a.run(async () => {
                  setRec(
                    (await api.post("/rl/recommend", { product_id: pid })).data,
                  );
                }, "Recommendation computed")
              }
            >
              Recommend <ArrowRight size={16} />
            </button>
          </div>
          {rec ? (
            <div className="recommendation">
              <span className="eyebrow">{rec.source}</span>
              <h3>{rec.action}</h3>
              <strong className="rec-quantity">
                {number(rec.quantity)} <small>units</small>
              </strong>
              <div className="detail-grid">
                <span>
                  Available<strong>{rec.available}</strong>
                </span>
                <span>
                  Pending<strong>{rec.pending}</strong>
                </span>
                <span>
                  Reorder point<strong>{number(rec.reorder_point)}</strong>
                </span>
                <span>
                  Estimated cost<strong>{money(rec.estimated_cost)}</strong>
                </span>
              </div>
              <p>{rec.expected_benefit}</p>
              <span className="badge neutral">Human approval required</span>
              <details>
                <summary>Supporting evidence & uncertainty</summary>
                <Evidence value={rec} />
              </details>
            </div>
          ) : (
            <div className="empty">
              Select a product to compute an auditable recommendation.
            </div>
          )}
        </Panel>
      </div>
      <Feedback action={a} />
      <Panel
        title="Policy comparison"
        subtitle="Same held-out demand seeds · FEFO for all policies"
        actions={
          <button
            className="secondary"
            disabled={a.busy}
            onClick={() =>
              a.run(async () => {
                await api.post("/rl/evaluate");
                setRefresh((x) => x + 1);
              }, "Evaluation completed")
            }
          >
            <RefreshCw size={15} /> Evaluate
          </button>
        }
      >
        {performance ? (
          <>
            <div className="chart">
              <ResponsiveContainer>
                <BarChart data={performance.results}>
                  <CartesianGrid vertical={false} stroke="#edf0ef" />
                  <XAxis dataKey="policy" />
                  <YAxis />
                  <Tooltip />
                  <Bar
                    dataKey="total_cost"
                    fill="#298773"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <Table
              rows={performance.results}
              columns={[
                { key: "policy", label: "Policy" },
                {
                  key: "total_cost",
                  label: "Simulated cost",
                  render: (r) => r.total_cost.toFixed(1),
                },
                {
                  key: "service_level",
                  label: "Service level",
                  render: (r) => `${(r.service_level * 100).toFixed(1)}%`,
                },
                {
                  key: "stockout_rate",
                  label: "Stockout days",
                  render: (r) => `${(r.stockout_rate * 100).toFixed(1)}%`,
                },
                { key: "expiry_wastage", label: "Expiry wastage" },
                {
                  key: "constraint_violations",
                  label: "Constraint violations",
                },
              ]}
            />
            <div className="panel-note">{performance.limitations}</div>
          </>
        ) : (
          <div className="empty">
            Run evaluation to calculate actual simulation results.
          </div>
        )}
      </Panel>
      {runs.at(-1)?.result?.history && (
        <Panel
          title="Training diagnostics"
          subtitle="Sampled step reward; not episode-return convergence evidence"
        >
          <div className="chart">
            <ResponsiveContainer>
              <LineChart data={runs.at(-1)!.result.history}>
                <XAxis dataKey="step" />
                <YAxis />
                <Tooltip />
                <Line dataKey="mean_step_reward" stroke="#298773" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      )}
    </>
  );
}
