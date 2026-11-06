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
import App from "./App";
import { DataForm, Status, Table } from "./components";
import { parseCSV } from "./csv";
vi.mock("./pages", () =>
  Object.fromEntries(
    [
      "Dashboard",
      "Inventory",
      "Forecast",
      "RLWorkspace",
      "ColdChain",
      "Suppliers",
      "Orders",
      "Agents",
      "Risks",
      "Reports",
      "SettingsPage",
    ].map((name) => [name, () => <div>{name} page</div>]),
  ),
);
afterEach(() => {
  cleanup();
  sessionStorage.clear();
});
describe("operational UI", () => {
  it("displays explicit quarantine status", () => {
    render(<Status value="quarantined" />);
    expect(screen.getByText("quarantined")).toBeTruthy();
  });
  it("shows empty state instead of fabricated records", () => {
    render(<Table rows={[]} columns={[{ key: "name", label: "Product" }]} />);
    expect(screen.getByText("No records yet")).toBeTruthy();
  });
  it("submits numeric quantities as numbers", async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    render(
      <DataForm
        fields={[
          { name: "quantity", label: "Quantity", type: "number", value: 50 },
        ]}
        onSubmit={submit}
      />,
    );
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => expect(submit).toHaveBeenCalledWith({ quantity: 50 }));
  });
  it("surfaces backend failures and permits retry", async () => {
    render(
      <DataForm
        fields={[{ name: "reason", label: "Reason", value: "QA review" }]}
        onSubmit={async () => {
          throw new Error("Role denied");
        }}
      />,
    );
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toContain("Role denied"),
    );
    expect((screen.getByText("Save") as HTMLButtonElement).disabled).toBe(
      false,
    );
  });
  it("requires login before displaying operations", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("button", { name: "Enter workspace" }),
    ).toBeTruthy();
    expect(screen.queryByText("Dashboard page")).toBeNull();
  });
  it.each([
    ["/", "Dashboard"],
    ["/inventory", "Inventory"],
    ["/forecast", "Forecast"],
    ["/optimization", "RLWorkspace"],
    ["/cold-chain", "ColdChain"],
    ["/suppliers", "Suppliers"],
    ["/orders", "Orders"],
    ["/agents", "Agents"],
    ["/risks", "Risks"],
    ["/reports", "Reports"],
    ["/settings", "SettingsPage"],
  ])("routes %s to its page", (url, name) => {
    sessionStorage.setItem("token", "test");
    sessionStorage.setItem(
      "user",
      JSON.stringify({ username: "viewer", role: "viewer" }),
    );
    render(
      <MemoryRouter initialEntries={[url]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText(`${name} page`)).toBeTruthy();
  });
  it("parses CSV quotes, commas, booleans and numbers", () => {
    expect(
      parseCSV(
        'name,unit_cost,temperature_sensitive\r\n"Medicine, synthetic",20,true\r\n',
      ),
    ).toEqual([
      {
        name: "Medicine, synthetic",
        unit_cost: 20,
        temperature_sensitive: true,
      },
    ]);
  });
});
