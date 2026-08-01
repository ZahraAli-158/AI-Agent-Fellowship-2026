import { createContext, useCallback, useContext, useEffect, useState } from "react";

const ThemeContext = createContext(null);
const STORAGE_KEY = "mardi-theme"; // "light" | "dark" | "system"

function resolveSystemPref() {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(() => localStorage.getItem(STORAGE_KEY) || "system");
  const [resolved, setResolved] = useState(() => (mode === "system" ? resolveSystemPref() : mode));

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode);
    const effective = mode === "system" ? resolveSystemPref() : mode;
    setResolved(effective);
    document.documentElement.setAttribute("data-theme", effective);
  }, [mode]);

  useEffect(() => {
    if (mode !== "system") return undefined;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => {
      const effective = resolveSystemPref();
      setResolved(effective);
      document.documentElement.setAttribute("data-theme", effective);
    };
    mq.addEventListener("change", listener);
    return () => mq.removeEventListener("change", listener);
  }, [mode]);

  const cycle = useCallback(() => {
    setMode((m) => (m === "light" ? "dark" : m === "dark" ? "system" : "light"));
  }, []);

  return (
    <ThemeContext.Provider value={{ mode, resolved, setMode, cycle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
