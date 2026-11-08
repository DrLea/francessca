"use client";

// Install-as-an-app support. The site is a PWA: on a phone it installs to
// the home screen, on a computer it becomes a windowed desktop app. This
// module registers the service worker and exposes the browser's install
// prompt so any page can put an "Install" button where it makes sense.

import { createContext, useCallback, useContext, useEffect, useState } from "react";

/** Chrome/Edge/Android fire this instead of showing their own banner. */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

interface PwaState {
  /** The browser offered an install prompt we can trigger. */
  canInstall: boolean;
  /** Already running as an installed app. */
  installed: boolean;
  /** iOS Safari has no prompt: the user adds it from the Share menu. */
  isIos: boolean;
  install: () => Promise<boolean>;
}

const PwaContext = createContext<PwaState>({
  canInstall: false,
  installed: false,
  isIos: false,
  install: async () => false,
});

export function PwaProvider({ children }: { children: React.ReactNode }) {
  const [prompt, setPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [isIos, setIsIos] = useState(false);

  useEffect(() => {
    // Production only: in `next dev` chunk URLs are not content-hashed, so
    // the worker's cache would keep serving stale code.
    if (process.env.NODE_ENV === "production" && "serviceWorker" in navigator) {
      // Best effort: without it the site simply works as a normal website.
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true;
    setInstalled(standalone);
    setIsIos(/iphone|ipad|ipod/i.test(navigator.userAgent) && !standalone);

    const onPrompt = (e: Event) => {
      e.preventDefault();
      setPrompt(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setPrompt(null);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  const install = useCallback(async () => {
    if (!prompt) return false;
    await prompt.prompt();
    const { outcome } = await prompt.userChoice;
    setPrompt(null); // a prompt can only be used once
    return outcome === "accepted";
  }, [prompt]);

  return (
    <PwaContext.Provider value={{ canInstall: !!prompt, installed, isIos, install }}>
      {children}
    </PwaContext.Provider>
  );
}

export function usePwa(): PwaState {
  return useContext(PwaContext);
}
