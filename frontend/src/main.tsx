import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./index.css";

// Apply persisted theme before React mounts to avoid a flash of light theme.
try {
  const stored = localStorage.getItem("greenhouse:theme");
  const prefersDark =
    window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  if (stored === "dark" || (stored === null && prefersDark)) {
    document.documentElement.classList.add("dark");
  }
} catch {
  // ignore
}

const root = document.getElementById("root");
if (!root) {
  throw new Error("Root element not found");
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
