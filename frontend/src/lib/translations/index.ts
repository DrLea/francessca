import en, { type TranslationKey } from "./en";
import de from "./de";
import tr from "./tr";
import ar from "./ar";
import uk from "./uk";
import ru from "./ru";
import pl from "./pl";
import ro from "./ro";

export type { TranslationKey };
export type Dictionary = Record<TranslationKey, string>;

export const dictionaries: Record<string, Dictionary> = {
  en,
  de,
  tr,
  ar,
  uk,
  ru,
  pl,
  ro,
};

export type LangCode = keyof typeof dictionaries;

export const DEFAULT_LANG: LangCode = "en";

// Languages that should render right-to-left.
export const RTL_LANGS: ReadonlySet<string> = new Set(["ar"]);

// BCP-47 locale tags used for date/number formatting (toLocaleDateString etc.)
export const LOCALE_TAGS: Record<LangCode, string> = {
  en: "en-US",
  de: "de-DE",
  tr: "tr-TR",
  ar: "ar",
  uk: "uk-UA",
  ru: "ru-RU",
  pl: "pl-PL",
  ro: "ro-RO",
};

export function isLangCode(value: string | null | undefined): value is LangCode {
  return !!value && value in dictionaries;
}
