import "@xyflow/react/dist/style.css";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Metric, Notice, Panel, Table, useData, type Row } from "../components";
import { Heading, number } from "./shared";
export function Risks() {
  const { data: d, loading, error } = useData<Row>("/analytics/dashboard", {});
  const { data: shipments } = useData<Row[]>("/cold-chain/shipments", []);
  const { data: warehouses } = useData<Row[]>("/warehouses", []);
  const { data: batches } = useData<Row[]>("/inventory/batches", []);
  const rows: Row[] = (d.risk_products || []).map((r: Row) => ({
    ...r,
    risks: [
      r.status === "low"
        ? "Stockout"
        : r.status === "excess"
          ? "Overstock"
          : "",
      r.near_expiry ? "Near expiry" : "",
      r.quarantined ? "Quality hold" : "",
    ]
      .filter(Boolean)
      .join(" · "),
  }));
  return (
    <>
      <Heading
        tag="INTELLIGENCE / RISK ASSESSMENT"
        title="Know where to look next"
        description="Evidence-backed operational indicators. Product disposition remains with authorized quality staff."
      />
      <Notice loading={loading} error={error} />
      <div className="metrics">
        <Metric
          label="Stockout indicators"
          value={d.low_stock}
          note="Products below reorder threshold"
        />
        <Metric
          label="Expiry exposure"
          value={number(d.near_expiry)}
          note="Available units within 90 days of expiry"
        />
        <Metric
          label="Quality holds"
          value={number(d.quarantined)}
          note="Units excluded from usable inventory"
        />
        <Metric
          label="Delayed shipments"
          value={shipments.filter((s) => s.status === "delayed").length}
          note="Synthetic transport status"
        />
      </div>
      <Panel
        title="Product risk register"
        subtitle="Derived from product thresholds and batch records"
      >
        <Table
          rows={rows}
          columns={[
            { key: "name", label: "Product" },
            { key: "risks", label: "Risk factors" },
            { key: "available", label: "Usable" },
            { key: "near_expiry", label: "Near expiry" },
            { key: "quarantined", label: "Quality hold" },
            {
              key: "action",
              label: "Supporting records",
              render: (r) => (
                <Link className="text-button" to="/inventory">
                  Product #{r.product_id} / batches <ArrowRight size={14} />
                </Link>
              ),
            },
          ]}
        />
      </Panel>
      <Panel
        title="Warehouse capacity exposure"
        subtitle="Total physical stock, including unavailable stock"
      >
        <Table
          rows={warehouses.map((w) => ({
            ...w,
            used: batches
              .filter((b) => b.warehouse_id === w.id)
              .reduce((s, b) => s + b.quantity, 0),
          }))}
          columns={[
            { key: "name", label: "Warehouse" },
            { key: "used", label: "Physical units" },
            { key: "capacity", label: "Capacity" },
            {
              key: "utilization",
              label: "Utilization",
              render: (r) => `${((r.used / r.capacity) * 100).toFixed(1)}%`,
            },
          ]}
        />
      </Panel>
    </>
  );
}
