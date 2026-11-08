import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { I18nProvider } from "@/lib/i18n";
import { PwaProvider } from "@/lib/pwa";
import { NavBar } from "@/components/NavBar";

export const metadata: Metadata = {
  title: "Francessca",
  description: "Prepare for speaking with a qualified lawyer. Not legal advice.",
  // Installable: home screen on a phone, a windowed app on a computer.
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icons/icon-192.png", apple: "/icons/icon-192.png" },
  appleWebApp: { capable: true, title: "Francessca", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: "#3b5bdb",
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
              {children}
            </PwaProvider>
          </I18nProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
