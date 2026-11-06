import "@xyflow/react/dist/style.css";
import { Plus, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import {
  DataForm,
  Evidence,
  Modal,
  Notice,
  Panel,
  Status,
  Table,
  useData,
  type Row,
} from "../components";
import { Heading, money, productOptions } from "./shared";
export function Orders() {
  const [refresh, setRefresh] = useState(0),
    [modal, setModal] = useState(false),
    [decision, setDecision] = useState<{ row: Row; action: string } | null>(
      null,
    ),
    [detail, setDetail] = useState<Row | null>(null);
  const {
    data: rows,
    loading,
    error,
  } = useData<Row[]>("/purchase-orders", [], refresh);
  const { data: suppliers } = useData<Row[]>("/suppliers", []);
  const { data: products } = useData<Row[]>("/products", []);
  return (
    <>
      <Heading
        tag="PLANNING / PURCHASE ORDERS"
        title="A human decision at every commitment"
        description="Prepare drafts, review costs, and record authorized approvals."
      >
        <button className="primary" onClick={() => setModal(true)}>
          <Plus size={16} /> Create draft
        </button>
      </Heading>
      <div className="overview-banner">
        <div>
          <ShieldAlert size={22} />
          <div>
            <strong>
              Approval is explicit. Supplier communication is manual.
            </strong>
            <p>
              Drafting does not commit spending. Approval records a human
              decision; this demo never sends orders.
            </p>
          </div>
        </div>
      </div>
      <Notice loading={loading} error={error} />
      <Panel title="Purchase orders" subtitle="Every status change is audited">
        <Table
          rows={rows}
          onRow={setDetail}
          columns={[
            {
              key: "id",
              label: "Order",
              render: (r) => `PO-${String(r.id).padStart(4, "0")}`,
            },
            {
              key: "supplier_id",
              label: "Supplier",
              render: (r) =>
                suppliers.find((s) => s.id === r.supplier_id)?.name,
            },
            { key: "total", label: "Total", render: (r) => money(r.total) },
            { key: "expected_date", label: "Expected receipt" },
            {
              key: "status",
              label: "Status",
              render: (r) => <Status value={r.status} />,
            },
            {
              key: "action",
              label: "Decision",
              render: (r) =>
                r.status === "draft" ? (
                  <div className="inline-actions">
                    <button
                      className="text-button"
                      onClick={() => setDecision({ row: r, action: "approve" })}
                    >
                      Approve
                    </button>
                    <button
                      className="text-button danger-text"
                      onClick={() => setDecision({ row: r, action: "reject" })}
                    >
                      Reject
                    </button>
                  </div>
                ) : (
                  r.approved_by || "—"
                ),
            },
          ]}
        />
      </Panel>
      {modal && (
        <Modal
          title="Prepare purchase order draft"
          onClose={() => setModal(false)}
        >
          <DataForm
            fields={[
              {
                name: "supplier_id",
                label: "Supplier",
                type: "number",
                options: suppliers.map((s) => ({ value: s.id, label: s.name })),
              },
              {
                name: "product_id",
                label: "Product",
                type: "number",
                options: productOptions(products),
              },
              {
                name: "quantity",
                label: "Quantity",
                type: "number",
                value: 100,
                min: 1,
              },
            ]}
            submit="Save draft"
            onSubmit={async (d) => {
              await api.post("/purchase-orders", {
                supplier_id: d.supplier_id,
                items: [{ product_id: d.product_id, quantity: d.quantity }],
              });
              setModal(false);
              setRefresh((x) => x + 1);
            }}
          >
            <p className="muted">
              Server pricing comes from the supplier catalog. Minimum order
              quantities are enforced.
            </p>
          </DataForm>
        </Modal>
      )}
      {decision && (
        <Modal
          title={`${decision.action === "approve" ? "Approve" : "Reject"} PO-${decision.row.id} · ${money(decision.row.total)}`}
          onClose={() => setDecision(null)}
        >
          <DataForm
            fields={[
              {
                name: "reason",
                label: "Decision reason (at least 5 characters)",
              },
            ]}
            submit={`Confirm ${decision.action}`}
            onSubmit={async (d) => {
              await api.post(
                `/purchase-orders/${decision.row.id}/${decision.action}`,
                d,
              );
              setDecision(null);
              setRefresh((x) => x + 1);
            }}
          >
            <p className="muted">
              Requires a manager or administrator. Your identity and reason are
              preserved in the audit trail.
            </p>
          </DataForm>
        </Modal>
      )}
      {detail && (
        <Modal title={`Order #${detail.id}`} onClose={() => setDetail(null)}>
          <OrderDetail id={detail.id} />
        </Modal>
      )}
    </>
  );
}
function OrderDetail({ id }: { id: number }) {
  const { data, loading, error } = useData<Row | null>(
    `/purchase-orders/${id}`,
    null,
  );
  return (
    <>
      <Notice loading={loading} error={error} />
      <Evidence value={data} />
    </>
  );
}
