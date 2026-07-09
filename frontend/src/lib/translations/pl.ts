import type { TranslationKey } from "./en";

const pl: Record<TranslationKey, string> = {
  "nav.dashboard": "Panel",
  "nav.chat": "Czat",
  "nav.timeline": "Oś czasu",
  "nav.files": "Dokumenty",
  "nav.lawyers": "Prawnicy",
  "nav.signOut": "Wyloguj się",
  "nav.login": "Zaloguj się",
  "nav.langSwitcherTitle": "Czat, eksporty i formularze będą korzystać z tego języka",

  "home.tagline":
    "Przygotuj się, zanim porozmawiasz z prawnikiem. Francessca zadaje właściwe pytania, zbiera fakty, pomaga wypełnić standardowe formularze i tworzy uporządkowane podsumowanie, które możesz przekazać wykwalifikowanemu prawnikowi w Niemczech.",
  "home.getStarted": "Rozpocznij",
  "home.findLawyer": "Znajdź prawnika",

  "common.disclaimer":
    "Francessca nie jest prawnikiem i nie udziela porad prawnych. Zawsze zlecaj przegląd dokumentów wykwalifikowanemu prawnikowi.",
  "common.loading": "Ładowanie…",

  "login.titleLogin": "Zaloguj się",
  "login.titleRegister": "Utwórz konto",
  "login.fullNamePlaceholder": "Imię i nazwisko (opcjonalnie)",
  "login.emailPlaceholder": "E-mail",
  "login.passwordPlaceholder": "Hasło",
  "login.pleaseWait": "Proszę czekać…",
  "login.signUp": "Zarejestruj się",
  "login.or": "lub",
  "login.needAccount": "Nie masz konta? Zarejestruj się",
  "login.haveAccount": "Masz już konto? Zaloguj się",

  "chat.newConversation": "+ Nowa rozmowa",
  "chat.noConversations": "Brak rozmów.",
  "chat.tokensRemaining": "Pozostało tokenów: {{count}}",
  "chat.exportPdf": "Eksportuj podsumowanie sprawy do PDF",
  "chat.generating": "Generowanie…",
  "chat.exportDone": "Pobrano PDF z podsumowaniem sprawy.",
  "chat.emptyPrompt": "Opowiedz, co się stało. Na przykład: „Zostałem/am zwolniony/a wczoraj”.",
  "chat.typing": "Francessca pisze…",
  "chat.attachDocuments": "Załącz dokumenty:",
  "chat.typeMessage": "Wpisz wiadomość…",
  "chat.send": "Wyślij",

  "files.title": "Dokumenty",
  "files.subtitle":
    "Prześlij pliki PDF, obrazy, DOCX lub TXT (maks. {{maxMb}} MB). Tekst jest wyodrębniany automatycznie — w tym OCR dla obrazów — dzięki czemu Francessca może go wykorzystać.",
  "files.uploadButton": "Prześlij dokument",
  "files.uploading": "Przesyłanie…",
  "files.textExtracted": "Tekst wyodrębniony",
  "files.noText": "Brak tekstu",
  "files.noDocuments": "Nie przesłano jeszcze żadnych dokumentów.",
  "files.sizeExceeds": "Plik przekracza {{maxMb}} MB.",
  "files.download": "Pobierz",
  "files.downloadTranslated": "Pobierz tłumaczenie",
  "files.translating": "Tłumaczenie…",
  "files.delete": "Usuń",
  "files.deleting": "Usuwanie…",
  "files.deleteConfirm": "Usunąć ten dokument? Tej czynności nie można cofnąć.",
  "files.noTextForTranslation": "Brak wyodrębnionego tekstu do przetłumaczenia",
  "files.actionError": "Coś poszło nie tak. Spróbuj ponownie.",

  "lawyers.title": "Znajdź prawnika",
  "lawyers.specialization": "Specjalizacja",
  "lawyers.city": "Miasto",
  "lawyers.language": "Język",
  "lawyers.search": "Szukaj",
  "lawyers.searching": "Wyszukiwanie…",
  "lawyers.languagesLabel": "Języki: {{list}}",
  "lawyers.email": "E-mail",
  "lawyers.website": "Strona internetowa",
  "lawyers.noResults": "Nie znaleziono prawników pasujących do wyszukiwania.",

  "timeline.title": "Oś czasu sprawy",
  "timeline.subtitle":
    "Tworzona automatycznie na podstawie przesłanych dokumentów i wiadomości czatu — Francessca wyodrębnia każdy datowany fakt, dzięki czemu nie musisz samodzielnie układać chronologii.",
  "timeline.loadingTimeline": "Ładowanie osi czasu…",
  "timeline.noEvents":
    "Brak jeszcze datowanych zdarzeń. Prześlij dokument lub opisz, co się stało, na czacie — Francessca automatycznie wyodrębni tu daty i zdarzenia.",
  "timeline.deadline": "Termin",
  "timeline.fromDocument": "Z dokumentu",
  "timeline.fromChat": "Z czatu",
  "timeline.undated": "Bez daty",

  "dashboard.welcome": "Witaj",
  "dashboard.welcomeName": "Witaj, {{name}}",
  "dashboard.tileConversations": "Rozmowy",
  "dashboard.tileDocuments": "Dokumenty",
  "dashboard.tileTimelineEvents": "Zdarzenia na osi czasu",
  "dashboard.tileCases": "Sprawy",
  "dashboard.tileExports": "Eksporty",
  "dashboard.tokenUsage": "Zużycie tokenów",
  "dashboard.tokenUsageLimited": "{{used}} / {{limit}}",
  "dashboard.tokenUsageUnlimited": "{{used}} (bez limitu)",
  "dashboard.premiumPlan": "Plan Premium — bez miesięcznego limitu.",
};

export default pl;
