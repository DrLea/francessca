"use client";

import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { usePwa } from "@/lib/pwa";
import { Button } from "@/components/ui";

/** "Get the app" for clients: install to the phone's home screen, and a
 *  pointer to the offline assistant that runs a small model on the device. */
export function InstallApp({ showOfflineLink = true }: { showOfflineLink?: boolean }) {
  const { t } = useI18n();
  const { canInstall, installed, isIos, install } = usePwa();

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        {installed ? (
          <span className="rounded-full bg-green-50 px-3 py-1 text-sm font-medium text-green-700">
            ✓ {t("app.installed")}
          </span>
        ) : canInstall ? (
          <Button onClick={() => void install()}>{t("app.install")}</Button>
        ) : null}
        {showOfflineLink && (
          <Link href="/offline">
            <Button variant="secondary">{t("app.openOffline")}</Button>
          </Link>
        )}
      </div>
      {!installed && !canInstall && (
        <p className="max-w-xl text-xs leading-relaxed text-slate-500">
          {isIos ? t("app.iosHint") : t("app.manualHint")}
        </p>
      )}
    </div>
  );
}
