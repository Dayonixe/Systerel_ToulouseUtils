export function registerServiceWorker(): void {
  if (!import.meta.env.PROD || !("serviceWorker" in navigator)) {
    return;
  }

  window.addEventListener("load", () => {
    const appBaseUrl = new URL(import.meta.env.BASE_URL, window.location.href);
    const serviceWorkerUrl = new URL("sw.js", appBaseUrl);

    void navigator.serviceWorker
      .register(serviceWorkerUrl, { scope: appBaseUrl.href })
      .catch((error: unknown) => {
        console.error("Impossible d’enregistrer le service worker.", error);
      });
  });
}
