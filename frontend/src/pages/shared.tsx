import "@xyflow/react/dist/style.css";
import { Check } from "lucide-react";
import { useState } from "react";
import { errorText } from "../api";
import { Notice, type Field, type Row } from "../components";

const number = (n: number) =>
  new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(n || 0);
const money = (n: number) => `₹${number(n)}`;
const productOptions = (products: Row[]) =>
  products.map((p) => ({ value: p.id, label: p.name }));
function Heading({
  tag,
  title,
  description,
  children,
}: {
  tag: string;
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{tag}</span>
        <h1>
          {title}
          <span className="title-dot">.</span>
        </h1>
        <p>{description}</p>
      </div>
      <div className="heading-actions">{children}</div>
    </div>
  );
}
function ProductSelect({
  products,
  value,
  onChange,
}: {
  products: Row[];
  value: number;
  onChange: (id: number) => void;
}) {
  return (
    <select
      aria-label="Select product"
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
    >
      {products.map((p) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </select>
  );
}
function useAction() {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  async function run(
    action: () => Promise<void>,
    success = "Completed successfully",
  ) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await action();
      setMessage(success);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, message, run };
}
function Feedback({ action }: { action: ReturnType<typeof useAction> }) {
  return (
    <>
      <Notice error={action.error} />
      {action.message && (
        <div className="notice success" role="status">
          <Check size={16} />
          {action.message}
        </div>
      )}
    </>
  );
}

const productFields: Field[] = [
  { name: "name", label: "Product name" },
  { name: "generic_name", label: "Generic name" },
  { name: "category", label: "Category", value: "General" },
  { name: "strength", label: "Strength", value: "10 mg" },
  { name: "dosage_form", label: "Dosage form", value: "Tablet" },
  { name: "manufacturer", label: "Manufacturer" },
  {
    name: "temperature_sensitive",
    label: "Cold-storage capacity required",
    type: "boolean",
    value: "false",
    options: [
      { value: "false", label: "No" },
      { value: "true", label: "Yes" },
    ],
  },
  {
    name: "reorder_point",
    label: "Reorder point (units)",
    type: "number",
    value: 300,
    min: 0,
  },
  {
    name: "safety_stock",
    label: "Configured safety stock (units)",
    type: "number",
    value: 100,
    min: 0,
  },
  {
    name: "temp_min",
    label: "Minimum temperature °C",
    type: "number",
    value: 15,
  },
  {
    name: "temp_max",
    label: "Maximum temperature °C",
    type: "number",
    value: 25,
  },
  {
    name: "min_stock",
    label: "Minimum stock",
    type: "number",
    value: 100,
    min: 0,
  },
  {
    name: "max_stock",
    label: "Maximum stock",
    type: "number",
    value: 3000,
    min: 1,
  },
  {
    name: "unit_cost",
    label: "Unit cost ₹",
    type: "number",
    value: 10,
    min: 0,
  },
  {
    name: "criticality",
    label: "Criticality",
    options: ["standard", "high", "critical"].map((x) => ({
      value: x,
      label: x,
    })),
  },
];

export {
  Feedback,
  Heading,
  money,
  number,
  productFields,
  productOptions,
  ProductSelect,
  useAction,
};
