import type { TranslationKey } from "./en";

const ro: Record<TranslationKey, string> = {
  "nav.dashboard": "Panou",
  "nav.chat": "Chat",
  "nav.timeline": "Cronologie",
  "nav.files": "Documente",
  "nav.lawyers": "Avocați",
  "nav.signOut": "Deconectare",
  "nav.login": "Autentificare",
  "nav.langSwitcherTitle": "Chatul, exporturile și formularele vor folosi această limbă",

  "home.tagline":
    "Organizează-te înainte de a vorbi cu un avocat. Francessca pune întrebările potrivite, îți colectează faptele, te ajută să completezi formulare standard și produce un rezumat structurat pe care îl poți preda unui avocat calificat din Germania.",
  "home.getStarted": "Începe",
  "home.findLawyer": "Găsește un avocat",

  "common.disclaimer":
    "Francessca nu este avocat și nu oferă consultanță juridică. Documentele trebuie verificate întotdeauna de un avocat calificat.",
  "common.loading": "Se încarcă…",

  "login.titleLogin": "Autentificare",
  "login.titleRegister": "Creează cont",
  "login.fullNamePlaceholder": "Nume complet (opțional)",
  "login.emailPlaceholder": "E-mail",
  "login.passwordPlaceholder": "Parolă",
  "login.pleaseWait": "Vă rugăm așteptați…",
  "login.signUp": "Înregistrare",
  "login.or": "sau",
  "login.needAccount": "Nu ai cont? Înregistrează-te",
  "login.haveAccount": "Ai deja un cont? Autentifică-te",

  "chat.newConversation": "+ Conversație nouă",
  "chat.noConversations": "Nicio conversație încă.",
  "chat.tokensRemaining": "{{count}} tokenuri rămase",
  "chat.exportPdf": "Exportă rezumatul cazului în PDF",
  "chat.generating": "Se generează…",
  "chat.exportDone": "PDF-ul cu rezumatul cazului a fost descărcat.",
  "chat.emptyPrompt": "Spune-mi ce s-a întâmplat. De exemplu: „Am fost concediat ieri”.",
  "chat.typing": "Francessca scrie…",
  "chat.attachDocuments": "Atașează documente:",
  "chat.typeMessage": "Scrie un mesaj…",
  "chat.send": "Trimite",

  "files.title": "Documente",
  "files.subtitle":
    "Încarcă fișiere PDF, imagine, DOCX sau TXT (max. {{maxMb}} MB). Textul este extras automat — inclusiv OCR pentru imagini — astfel încât Francessca să îl poată folosi.",
  "files.uploadButton": "Încarcă un document",
  "files.uploading": "Se încarcă…",
  "files.textExtracted": "Text extras",
  "files.noText": "Fără text",
  "files.noDocuments": "Niciun document încărcat încă.",
  "files.sizeExceeds": "Fișierul depășește {{maxMb}} MB.",

  "lawyers.title": "Găsește un avocat",
  "lawyers.specialization": "Specializare",
  "lawyers.city": "Oraș",
  "lawyers.language": "Limbă",
  "lawyers.search": "Caută",
  "lawyers.searching": "Se caută…",
  "lawyers.languagesLabel": "Limbi: {{list}}",
  "lawyers.email": "E-mail",
  "lawyers.website": "Website",
  "lawyers.noResults": "Niciun avocat nu corespunde căutării tale.",

  "timeline.title": "Cronologia cazului",
  "timeline.subtitle":
    "Construită automat din documentele încărcate și mesajele din chat — Francessca extrage fiecare fapt datat, ca să nu fie nevoie să întocmești manual o cronologie.",
  "timeline.loadingTimeline": "Se încarcă cronologia…",
  "timeline.noEvents":
    "Niciun eveniment datat încă. Încarcă un document sau descrie în chat ce s-a întâmplat — Francessca va extrage automat aici datele și evenimentele.",
  "timeline.deadline": "Termen limită",
  "timeline.fromDocument": "Dintr-un document",
  "timeline.fromChat": "Din chat",
  "timeline.undated": "Nedatat",

  "dashboard.welcome": "Bine ai venit",
  "dashboard.welcomeName": "Bine ai venit, {{name}}",
  "dashboard.tileConversations": "Conversații",
  "dashboard.tileDocuments": "Documente",
  "dashboard.tileTimelineEvents": "Evenimente cronologie",
  "dashboard.tileCases": "Cazuri",
  "dashboard.tileExports": "Exporturi",
  "dashboard.tokenUsage": "Utilizare tokenuri",
  "dashboard.tokenUsageLimited": "{{used}} / {{limit}}",
  "dashboard.tokenUsageUnlimited": "{{used}} (nelimitat)",
  "dashboard.premiumPlan": "Plan Premium — fără limită lunară.",
};

export default ro;
