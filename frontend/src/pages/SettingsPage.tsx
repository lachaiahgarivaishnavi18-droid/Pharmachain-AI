import "@xyflow/react/dist/style.css";
import { ArrowUpRight, Plus } from "lucide-react";
import { useState } from "react";
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
export function SettingsPage() {
  const [refresh, setRefresh] = useState(0),
    [modal, setModal] = useState("");
  const {
    data: settings,
    loading,
    error,
  } = useData<Row[]>("/settings", [], refresh);
  const { data: health } = useData<Row>("/health/database", {});
  const { data: models } = useData<Row>("/health/models", {});
  const a = useAction();
  const user = JSON.parse(sessionStorage.getItem("user") || "{}");
  const { data: users } = useData<Row[]>(
    user.role === "admin" ? "/users" : "/products?limit=1",
    [],
    refresh,
  );
  return (
    <>
      <Heading
        tag="WORKSPACE / SETTINGS"
        title="Configured for careful decisions"
        description="Manage research settings, users, and data. Secrets stay on the server."
      />
      <Notice loading={loading} error={error} />
      <Feedback action={a} />
      <div className="two-col">
        <Panel
          title="System status"
          subtitle="Local services and model availability"
        >
          <div className="setting-row">
            <span>Database</span>
            <Status value={health.status || "loading"} />
            <strong>{health.dialect}</strong>
          </div>
          <div className="setting-row">
            <span>Forecasting</span>
            <Status value={models.forecast || "loading"} />
          </div>
          <div className="setting-row">
            <span>Saved RL models</span>
            <strong>{models.rl_models || 0}</strong>
          </div>
          <div className="setting-row">
            <span>LLM explanations</span>
            <strong>Deterministic local mode</strong>
          </div>
          <p className="panel-note">
            External LLM integration is not enabled. Operational calculations
            always use deterministic tools.
          </p>
        </Panel>
        <Panel
          title="Research configuration"
          subtitle="Administrator access required to edit"
        >
          <DataForm
            key={refresh}
            fields={[
              {
                name: "near_expiry_days",
                label: "Near-expiry threshold (days)",
                type: "number",
                value: settings[0]?.value.near_expiry_days || 90,
                min: 1,
                max: 3650,
              },
              {
                name: "retention_days",
                label: "Retention preference (days)",
                type: "number",
                value: settings[0]?.value.retention_days || 365,
                min: 1,
                max: 3650,
              },
            ]}
            onSubmit={async (d) => {
              await api.put("/settings", d);
              setRefresh((x) => x + 1);
            }}
            submit="Save configuration"
          >
            <p className="muted">
              Retention is a stored preference; automated deletion is not
              enabled. Temperature thresholds are configured per product through
              the API.
            </p>
          </DataForm>
        </Panel>
      </div>
      <Panel
        title="Data import"
        subtitle="Validated JSON arrays or CSV files with header names matching the API schema"
      >
        <div className="control-bar">
          <button className="secondary" onClick={() => setModal("products")}>
            <Plus size={16} /> Import products
          </button>
          <button className="secondary" onClick={() => setModal("demand")}>
            <Plus size={16} /> Import demand history
          </button>
          <a
            href={import.meta.env.DEV ? "http://127.0.0.1:8000/docs" : "/docs"}
            target="_blank"
            rel="noreferrer"
            className="subtle-link"
          >
            API documentation <ArrowUpRight size={15} />
          </a>
        </div>
      </Panel>
      {user.role === "admin" && (
        <Panel
          title="Users & roles"
          subtitle="Passwords are salted and hashed"
          actions={
            <button className="secondary" onClick={() => setModal("user")}>
              <Plus size={16} /> Create user
            </button>
          }
        >
          <Table
            rows={users}
            columns={[
              { key: "username", label: "Username" },
              { key: "role", label: "Role" },
            ]}
          />
        </Panel>
      )}
      {modal && (
        <Modal
          title={modal === "user" ? "Create user" : `Import ${modal}`}
          onClose={() => setModal("")}
        >
          {modal === "user" ? (
            <DataForm
              fields={[
                { name: "username", label: "Username" },
                {
                  name: "password",
                  label: "Password (12+ characters)",
                  type: "password",
                },
                {
                  name: "role",
                  label: "Role",
                  options: [
                    "viewer",
                    "operator",
                    "manager",
                    "quality",
                    "admin",
                  ].map((x) => ({ value: x, label: x })),
                },
              ]}
              onSubmit={async (d) => {
                await api.post("/users", d);
                setModal("");
                setRefresh((x) => x + 1);
              }}
            />
          ) : (
            <ImportForm
              kind={modal}
              onDone={() => {
                setModal("");
                setRefresh((x) => x + 1);
              }}
            />
          )}
        </Modal>
      )}
    </>
  );
}
function ImportForm({ kind, onDone }: { kind: string; onDone: () => void }) {
  const [value, setValue] = useState("[]");
  const a = useAction();
  return (
    <>
      <label>
        JSON records
        <textarea
          rows={14}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </label>
      <label className="file-label">
        Load JSON or CSV
        <input
          type="file"
          accept=".json,.csv"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            try {
              const text = await file.text();
              if (file.name.endsWith(".csv")) {
                const { parseCSV } = await import("../csv");
                setValue(JSON.stringify(parseCSV(text), null, 2));
              } else setValue(text);
            } catch (e) {
              await a.run(async () => {
                throw e;
              });
            }
          }}
        />
      </label>
      <Feedback action={a} />
      <button
        className="primary"
        disabled={a.busy}
        onClick={() =>
          a.run(async () => {
            let data = JSON.parse(value);
            if (data.records) data = data.records;
            await api.post(`/import/${kind}`, data);
            onDone();
          }, "Imported")
        }
      >
        Validate & import
      </button>
    </>
  );
}
