"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useAuth } from "@/lib/auth";
import {
  dictionaries,
  DEFAULT_LANG,
  isLangCode,
  LOCALE_TAGS,
  RTL_LANGS,
  type LangCode,
  type TranslationKey,
} from "@/lib/translations";

const STORAGE_KEY = "francessca_ui_lang";

type TFunction = (
  key: TranslationKey,
  vars?: Record<string, string | number>,
) => string;

interface I18nState {
  lang: LangCode;
  locale: string;
  dir: "ltr" | "rtl";
  setLang: (lang: LangCode) => void;
  t: TFunction;
}

const I18nContext = createContext<I18nState | undefined>(undefined);

function readStoredLang(): LangCode | null {
  if (typeof window === "undefined") return null;
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return isLangCode(stored) ? stored : null;
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [lang, setLangState] = useState<LangCode>(DEFAULT_LANG);

  // Pick up a language chosen on a previous visit (covers logged-out pages).
  useEffect(() => {
    const stored = readStoredLang();
    if (stored) setLangState(stored);
  }, []);

  // Once signed in, the account's saved preference is the source of truth.
  useEffect(() => {
    if (isLangCode(user?.language)) {
      setLangState(user.language);
    }
  }, [user?.language]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(STORAGE_KEY, lang);
    document.documentElement.lang = lang;
    document.documentElement.dir = RTL_LANGS.has(lang) ? "rtl" : "ltr";
  }, [lang]);

  const setLang = useCallback((next: LangCode) => {
    setLangState(next);
  }, []);

  const t = useMemo<TFunction>(() => {
    const dict = dictionaries[lang] ?? dictionaries[DEFAULT_LANG];
    const fallback = dictionaries[DEFAULT_LANG];
    return (key, vars) => {
      let str = dict[key] ?? fallback[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          str = str.split(`{{${k}}}`).join(String(v));
        }
      }
      return str;
    };
  }, [lang]);

  const value = useMemo<I18nState>(
    () => ({
      lang,
      locale: LOCALE_TAGS[lang],
      dir: RTL_LANGS.has(lang) ? "rtl" : "ltr",
      setLang,
      t,
    }),
    [lang, setLang, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nState {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

export function useT(): TFunction {
  return useI18n().t;
}
