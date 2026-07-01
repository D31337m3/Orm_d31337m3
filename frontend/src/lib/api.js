import axios from "axios";

const runtimeBase = typeof window !== "undefined" ? window.location.origin : "";
const BACKEND_URL = runtimeBase.replace(/\/$/, "");
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

const client = axios.create({ baseURL: API });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("d31337m3_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const detail = error?.response?.data?.detail;
    const code = typeof detail === "object" ? detail?.code : null;

    if (status === 402 && code === "TRIAL_EXPIRED" && typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("d31337m3:trial-expired", { detail }));
    }

    return Promise.reject(error);
  }
);

export default client;
