import axios from "axios";

const API_BASE = `${import.meta.env.VITE_API_URL || ""}/api`;

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
  get: (topN = 10) => api.get(`/insights?topN=${topN}`, { timeout: 60000 })
};

export default api;
