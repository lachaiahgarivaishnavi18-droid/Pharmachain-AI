import "@xyflow/react/dist/style.css";
import { ArrowRight, Plus, RefreshCw, Thermometer } from "lucide-react";
import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import {
  DataForm,
  Modal,
  Notice,
  Panel,
  Status,
  Table,
  useData,
  type Row,
} from "../components";
import { Feedback, Heading, useAction } from "./shared";
export function ColdChain() {
  const [refresh, setRefresh] = useState(0),
    [sid, setSid] = useState(1),
    [investigate, setInvestigate] = useState<Row | null>(null);
  const {
    data: sensors,
    loading,
    error,
  } = useData<Row[]>("/cold-chain/sensors", [], refresh);
  const { data: readings } = useData<Row[]>(
    `/cold-chain/readings?sensor_id=${sid}&limit=96`,
    [],
    refresh,
  );
  const { data: alerts } = useData<Row[]>("/cold-chain/alerts", [], refresh);
  const { data: excursions } = useData<Row[]>(
    "/cold-chain/excursions",
    [],
    refresh,
  );
  const { data: shipments } = useData<Row[]>(
    "/cold-chain/shipments",
    [],
    refresh,
  );
  const a = useAction();
  const selected = sensors.find((s) => s.id === sid);
  async function simulate() {
    await api.post("/cold-chain/readings", {
      sensor_id: sid,
      timestamp: new Date().toISOString(),
      temperature: 5 + Math.random() * 5,
      source: "synthetic",
    });
    setRefresh((x) => x + 1);
  }
  return (
    <>
      <Heading
        tag="OPERATIONS / COLD CHAIN"
        title="Conditions matter. Visibility helps."
        description="Product-specific limits, preserved readings, and traceable investigation."
      >
        <button className="secondary" onClick={() => setRefresh((x) => x + 1)}>
          <RefreshCw size={16} /> Refresh
        </button>
        <button
          className="primary"
          disabled={a.busy}
          onClick={() => a.run(simulate, "Synthetic reading recorded")}
        >
          <Plus size={16} /> Simulate reading
        </button>
      </Heading>
      <Notice loading={loading} error={error} />
      <Feedback action={a} />
      <div className="sensor-grid">
        {sensors.map((s) => (
          <button
            key={s.id}
            className={`sensor-card ${s.id === sid ? "active" : ""}`}
            onClick={() => setSid(s.id)}
          >
            <span>
              {s.name}
              <Thermometer size={17} />
            </span>
            <strong>
              {s.temperature?.toFixed(1) ?? "—"}
              <small>°C</small>
            </strong>
            <div>
              <Status
                value={
                  s.status === "missing"
                    ? "missing"
                    : s.excursion
                      ? "high"
                      : s.status
                }
              />
              <small>
                {s.temp_min}–{s.temp_max} °C
              </small>
            </div>
          </button>
        ))}
      </div>
      <Panel
        title={selected?.name || "Temperature history"}
        subtitle={`${selected?.product || ""} · Synthetic readings · Select a logger above`}
      >
        <div className="chart tall">
          <ResponsiveContainer>
            <LineChart
              data={readings.map((r) => ({
                ...r,
                time: r.timestamp.slice(11, 16),
              }))}
            >
              <CartesianGrid vertical={false} stroke="#edf0ef" />
              <XAxis dataKey="time" minTickGap={45} />
              <YAxis domain={["auto", "auto"]} />
              <Tooltip />
              <ReferenceLine
                y={selected?.temp_min}
                stroke="#d09961"
                label="Lower limit"
                strokeDasharray="4 4"
              />
              <ReferenceLine
                y={selected?.temp_max}
                stroke="#d09961"
                label="Upper limit"
                strokeDasharray="4 4"
              />
              <Line
                dataKey="temperature"
                stroke="#287f70"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <Panel
        title="Excursion & investigation queue"
        subtitle="Recovery does not release quarantined stock"
      >
        <Table
          rows={alerts}
          columns={[
            { key: "id", label: "Alert" },
            { key: "message", label: "Evidence" },
            {
              key: "status",
              label: "Status",
              render: (r) => <Status value={r.status} />,
            },
            {
              key: "action",
              label: "Review",
              render: (r) => (
                <button
                  className="text-button"
                  onClick={() => setInvestigate(r)}
                >
                  Investigate <ArrowRight size={14} />
                </button>
              ),
            },
          ]}
        />
      </Panel>
      <div className="two-col">
        <Panel
          title="Excursion traceability"
          subtitle="Duration is observed exposure; never a stability calculation"
        >
          <Table
            rows={excursions}
            columns={[
              { key: "id", label: "Event" },
              { key: "duration_minutes", label: "Minutes" },
              {
                key: "maximum",
                label: "Max °C",
                render: (r) => r.maximum.toFixed(1),
              },
              {
                key: "affected_batches",
                label: "Batch IDs",
                render: (r) => r.affected_batches.join(", ") || "None linked",
              },
            ]}
          />
        </Panel>
        <Panel title="Shipments" subtitle="Synthetic transportation records">
          <Table
            rows={shipments}
            columns={[
              { key: "reference", label: "Shipment" },
              { key: "destination", label: "Destination" },
              {
                key: "status",
                label: "Status",
                render: (r) => <Status value={r.status} />,
              },
            ]}
          />
        </Panel>
      </div>
      {investigate && (
        <Modal
          title={`Investigate alert #${investigate.id}`}
          onClose={() => setInvestigate(null)}
        >
          <p>{investigate.message}</p>
          <DataForm
            fields={[
              {
                name: "reason",
                label: "Investigation note / authorized procedure reference",
              },
            ]}
            submit="Record investigation"
            onSubmit={async (d) => {
              await api.post(
                `/cold-chain/alerts/${investigate.id}/investigate`,
                d,
              );
              setInvestigate(null);
              setRefresh((x) => x + 1);
            }}
          >
            <p className="muted">
              Quality or administrator role required. This action records an
              investigation and does not release, discard, or declare any
              product safe.
            </p>
          </DataForm>
        </Modal>
      )}
    </>
  );
}
