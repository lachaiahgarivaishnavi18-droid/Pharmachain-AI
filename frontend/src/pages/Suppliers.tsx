import "@xyflow/react/dist/style.css";
import { Plus } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import {
  DataForm,
  Modal,
  Notice,
  Panel,
  Table,
  useData,
  type Row,
} from "../components";
import { Heading, money } from "./shared";
export function Suppliers() {
  const [refresh, setRefresh] = useState(0),
    [modal, setModal] = useState(false),
    [detail, setDetail] = useState<Row | null>(null);
  const {
    data: rows,
    loading,
    error,
  } = useData<Row[]>("/suppliers", [], refresh);
  const { data: catalog } = useData<Row | null>(
    detail ? `/suppliers/${detail.id}` : "/health",
    null,
  );
  return (
    <>
      <Heading
        tag="PLANNING / SUPPLIERS"
        title="Build a more reliable supply network"
        description="Compare configured lead times, costs, and fulfillment reliability."
      >
        <button className="primary" onClick={() => setModal(true)}>
          <Plus size={16} /> Add supplier
        </button>
      </Heading>
      <Notice loading={loading} error={error} />
      <Panel
        title="Supplier directory"
        subtitle="Select a supplier to view its product catalog"
      >
        <Table
          rows={rows}
          onRow={setDetail}
          columns={[
            { key: "name", label: "Supplier" },
            {
              key: "lead_days",
              label: "Lead time",
              render: (r) => `${r.lead_days} days`,
            },
            {
              key: "reliability",
              label: "Configured reliability",
              render: (r) => (
                <div className="reliability">
                  <span>{(r.reliability * 100).toFixed(1)}%</span>
                  <div className="stock-track">
                    <i style={{ width: `${r.reliability * 100}%` }} />
                  </div>
                </div>
              ),
            },
            { key: "email", label: "Contact" },
          ]}
        />
      </Panel>
      {modal && (
        <Modal title="Register supplier" onClose={() => setModal(false)}>
          <DataForm
            fields={[
              { name: "name", label: "Supplier name" },
              { name: "email", label: "Contact email", type: "email" },
              {
                name: "lead_days",
                label: "Lead time (days)",
                type: "number",
                value: 7,
                min: 1,
              },
              {
                name: "reliability",
                label: "Reliability (0–1)",
                type: "number",
                value: 0.95,
                min: 0,
                max: 1,
              },
            ]}
            onSubmit={async (d) => {
              await api.post("/suppliers", d);
              setModal(false);
              setRefresh((x) => x + 1);
            }}
          />
        </Modal>
      )}
      {detail && (
        <Modal title={detail.name} onClose={() => setDetail(null)}>
          <Table
            rows={catalog?.catalog || []}
            columns={[
              { key: "product_id", label: "Product ID" },
              {
                key: "unit_cost",
                label: "Unit cost",
                render: (r) => money(r.unit_cost),
              },
              { key: "minimum_order", label: "MOQ" },
            ]}
          />
          <p className="muted">
            Reliability values are synthetic configured inputs. Real supplier
            delivery-performance integration is not available.
          </p>
        </Modal>
      )}
    </>
  );
}
