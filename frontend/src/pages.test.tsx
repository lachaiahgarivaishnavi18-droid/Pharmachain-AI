// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
import {
  ColdChain,
  Dashboard,
  Forecast,
  Inventory,
  Orders,
  RLWorkspace,
} from "./pages";
vi.mock("./api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  download: vi.fn(),
  errorText: (e: unknown) => String(e),
}));
vi.mock("recharts", () => ({
  ResponsiveContainer: () => null,
  AreaChart: () => null,
  Area: () => null,
  LineChart: () => null,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  BarChart: () => null,
  Bar: () => null,
  ReferenceLine: () => null,
  Legend: () => null,
}));
vi.mock("@xyflow/react", () => ({
  ReactFlow: () => null,
  Background: () => null,
  Controls: () => null,
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
function setup(records: Record<string, unknown>) {
  vi.mocked(api.get).mockImplementation(async (url: any) => ({
    data: Object.prototype.hasOwnProperty.call(records, url)
      ? records[url]
      : url.includes("analytics/dashboard")
        ? {}
        : [],
  }));
  vi.mocked(api.post).mockResolvedValue({ data: {} });
}
describe("connected page interactions", () => {
  it("filters actual inventory and opens batch traceability", async () => {
    setup({
      "/inventory": [
        {
          product_id: 1,
          name: "Synthetic insulin",
          category: "Biologics",
          available: 20,
          reserved: 0,
          quarantined: 50,
          near_expiry: 0,
          status: "low",
          max_stock: 3000,
        },
      ],
      "/products": [{ id: 1, name: "Synthetic insulin" }],
      "/inventory/batches": [
        {
          id: 1,
          product_id: 1,
          number: "SYN-001",
          warehouse_id: 1,
          quantity: 50,
          reserved: 0,
          expiry_date: "2027-01-01",
          status: "quarantined",
        },
      ],
    });
    render(<Inventory />);
    fireEvent.click(await screen.findByText("Synthetic insulin"));
    expect(await screen.findByRole("dialog")).toBeTruthy();
    expect(screen.getByText("SYN-001")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Close dialog"));
    fireEvent.change(screen.getByLabelText("Search products…"), {
      target: { value: "absent" },
    });
    expect(await screen.findByText("No records yet")).toBeTruthy();
  });
  it("requires an explicit decision dialog before purchase approval", async () => {
    setup({
      "/purchase-orders": [
        {
          id: 7,
          supplier_id: 1,
          total: 100,
          status: "draft",
          expected_date: "2026-12-01",
        },
      ],
      "/suppliers": [{ id: 1, name: "Synthetic supplier" }],
    });
    render(<Orders />);
    fireEvent.click(await screen.findByText("Approve"));
    expect(api.post).not.toHaveBeenCalled();
    fireEvent.change(
      screen.getByLabelText("Decision reason (at least 5 characters)"),
      { target: { value: "Authorized synthetic test" } },
    );
    fireEvent.click(screen.getByText("Confirm approve"));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/purchase-orders/7/approve", {
        reason: "Authorized synthetic test",
      }),
    );
  });
  it("does not fabricate forecasts before an analysis", async () => {
    setup({
      "/forecast/1": null,
      "/products": [{ id: 1, name: "Synthetic insulin" }],
    });
    render(<Forecast />);
    expect(
      await screen.findByText("Generate your first forecast"),
    ).toBeTruthy();
    expect(api.post).not.toHaveBeenCalled();
  });
  it("computes recommendation only after user action", async () => {
    setup({
      "/products": [{ id: 1, name: "Synthetic insulin" }],
      "/rl/policy-performance": null,
    });
    render(<RLWorkspace />);
    fireEvent.click(await screen.findByText("Recommend"));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/rl/recommend", { product_id: 1 }),
    );
  });
  it("opens a quality investigation without releasing stock", async () => {
    setup({
      "/cold-chain/alerts": [
        {
          id: 3,
          message: "Temperature excursion; batch quarantined",
          status: "open",
        },
      ],
    });
    render(<ColdChain />);
    fireEvent.click(await screen.findByText("Investigate"));
    expect(await screen.findByText(/does not release, discard/)).toBeTruthy();
    expect(api.post).not.toHaveBeenCalled();
  });
  it("shows server-derived dashboard values", async () => {
    setup({
      "/analytics/dashboard": {
        products: 50,
        available_units: 1234,
        inventory_value: 10000,
        low_stock: 2,
        open_alerts: 1,
        quarantined: 4,
        pending_approvals: 0,
        risk_products: [],
        categories: [],
      },
    });
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    expect(await screen.findByText("1,234")).toBeTruthy();
    expect(screen.getByText("50 products across 5 warehouses")).toBeTruthy();
  });
});
