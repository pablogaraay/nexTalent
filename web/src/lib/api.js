import axios from "axios";

const runtimeApiUrl = window.__CONFIG__?.VITE_API_URL || "";
const viteApiUrl = import.meta.env.VITE_API_URL || "";
const apiBaseUrl = runtimeApiUrl || viteApiUrl;
const API_BASE = `${apiBaseUrl}/api`;

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: false,
  headers: { "Content-Type": "application/json" }
});

export const jobsAPI = {
  search: (formData) =>
    api.post("/search", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000
    })
};

export const insightsAPI = {
  get: (params = {}) =>
    api.get("/insights", {
      params,
      timeout: 60000
    })
};

export default api;
