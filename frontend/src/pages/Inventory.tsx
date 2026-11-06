import "@xyflow/react/dist/style.css";
import { Download, Package, Plus } from "lucide-react";
import { useState } from "react";
import { api, download } from "../api";
import {
  DataForm,
  Metric,
  Modal,
  Notice,
  Panel,
  SearchBox,
  Status,
  Table,
  useData,
  type Field,
  type Row,
} from "../components";
import {
  Feedback,
  Heading,
  number,
  productFields,
  productOptions,
  useAction,
} from "./shared";
export function Inventory() {
  const [refresh, setRefresh] = useState(0),
    [q, setQ] = useState(""),
    [filter, setFilter] = useState("all"),
    [modal, setModal] = useState(""),
    [detail, setDetail] = useState<Row | null>(null);
  const {
    data: rows,
    loading,
    error,
  } = useData<Row[]>("/inventory", [], refresh);
  const { data: products } = useData<Row[]>("/products", [], refresh);
  const { data: wh } = useData<Row[]>("/warehouses", []);
  const { data: batches } = useData<Row[]>("/inventory/batches", [], refresh);
  const a = useAction();
  const done = () => {
    setModal("");
    setRefresh((x) => x + 1);
  };
  const stockFields: Field[] = [
    {
      name: "product_id",
      label: "Product",
      type: "number",
      options: productOptions(products),
    },
    {
      name: "warehouse_id",
      label: "Warehouse",
      type: "number",
      options: wh.map((w) => ({ value: w.id, label: w.name })),
    },
    { name: "quantity", label: "Quantity", type: "number", value: 100, min: 1 },
  ];
  return (
    <>
      <Heading
        tag="OPERATIONS / INVENTORY"
        title="Every batch accounted for"
        description="Manage stock, trace batches, and allocate by first expiry."
      >
        <button className="secondary" onClick={() => setModal("stock-out")}>
          Stock out / transfer
        </button>
        <button className="secondary" onClick={() => setModal("stock-in")}>
          <Plus size={16} /> Receive stock
        </button>
        <button className="primary" onClick={() => setModal("product")}>
          <Plus size={16} /> Add product
        </button>
      </Heading>
      <div className="metrics">
        <Metric
          label="Registered products"
          value={rows.length}
          note="Synthetic pharmaceutical catalog"
        />
        <Metric
          label="Usable units"
          value={number(rows.reduce((s, r) => s + r.available, 0))}
          note="Reserved and unavailable stock excluded"
        />
        <Metric
          label="Near expiry"
          value={number(rows.reduce((s, r) => s + r.near_expiry, 0))}
          note="Usable units within configured threshold"
        />
        <Metric
          label="Quarantined"
          value={number(rows.reduce((s, r) => s + r.quarantined, 0))}
          note="Authorized quality review required"
        />
      </div>
      <Panel
        title="Product inventory"
        subtitle="Select a product to inspect its batches"
        actions={
          <button
            className="text-button"
            onClick={() =>
              a.run(() => download("inventory", "csv"), "CSV downloaded")
            }
          >
            <Download size={16} /> Export CSV
          </button>
        }
      >
        <div className="table-toolbar">
          <div className="tabs">
            {["all", "healthy", "low", "excess"].map((f) => (
              <button
                className={filter === f ? "selected" : ""}
                key={f}
                onClick={() => setFilter(f)}
              >
                {f === "all"
                  ? "All products"
                  : f === "low"
                    ? "Low stock"
                    : f === "excess"
                      ? "Overstock"
                      : "Healthy"}
              </button>
            ))}
          </div>
          <SearchBox value={q} onChange={setQ} />
        </div>
        <Notice loading={loading} error={error} />
        <Feedback action={a} />
        <Table
          onRow={setDetail}
          rows={rows.filter(
            (r) =>
              r.name.toLowerCase().includes(q.toLowerCase()) &&
              (filter === "all" || r.status === filter),
          )}
          columns={[
            {
              key: "name",
              label: "Product",
              render: (r) => (
                <div className="product-cell">
                  <span className="product-icon">
                    <Package size={17} />
                  </span>
                  <span>
                    <strong>{r.name}</strong>
                    <small>
                      {r.category} · #{r.product_id.toString().padStart(3, "0")}
                    </small>
                  </span>
                </div>
              ),
            },
            {
              key: "available",
              label: "Usable stock",
              render: (r) => (
                <>
                  <strong>{number(r.available)}</strong>
                  <div className="stock-track">
                    <i
                      style={{
                        width: `${Math.min(100, (r.available / r.max_stock) * 100)}%`,
                        background: r.status === "low" ? "#d59a58" : "#479583",
                      }}
                    />
                  </div>
                </>
              ),
            },
            { key: "reserved", label: "Reserved" },
            { key: "quarantined", label: "Quarantined" },
            { key: "near_expiry", label: "Near expiry" },
            {
              key: "status",
              label: "Status",
              render: (r) => <Status value={r.status} />,
            },
          ]}
        />
      </Panel>
      {detail && (
        <Modal
          title={`${detail.name} · batch traceability`}
          onClose={() => setDetail(null)}
        >
          <Table
            rows={batches.filter((b) => b.product_id === detail.product_id)}
            columns={[
              { key: "number", label: "Batch" },
              { key: "warehouse_id", label: "Warehouse" },
              { key: "quantity", label: "Quantity" },
              { key: "reserved", label: "Reserved" },
              { key: "expiry_date", label: "Expiry" },
              {
                key: "status",
                label: "Status",
                render: (r) => <Status value={r.status} />,
              },
            ]}
          />
          <p className="muted">
            FEFO applies only to available, unexpired, unreserved stock.
            Quarantine cannot be released by this application.
          </p>
        </Modal>
      )}
      {modal && (
        <Modal
          title={
            modal === "product"
              ? "Register pharmaceutical product"
              : modal === "stock-in"
                ? "Receive a new batch"
                : "Allocate or transfer stock"
          }
          onClose={() => setModal("")}
        >
          <DataForm
            fields={
              modal === "product"
                ? productFields
                : modal === "stock-in"
                  ? [
                      ...stockFields,
                      { name: "number", label: "Batch number" },
                      {
                        name: "manufacturing_date",
                        label: "Manufacturing date",
                        type: "date",
                      },
                      {
                        name: "expiry_date",
                        label: "Expiry date",
                        type: "date",
                      },
                    ]
                  : [
                      ...stockFields,
                      { name: "reference", label: "Transaction reference" },
                      {
                        name: "destination_id",
                        label: "Destination (0 = stock out)",
                        type: "number",
                        value: 0,
                        min: 0,
                      },
                    ]
            }
            onSubmit={async (data) => {
              if (modal === "product") await api.post("/products", data);
              else if (modal === "stock-in")
                await api.post("/inventory/stock-in", data);
              else {
                const { destination_id, ...rest } = data;
                await api.post(
                  destination_id
                    ? "/inventory/transfer"
                    : "/inventory/stock-out",
                  destination_id ? data : rest,
                );
              }
              done();
            }}
            submit={
              modal === "product" ? "Register product" : "Record transaction"
            }
          >
            <p className="muted">
              All changes are validated and audited on the server.
            </p>
          </DataForm>
        </Modal>
      )}
    </>
  );
}
