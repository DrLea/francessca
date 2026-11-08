import en, { type TranslationKey } from "./en";
import de from "./de";
import tr from "./tr";
import ar from "./ar";
import uk from "./uk";
import ru from "./ru";
import pl from "./pl";
import ro from "./ro";

import portalEn, { type PortalKey } from "./portal.en";
import portalDe from "./portal.de";
import { portalAr, portalPl, portalRo, portalRu, portalTr, portalUk } from "./portal.client";
import deckEn, { type DeckKey } from "./deck.en";
import deckDe from "./deck.de";
import { deckAr, deckPl, deckRo, deckRu, deckTr, deckUk } from "./deck.client";

/** Every key the UI can ask for: the original set, the portal set and the
 *  strings added to match the pitch deck. */
export type FullTranslationKey = TranslationKey | PortalKey | DeckKey;
export type { FullTranslationKey as TranslationKey };
export type Dictionary = Record<FullTranslationKey, string>;

// The portal strings are layered: English is complete, a language may
// translate only part of it (the lawyer portal exists in English and
// German; the client-facing strings in all eight languages).
const withPortal = (
  base: Record<TranslationKey, string>,
  portal: Partial<Record<PortalKey, string>> = {},
  deck: Partial<Record<DeckKey, string>> = {},
): Dictionary => ({ ...portalEn, ...portal, ...deckEn, ...deck, ...base });

export const dictionaries: Record<string, Dictionary> = {
  en: withPortal(en),
  de: withPortal(de, portalDe, deckDe),
  tr: withPortal(tr, portalTr, deckTr),
  ar: withPortal(ar, portalAr, deckAr),
  uk: withPortal(uk, portalUk, deckUk),
  ru: withPortal(ru, portalRu, deckRu),
  pl: withPortal(pl, portalPl, deckPl),
  ro: withPortal(ro, portalRo, deckRo),
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
