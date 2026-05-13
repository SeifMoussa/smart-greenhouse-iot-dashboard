import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useTheme } from "../src/hooks/useTheme";

describe("useTheme", () => {
  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("reads the stored theme on mount", () => {
    localStorage.setItem("greenhouse:theme", "dark");
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("persists changes to localStorage", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("dark"));
    expect(localStorage.getItem("greenhouse:theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("toggle flips between light and dark", () => {
    localStorage.setItem("greenhouse:theme", "light");
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
    act(() => result.current.toggle());
    expect(result.current.theme).toBe("dark");
    act(() => result.current.toggle());
    expect(result.current.theme).toBe("light");
  });

  it("removes the dark class when set to light", () => {
    localStorage.setItem("greenhouse:theme", "dark");
    const { result } = renderHook(() => useTheme());
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    act(() => result.current.setTheme("light"));
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
