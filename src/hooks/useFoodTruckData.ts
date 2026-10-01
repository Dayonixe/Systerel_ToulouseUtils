import { useCallback, useEffect, useState } from "react";
import type { FoodTruckFeed } from "../domain/foodTrucks";
import { loadFoodTruckData } from "../services/foodTrucks";

type FoodTruckDataState =
  | { status: "loading"; data: null; error: null }
  | { status: "ready"; data: FoodTruckFeed; error: null }
  | { status: "error"; data: null; error: string };

export function useFoodTruckData() {
  const [state, setState] = useState<FoodTruckDataState>({
    status: "loading",
    data: null,
    error: null,
  });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading", data: null, error: null });

    loadFoodTruckData(controller.signal)
      .then((data) => setState({ status: "ready", data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          status: "error",
          data: null,
          error:
            error instanceof Error
              ? error.message
              : "Une erreur inattendue est survenue.",
        });
      });

    return () => controller.abort();
  }, [reloadKey]);

  const reload = useCallback(() => setReloadKey((value) => value + 1), []);
  return { ...state, reload };
}
