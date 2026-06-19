import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("d31337m3_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default client;
