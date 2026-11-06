import {
  ArrowUpRight,
  LoaderCircle,
  PackageOpen,
  Search,
  X,
} from "lucide-react";
import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { api, errorText } from "./api";
export type Row = Record<string, any>;
export function useData<T>(url: string, initial: T, refresh = 0) {
  const [data, setData] = useState<T>(initial);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const empty = useRef(initial);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setData(empty.current);
    setError("");
    api
      .get(url)
      .then((r) => {
        if (active) setData(r.data);
      })
      .catch((e) => {
        if (active) setError(errorText(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [url, refresh]);
  return { data, loading, error, setData };
}
export function Status({ value }: { value: string }) {
  return (
    <span
      className={`badge ${["low", "high", "open", "failed", "quarantined", "delayed", "critical"].includes(value) ? "danger" : ["healthy", "completed", "approved", "available"].includes(value) ? "success" : "neutral"}`}
    >
      <i />
      {value.replaceAll("-", " ")}
    </span>
  );
}
export function Notice({
  error,
  loading,
}: {
  error?: string;
  loading?: boolean;
}) {
  return error ? (
    <div className="notice error" role="alert">
      {error}
    </div>
  ) : loading ? (
    <div className="notice" role="status">
      <LoaderCircle size={16} className="spin" /> Loading current records…
    </div>
  ) : null;
}
export function Panel({
  title,
  subtitle,
  actions,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}
export function Metric({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: ReactNode;
  note: string;
  icon?: ReactNode;
}) {
  return (
    <div className="metric">
      <div className="metric-top">
        {label}
        <span>{icon || <ArrowUpRight size={17} />}</span>
      </div>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}
export function Table({
  rows,
  columns,
  onRow,
}: {
  rows: Row[];
  columns: { key: string; label: string; render?: (r: Row) => ReactNode }[];
  onRow?: (r: Row) => void;
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={r.id || r.product_id || i}
              className={onRow ? "clickable" : ""}
            >
              {columns.map((c, j) => (
                <td key={c.key}>
                  {onRow && j === 0 ? (
                    <button className="text-button" onClick={() => onRow(r)}>
                      {c.render ? c.render(r) : String(r[c.key] ?? "—")}
                    </button>
                  ) : c.render ? (
                    c.render(r)
                  ) : (
                    String(r[c.key] ?? "—")
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && (
        <div className="empty">
          <PackageOpen size={28} />
          <strong>No records yet</strong>
          <span>
            Records appear here when data is added or an analysis runs.
          </span>
        </div>
      )}
    </div>
  );
}
export function SearchBox({
  value,
  onChange,
  placeholder = "Search products…",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="search">
      <Search size={17} />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
      />
    </label>
  );
}
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    function close(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2>{title}</h2>
          <button
            className="icon-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
export type Field = {
  name: string;
  label: string;
  type?: string;
  value?: string | number;
  options?: { value: string | number; label: string }[];
  required?: boolean;
  min?: number;
  max?: number;
};
export function DataForm({
  fields,
  onSubmit,
  submit = "Save",
  children,
}: {
  fields: Field[];
  onSubmit: (data: Row) => Promise<void>;
  submit?: string;
  children?: ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function send(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const data: Row = {};
    fields.forEach((f) => {
      const value = form.get(f.name);
      data[f.name] =
        f.type === "number"
          ? Number(value)
          : f.type === "boolean"
            ? value === "true"
            : String(value ?? "");
    });
    setBusy(true);
    setError("");
    try {
      await onSubmit(data);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={send}>
      <div className="form-grid">
        {fields.map((f) => (
          <label key={f.name}>
            {f.label}
            {f.options ? (
              <select
                name={f.name}
                defaultValue={f.value}
                required={f.required !== false}
              >
                {f.options.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                name={f.name}
                type={f.type || "text"}
                defaultValue={f.value}
                required={f.required !== false}
                min={f.min}
                max={f.max}
                step={f.type === "number" ? "any" : undefined}
              />
            )}
          </label>
        ))}
      </div>
      {children}
      <Notice error={error} />
      <button className="primary" disabled={busy}>
        {busy ? "Working…" : submit}
      </button>
    </form>
  );
}
export function Evidence({ value }: { value: unknown }) {
  return <pre className="evidence">{JSON.stringify(value, null, 2)}</pre>;
}
