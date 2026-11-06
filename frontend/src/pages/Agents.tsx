import { Background, Controls, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Play } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import {
  Evidence,
  Modal,
  Notice,
  Panel,
  Status,
  Table,
  useData,
  type Row,
} from "../components";
import { Feedback, Heading, ProductSelect, useAction } from "./shared";
export function Agents() {
  const { data: agents } = useData<Row[]>("/agents", []);
  const { data: products } = useData<Row[]>("/products", []);
  const [pid, setPid] = useState(1),
    [refresh, setRefresh] = useState(0),
    [selected, setSelected] = useState<Row | null>(null);
  const {
    data: logs,
    loading,
    error,
  } = useData<Row[]>("/agents/executions", [], refresh);
  const a = useAction();
  const latestRun = logs[0]?.run_id;
  const latest = logs.filter((x) => x.run_id === latestRun);
  const nodes = agents.map((agent, i) => {
    const execution = latest.find((x) => x.agent === agent.id);
    return {
      id: agent.id,
      position: { x: (i % 5) * 230, y: Math.floor(i / 5) * 150 },
      data: {
        label: (
          <div>
            <small>AGENT {String(i + 1).padStart(2, "0")}</small>
            <strong>{agent.name}</strong>
            <span>{execution ? execution.status : "Ready"}</span>
          </div>
        ),
      },
      style: {
        background: execution?.status === "completed" ? "#eaf4ef" : "#fff",
        borderColor: execution?.status === "failed" ? "#d68271" : "#ccdcd4",
        borderRadius: 10,
        width: 205,
        padding: 12,
      },
    };
  });
  return (
    <>
      <Heading
        tag="INTELLIGENCE / AGENT WORKFLOW"
        title="From signals to a shared decision"
        description="A LangGraph workflow with structured outputs and measured execution records."
      />
      <div className="control-bar">
        <ProductSelect products={products} value={pid} onChange={setPid} />
        <button
          className="primary"
          disabled={a.busy}
          onClick={() =>
            a.run(async () => {
              await api.post("/agents/run", { product_id: pid });
              setRefresh((x) => x + 1);
            }, "Workflow finished; inspect individual node results below")
          }
        >
          <Play size={16} />
          {a.busy ? "Agents are analyzing…" : "Run integrated analysis"}
        </button>
        <span className="muted">
          Deterministic local tools · No paid LLM required
        </span>
      </div>
      <Feedback action={a} />
      <Panel
        title="Ten specialized agents, one traceable run"
        subtitle={
          latestRun
            ? `Latest run: ${latestRun}`
            : "No executions yet. Nodes show readiness, not fabricated results."
        }
      >
        <div className="workflow-canvas">
          <ReactFlow
            nodes={nodes}
            edges={agents.slice(1).map((agent, i) => ({
              id: `e${i}`,
              source: agents[i].id,
              target: agent.id,
              animated: a.busy,
            }))}
            fitView
            nodesDraggable={false}
            nodesConnectable={false}
            onNodeClick={(_, n) => {
              const log = latest.find((x) => x.agent === n.id);
              if (log) setSelected(log);
            }}
          >
            <Background color="#d9e3df" gap={18} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      </Panel>
      <Notice loading={loading} error={error} />
      <Panel
        title="Execution log"
        subtitle="Actual durations, errors, and validated outputs"
      >
        <Table
          rows={latest}
          onRow={setSelected}
          columns={[
            {
              key: "agent",
              label: "Agent",
              render: (r) =>
                agents.find((a) => a.id === r.agent)?.name || r.agent,
            },
            {
              key: "status",
              label: "Status",
              render: (r) => <Status value={r.status} />,
            },
            {
              key: "duration_ms",
              label: "Duration",
              render: (r) => `${r.duration_ms.toFixed(1)} ms`,
            },
            {
              key: "output",
              label: "Output summary",
              render: (r) => r.output.summary,
            },
            { key: "error", label: "Error" },
          ]}
        />
      </Panel>
      {selected && (
        <Modal
          title={`${selected.agent} · execution #${selected.id}`}
          onClose={() => setSelected(null)}
        >
          <Evidence value={selected} />
        </Modal>
      )}
    </>
  );
}
