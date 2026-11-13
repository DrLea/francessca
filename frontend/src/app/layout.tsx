import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { I18nProvider } from "@/lib/i18n";
import { PwaProvider } from "@/lib/pwa";
import { NavBar } from "@/components/NavBar";
import { ConsentDialog } from "@/components/ConsentDialog";

export const metadata: Metadata = {
  metadataBase: new URL("https://francesca.dpdns.org"),
  title: "Francesca",
  description: "Prepare for speaking with a qualified lawyer. Not legal advice.",
  // Installable: home screen on a phone, a windowed app on a computer.
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icons/favicon-32.png", type: "image/png", sizes: "32x32" },
      { url: "/icons/icon-192.png", type: "image/png", sizes: "192x192" },
    ],
    apple: "/icons/apple-touch-icon.png",
  },
  openGraph: {
    title: "Francesca",
    description: "Prepare for speaking with a qualified lawyer. Not legal advice.",
    url: "https://francesca.dpdns.org",
    siteName: "Francesca",
    images: [{ url: "/brand/og.png", width: 1200, height: 630, alt: "Francesca" }],
    type: "website",
  },
  twitter: { card: "summary_large_image", images: ["/brand/og.png"] },
  appleWebApp: { capable: true, title: "Francesca", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: "#0b192e",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <AuthProvider>
          <I18nProvider>
            <PwaProvider>
              <NavBar />
              <ConsentDialog />
              {children}
            </PwaProvider>
          </I18nProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
