import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach } from "vitest";
import { cleanup } from "@testing-library/react";

beforeEach(() => {
  // Clean DOM between tests so React Testing Library doesn't pile up roots.
});

afterEach(() => {
  cleanup();
  localStorage.clear();
});
