import axios from "axios";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 120000,
});
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e.response?.status === 401) {
      sessionStorage.removeItem("token");
      window.dispatchEvent(new Event("session-expired"));
    }
    return Promise.reject(e);
  },
);
export function errorText(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const detail = e.response?.data?.detail;
    return typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((x) => x.msg).join("; ")
        : e.message;
  }
  return String(e);
}
export async function download(kind: string, format: string) {
  const r = await api.get(`/export/${kind}?format=${format}`, {
    responseType: "blob",
  });
  const u = URL.createObjectURL(r.data);
  const a = document.createElement("a");
  a.href = u;
  a.download = `pharmachain-synthetic-${kind}.${format}`;
  a.click();
  URL.revokeObjectURL(u);
}
