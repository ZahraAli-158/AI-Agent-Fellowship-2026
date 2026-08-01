import { useEffect, useRef, useState } from "react";

/**
 * Polls an async fetcher on an interval and exposes { data, error, loading }.
 * Used throughout the dashboard to keep Status/Tasks/Evidence/Trace panels
 * live without the caller managing setInterval/cleanup itself.
 *
 * Pass `enabled=false` to pause polling (e.g. no active run yet, or the run
 * has already finished and there's nothing left to change).
 */
export function usePolling(fetcher, deps, { intervalMs = 1500, enabled = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);

    const tick = async () => {
      try {
        const result = await fetcherRef.current();
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs, ...deps]);

  return { data, error, loading };
}
