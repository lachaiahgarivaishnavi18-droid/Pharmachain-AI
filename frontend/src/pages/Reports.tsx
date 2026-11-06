import "@xyflow/react/dist/style.css";
import { Download } from "lucide-react";
import { useState } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { download } from "../api";
import { Notice, Panel, Table, useData, type Row } from "../components";
import { Feedback, Heading, useAction } from "./shared";
export function Reports() {
  const [kind, setKind] = useState("inventory");
  const {
    data: stock,
    loading,
    error,
  } = useData<Row[]>("/analytics/inventory", []);
  const { data: forecasts } = useData<Row[]>("/forecast/metrics", []);
  const { data: logs } = useData<Row[]>("/agents/executions", []);
  const a = useAction();
  return (
    <>
      <Heading
        tag="RESEARCH / REPORTS & ANALYTICS"
        title="Make the evidence portable"
        description="Export synthetic datasets and inspect measured model and workflow performance."
      />
      <Notice loading={loading} error={error} />
      <Panel
        title="Dataset exports"
        subtitle="CSV and JSON preserve record-level data; PDF is an inventory summary"
      >
        <div className="control-bar">
          <select
            aria-label="Dataset"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            {[
              "inventory",
              "products",
              "batches",
              "demand",
              "readings",
              "shipments",
            ].map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
          {["csv", "json", ...(kind === "inventory" ? ["pdf"] : [])].map(
            (format) => (
              <button
                key={format}
                className="secondary"
                disabled={a.busy}
                onClick={() =>
                  a.run(
                    () => download(kind, format),
                    `${format.toUpperCase()} downloaded`,
                  )
                }
              >
                <Download size={16} />
                {format.toUpperCase()}
              </button>
            ),
          )}
        </div>
        <Feedback action={a} />
      </Panel>
      <div className="two-col">
        <Panel
          title="Stock exposure"
          subtitle="Units by availability classification"
        >
          <div className="chart">
            <ResponsiveContainer>
              <BarChart
                data={[
                  {
                    name: "Available",
                    value: stock.reduce((s, r) => s + r.available, 0),
                  },
                  {
                    name: "Quarantined",
                    value: stock.reduce((s, r) => s + r.quarantined, 0),
                  },
                  {
                    name: "Expired",
                    value: stock.reduce((s, r) => s + r.expired, 0),
                  },
                ]}
              >
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#3e8e7a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel
          title="Agent execution performance"
          subtitle="Measured wall-clock time for recorded executions"
        >
          <Table
            rows={Object.values(
              logs.reduce((acc: Row, r) => {
                if (!acc[r.agent])
                  acc[r.agent] = {
                    agent: r.agent,
                    count: 0,
                    total: 0,
                    failures: 0,
                  };
                acc[r.agent].count++;
                acc[r.agent].total += r.duration_ms;
                acc[r.agent].failures += r.status === "failed" ? 1 : 0;
                return acc;
              }, {}),
            )}
            columns={[
              { key: "agent", label: "Agent" },
              { key: "count", label: "Runs" },
              {
                key: "mean",
                label: "Mean ms",
                render: (r) => (r.total / r.count).toFixed(1),
              },
              { key: "failures", label: "Failures" },
            ]}
          />
        </Panel>
      </div>
      <Panel
        title="Forecast test performance"
        subtitle="Recorded only after a real forecast run"
      >
        <Table
          rows={forecasts.slice(-20)}
          columns={[
            { key: "product_id", label: "Product ID" },
            {
              key: "model",
              label: "Selected model",
              render: (r) => r.result.model,
            },
            {
              key: "mae",
              label: "MAE",
              render: (r) => r.result.MAE.toFixed(2),
            },
            {
              key: "rmse",
              label: "RMSE",
              render: (r) => r.result.RMSE.toFixed(2),
            },
            {
              key: "wape",
              label: "WAPE",
              render: (r) => r.result.WAPE?.toFixed(2),
            },
          ]}
        />
      </Panel>
    </>
  );
}
