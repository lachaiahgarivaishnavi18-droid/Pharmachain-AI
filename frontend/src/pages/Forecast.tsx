import "@xyflow/react/dist/style.css";
import { Play, Sparkles } from "lucide-react";
import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import { Metric, Notice, Panel, Table, useData, type Row } from "../components";
import { Feedback, Heading, ProductSelect, useAction } from "./shared";
export function Forecast() {
  const { data: products } = useData<Row[]>("/products", []);
  const [pid, setPid] = useState(1),
    [horizon, setHorizon] = useState(30),
    [advanced, setAdvanced] = useState(false),
    [refresh, setRefresh] = useState(0);
  const {
    data: f,
    loading,
    error,
  } = useData<Row | null>(`/forecast/${pid}`, null, refresh);
  const a = useAction();
  const chart = [...(f?.history || []), ...(f?.forecast || [])];
  return (
    <>
      <Heading
        tag="INTELLIGENCE / FORECASTING"
        title="See demand before it arrives"
        description="Compare models using chronological validation and a held-out test period."
      />
      <div className="control-bar">
        <ProductSelect products={products} value={pid} onChange={setPid} />
        <select
          aria-label="Forecast horizon"
          value={horizon}
          onChange={(e) => setHorizon(+e.target.value)}
        >
          {[7, 14, 30, 60, 90].map((n) => (
            <option key={n} value={n}>
              {n} days
            </option>
          ))}
        </select>
        <label className="check-label">
          <input
            type="checkbox"
            checked={advanced}
            onChange={(e) => setAdvanced(e.target.checked)}
          />{" "}
          Include ARIMA & XGBoost
        </label>
        <button
          className="primary"
          disabled={a.busy}
          onClick={() =>
            a.run(async () => {
              await api.post("/forecast/run", {
                product_id: pid,
                horizon,
                advanced,
              });
              setRefresh((x) => x + 1);
            }, "Forecast generated")
          }
        >
          <Play size={16} />
          {a.busy ? "Comparing models…" : "Generate forecast"}
        </button>
      </div>
      <Feedback action={a} />
      <Notice loading={loading} error={error} />
      {f ? (
        <>
          <div className="metrics">
            <Metric
              label="Selected model"
              value={<span className="small-value">{f.model}</span>}
              note="Lowest validation MAE"
            />
            <Metric
              label="Test MAE"
              value={f.test_metrics.MAE.toFixed(2)}
              note="Units per day"
            />
            <Metric
              label="Test RMSE"
              value={f.test_metrics.RMSE.toFixed(2)}
              note="Held-out period"
            />
            <Metric
              label="Test WAPE"
              value={`${f.test_metrics.WAPE?.toFixed(1)}%`}
              note="Weighted absolute percentage error"
            />
          </div>
          <Panel
            title="Demand outlook"
            subtitle="Historical demand and recursively generated forecast"
          >
            <div className="chart tall">
              <ResponsiveContainer>
                <LineChart data={chart}>
                  <CartesianGrid stroke="#edf0ef" vertical={false} />
                  <XAxis
                    dataKey="date"
                    minTickGap={70}
                    tickFormatter={(v) => v.slice(5)}
                  />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line
                    dataKey="actual"
                    name="Historical demand"
                    stroke="#94aaa4"
                    dot={false}
                  />
                  <Line
                    dataKey="predicted"
                    name="Forecast"
                    stroke="#1c7e69"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    dataKey="upper"
                    name="Approximate upper band"
                    stroke="#cba77b"
                    strokeDasharray="4 4"
                    dot={false}
                  />
                  <Line
                    dataKey="lower"
                    name="Approximate lower band"
                    stroke="#cba77b"
                    strokeDasharray="4 4"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Panel>
          <Panel
            title="Validation model comparison"
            subtitle={`Train: ${f.split.train} days · Validation: ${f.split.validation} days · Test: ${f.split.test} days`}
          >
            <Table
              rows={f.comparison}
              columns={[
                { key: "model", label: "Model" },
                ...["MAE", "RMSE", "MAPE", "WAPE"].map((k) => ({
                  key: k,
                  label: k,
                  render: (r: Row) => r[k]?.toFixed(2) ?? "N/A",
                })),
              ]}
            />
            <div className="panel-note">{f.limitations.join(" · ")}</div>
          </Panel>
        </>
      ) : (
        !loading && (
          <Panel
            title="Generate your first forecast"
            subtitle="At least 90 consecutive demand days are required"
          >
            <div className="empty">
              <Sparkles size={32} />
              <p>
                Choose a product and run the model comparison. No forecasts are
                fabricated.
              </p>
            </div>
          </Panel>
        )
      )}
    </>
  );
}
