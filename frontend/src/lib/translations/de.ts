import type { TranslationKey } from "./en";

const de: Record<TranslationKey, string> = {
  "nav.dashboard": "Übersicht",
  "nav.chat": "Chat",
  "nav.timeline": "Zeitleiste",
  "nav.files": "Dokumente",
  "nav.lawyers": "Anwälte",
  "nav.signOut": "Abmelden",
  "nav.login": "Anmelden",
  "nav.langSwitcherTitle": "Chat, Exporte und Formulare verwenden diese Sprache",

  "home.tagline":
    "Bereiten Sie sich vor, bevor Sie mit einem Anwalt sprechen. Francessca stellt die richtigen Fragen, erfasst Ihre Fakten, hilft beim Ausfüllen von Standardformularen und erstellt eine strukturierte Zusammenfassung, die Sie einem qualifizierten Anwalt in Deutschland übergeben können.",
  "home.getStarted": "Loslegen",
  "home.findLawyer": "Anwalt finden",

  "common.disclaimer":
    "Francessca ist keine Anwältin und bietet keine Rechtsberatung. Lassen Sie Dokumente stets von einem qualifizierten Anwalt prüfen.",
  "common.loading": "Wird geladen…",

  "login.titleLogin": "Anmelden",
  "login.titleRegister": "Konto erstellen",
  "login.fullNamePlaceholder": "Vollständiger Name (optional)",
  "login.emailPlaceholder": "E-Mail",
  "login.passwordPlaceholder": "Passwort",
  "login.pleaseWait": "Bitte warten…",
  "login.signUp": "Registrieren",
  "login.or": "oder",
  "login.needAccount": "Noch kein Konto? Registrieren",
  "login.haveAccount": "Bereits ein Konto? Anmelden",

  "chat.newConversation": "+ Neue Unterhaltung",
  "chat.noConversations": "Noch keine Unterhaltungen.",
  "chat.tokensRemaining": "{{count}} Tokens übrig",
  "chat.exportPdf": "Fallzusammenfassung als PDF exportieren",
  "chat.generating": "Wird erstellt…",
  "chat.exportDone": "PDF der Fallzusammenfassung heruntergeladen.",
  "chat.emptyPrompt":
    "Erzählen Sie mir, was passiert ist. Zum Beispiel: „Ich wurde gestern gekündigt.“",
  "chat.typing": "Francessca schreibt…",
  "chat.attachDocuments": "Dokumente anhängen:",
  "chat.typeMessage": "Nachricht eingeben…",
  "chat.send": "Senden",

  "files.title": "Dokumente",
  "files.subtitle":
    "Laden Sie PDF-, Bild-, DOCX- oder TXT-Dateien hoch (max. {{maxMb}} MB). Text wird automatisch extrahiert — einschließlich OCR für Bilder —, damit Francessca ihn nutzen kann.",
  "files.uploadButton": "Dokument hochladen",
  "files.uploading": "Wird hochgeladen…",
  "files.textExtracted": "Text extrahiert",
  "files.noText": "Kein Text",
  "files.noDocuments": "Noch keine Dokumente hochgeladen.",
  "files.sizeExceeds": "Datei überschreitet {{maxMb}} MB.",

  "lawyers.title": "Anwalt finden",
  "lawyers.specialization": "Fachgebiet",
  "lawyers.city": "Stadt",
  "lawyers.language": "Sprache",
  "lawyers.search": "Suchen",
  "lawyers.searching": "Wird gesucht…",
  "lawyers.languagesLabel": "Sprachen: {{list}}",
  "lawyers.email": "E-Mail",
  "lawyers.website": "Website",
  "lawyers.noResults": "Keine Anwälte gefunden, die Ihrer Suche entsprechen.",

  "timeline.title": "Fallzeitleiste",
  "timeline.subtitle":
    "Automatisch erstellt aus Ihren hochgeladenen Dokumenten und Chat-Nachrichten — Francessca extrahiert jede datierte Tatsache, damit Sie keine Chronologie von Hand erstellen müssen.",
  "timeline.loadingTimeline": "Zeitleiste wird geladen…",
  "timeline.noEvents":
    "Noch keine datierten Ereignisse. Laden Sie ein Dokument hoch oder beschreiben Sie im Chat, was passiert ist — Francessca extrahiert hier automatisch Daten und Ereignisse.",
  "timeline.deadline": "Frist",
  "timeline.fromDocument": "Aus einem Dokument",
  "timeline.fromChat": "Aus dem Chat",
  "timeline.undated": "Undatiert",

  "dashboard.welcome": "Willkommen",
  "dashboard.welcomeName": "Willkommen, {{name}}",
  "dashboard.tileConversations": "Unterhaltungen",
  "dashboard.tileDocuments": "Dokumente",
  "dashboard.tileTimelineEvents": "Zeitleisten-Ereignisse",
  "dashboard.tileCases": "Fälle",
  "dashboard.tileExports": "Exporte",
  "dashboard.tokenUsage": "Token-Nutzung",
  "dashboard.tokenUsageLimited": "{{used}} / {{limit}}",
  "dashboard.tokenUsageUnlimited": "{{used}} (unbegrenzt)",
  "dashboard.premiumPlan": "Premium-Plan — kein monatliches Limit.",
};

export default de;
