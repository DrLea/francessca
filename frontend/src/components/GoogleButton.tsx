"use client";

import Script from "next/script";
import { useEffect, useRef } from "react";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

interface Props {
  onCredential: (idToken: string) => void;
}

/**
 * Renders the Google Identity Services button. The returned ID token is sent
 * to the backend (`POST /auth/google`) which verifies it server-side.
 * Renders nothing if NEXT_PUBLIC_GOOGLE_CLIENT_ID is not configured.
 */
export function GoogleButton({ onCredential }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!CLIENT_ID) return;
    const g = (window as unknown as { google?: any }).google;
    if (!g || !ref.current) return;
    g.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: (resp: { credential: string }) => onCredential(resp.credential),
    });
    g.accounts.id.renderButton(ref.current, {
      theme: "outline",
      size: "large",
      width: 320,
    });
  }, [onCredential]);

  if (!CLIENT_ID) return null;

  return (
    <>
      <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
      <div ref={ref} />
    </>
  );
}
