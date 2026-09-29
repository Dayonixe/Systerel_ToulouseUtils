import { useCallback, useEffect, useState } from "react";
import type { PromotionData } from "../domain/offers";
import { loadPromotionData } from "../services/offers";

type PromotionDataState =
  | { status: "loading"; data: null; error: null }
  | { status: "ready"; data: PromotionData; error: null }
  | { status: "error"; data: null; error: string };

export function usePromotionData() {
  const [state, setState] = useState<PromotionDataState>({
    status: "loading",
    data: null,
    error: null,
  });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading", data: null, error: null });

    loadPromotionData(controller.signal)
      .then((data) => setState({ status: "ready", data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          status: "error",
          data: null,
          error: error instanceof Error ? error.message : "Une erreur inattendue est survenue.",
        });
      });

    return () => controller.abort();
  }, [reloadKey]);

  const reload = useCallback(() => setReloadKey((value) => value + 1), []);
  return { ...state, reload };
}
