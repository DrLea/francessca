const en = {
  "nav.dashboard": "Dashboard",
  "nav.chat": "Chat",
  "nav.timeline": "Timeline",
  "nav.files": "Documents",
  "nav.lawyers": "Lawyers",
  "nav.signOut": "Sign out",
  "nav.login": "Log in",
  "nav.langSwitcherTitle": "Chat, exports, and forms will use this language",

  "home.tagline":
    "Get organized before you speak with a lawyer. Francessca asks the right questions, collects your facts, helps fill standard forms, and produces a structured summary you can hand to a qualified lawyer in Germany.",
  "home.getStarted": "Get started",
  "home.findLawyer": "Find a lawyer",

  "common.disclaimer":
    "Francessca is not a lawyer and does not provide legal advice. Always have documents reviewed by a qualified lawyer.",
  "common.loading": "Loading…",

  "login.titleLogin": "Log in",
  "login.titleRegister": "Create account",
  "login.fullNamePlaceholder": "Full name (optional)",
  "login.emailPlaceholder": "Email",
  "login.passwordPlaceholder": "Password",
  "login.pleaseWait": "Please wait…",
  "login.signUp": "Sign up",
  "login.or": "or",
  "login.needAccount": "Need an account? Sign up",
  "login.haveAccount": "Have an account? Log in",

  "chat.newConversation": "+ New conversation",
  "chat.noConversations": "No conversations yet.",
  "chat.tokensRemaining": "{{count}} tokens remaining",
  "chat.exportPdf": "Export case PDF",
  "chat.generating": "Generating…",
  "chat.exportDone": "Case summary PDF downloaded.",
  "chat.emptyPrompt":
    "Tell me what happened. For example: “I was fired yesterday.”",
  "chat.typing": "Francessca is typing…",
  "chat.attachDocuments": "Attach documents:",
  "chat.typeMessage": "Type your message…",
  "chat.send": "Send",

  "files.title": "Documents",
  "files.subtitle":
    "Upload PDF, image, DOCX, or TXT files (max {{maxMb}} MB). Text is extracted automatically — including OCR for images — so Francessca can use it.",
  "files.uploadButton": "Upload a document",
  "files.uploading": "Uploading…",
  "files.textExtracted": "Text extracted",
  "files.noText": "No text",
  "files.noDocuments": "No documents uploaded yet.",
  "files.sizeExceeds": "File exceeds {{maxMb}} MB.",
  "files.download": "Download",
  "files.downloadTranslated": "Download translation",
  "files.translating": "Translating…",
  "files.delete": "Delete",
  "files.deleting": "Deleting…",
  "files.deleteConfirm": "Delete this document? This cannot be undone.",
  "files.noTextForTranslation": "No extracted text available to translate",
  "files.actionError": "Something went wrong. Please try again.",

  "lawyers.title": "Find a lawyer",
  "lawyers.specialization": "Specialization",
  "lawyers.city": "City",
  "lawyers.language": "Language",
  "lawyers.search": "Search",
  "lawyers.searching": "Searching…",
  "lawyers.languagesLabel": "Languages: {{list}}",
  "lawyers.email": "Email",
  "lawyers.website": "Website",
  "lawyers.noResults": "No lawyers matched your search.",

  "timeline.title": "Case timeline",
  "timeline.subtitle":
    "Automatically built from your uploaded documents and chat messages — Francessca pulls out every dated fact so you don't have to assemble a chronology by hand.",
  "timeline.loadingTimeline": "Loading timeline…",
  "timeline.noEvents":
    "No dated events yet. Upload a document or describe what happened in chat — Francessca will extract dates and events here automatically.",
  "timeline.deadline": "Deadline",
  "timeline.fromDocument": "From a document",
  "timeline.fromChat": "From chat",
  "timeline.undated": "Undated",

  "dashboard.welcome": "Welcome",
  "dashboard.welcomeName": "Welcome, {{name}}",
  "dashboard.tileConversations": "Conversations",
  "dashboard.tileDocuments": "Documents",
  "dashboard.tileTimelineEvents": "Timeline events",
  "dashboard.tileCases": "Cases",
  "dashboard.tileExports": "Exports",
  "dashboard.tokenUsage": "Token usage",
  "dashboard.tokenUsageLimited": "{{used}} / {{limit}}",
  "dashboard.tokenUsageUnlimited": "{{used}} (unlimited)",
  "dashboard.premiumPlan": "Premium plan — no monthly limit.",
} as const;

export default en;
export type TranslationKey = keyof typeof en;
