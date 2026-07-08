import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { I18nProvider } from "@/lib/i18n";
import { NavBar } from "@/components/NavBar";

export const metadata: Metadata = {
  title: "Francessca",
  description: "Prepare for speaking with a qualified lawyer. Not legal advice.",
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
            <NavBar />
            {children}
          </I18nProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
