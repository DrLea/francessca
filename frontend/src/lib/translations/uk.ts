import type { TranslationKey } from "./en";

const uk: Record<TranslationKey, string> = {
  "nav.dashboard": "Панель",
  "nav.chat": "Чат",
  "nav.timeline": "Хронологія",
  "nav.files": "Документи",
  "nav.lawyers": "Юристи",
  "nav.signOut": "Вийти",
  "nav.login": "Увійти",
  "nav.langSwitcherTitle": "Чат, експорти та форми використовуватимуть цю мову",

  "home.tagline":
    "Підготуйтеся, перш ніж звертатися до юриста. Francessca ставить правильні запитання, збирає ваші факти, допомагає заповнити стандартні форми та створює структуроване резюме, яке можна передати кваліфікованому юристу в Німеччині.",
  "home.getStarted": "Почати",
  "home.findLawyer": "Знайти юриста",

  "common.disclaimer":
    "Francessca не є юристом і не надає юридичних консультацій. Завжди переглядайте документи разом із кваліфікованим юристом.",
  "common.loading": "Завантаження…",

  "login.titleLogin": "Увійти",
  "login.titleRegister": "Створити акаунт",
  "login.fullNamePlaceholder": "Повне ім'я (необов'язково)",
  "login.emailPlaceholder": "Електронна пошта",
  "login.passwordPlaceholder": "Пароль",
  "login.pleaseWait": "Зачекайте, будь ласка…",
  "login.signUp": "Зареєструватися",
  "login.or": "або",
  "login.needAccount": "Немає акаунта? Зареєструватися",
  "login.haveAccount": "Вже є акаунт? Увійти",

  "chat.newConversation": "+ Нова розмова",
  "chat.noConversations": "Розмов ще немає.",
  "chat.tokensRemaining": "Залишилося токенів: {{count}}",
  "chat.exportPdf": "Експортувати резюме справи у PDF",
  "chat.generating": "Створення…",
  "chat.exportDone": "PDF-резюме справи завантажено.",
  "chat.emptyPrompt": "Розкажіть, що сталося. Наприклад: «Мене звільнили вчора».",
  "chat.typing": "Francessca друкує…",
  "chat.attachDocuments": "Додати документи:",
  "chat.typeMessage": "Введіть повідомлення…",
  "chat.send": "Надіслати",

  "files.title": "Документи",
  "files.subtitle":
    "Завантажте файли PDF, зображення, DOCX або TXT (макс. {{maxMb}} МБ). Текст витягується автоматично — включно з OCR для зображень, — щоб Francessca могла його використати.",
  "files.uploadButton": "Завантажити документ",
  "files.uploading": "Завантаження…",
  "files.textExtracted": "Текст витягнуто",
  "files.noText": "Немає тексту",
  "files.noDocuments": "Документів ще не завантажено.",
  "files.sizeExceeds": "Файл перевищує {{maxMb}} МБ.",

  "lawyers.title": "Знайти юриста",
  "lawyers.specialization": "Спеціалізація",
  "lawyers.city": "Місто",
  "lawyers.language": "Мова",
  "lawyers.search": "Пошук",
  "lawyers.searching": "Пошук…",
  "lawyers.languagesLabel": "Мови: {{list}}",
  "lawyers.email": "Електронна пошта",
  "lawyers.website": "Вебсайт",
  "lawyers.noResults": "Юристів, що відповідають вашому запиту, не знайдено.",

  "timeline.title": "Хронологія справи",
  "timeline.subtitle":
    "Автоматично формується з ваших завантажених документів і повідомлень чату — Francessca витягує кожен датований факт, щоб вам не довелося складати хронологію вручну.",
  "timeline.loadingTimeline": "Завантаження хронології…",
  "timeline.noEvents":
    "Датованих подій ще немає. Завантажте документ або опишіть, що сталося, в чаті — Francessca автоматично витягне дати та події сюди.",
  "timeline.deadline": "Термін",
  "timeline.fromDocument": "З документа",
  "timeline.fromChat": "З чату",
  "timeline.undated": "Без дати",

  "dashboard.welcome": "Ласкаво просимо",
  "dashboard.welcomeName": "Ласкаво просимо, {{name}}",
  "dashboard.tileConversations": "Розмови",
  "dashboard.tileDocuments": "Документи",
  "dashboard.tileTimelineEvents": "Події хронології",
  "dashboard.tileCases": "Справи",
  "dashboard.tileExports": "Експорти",
  "dashboard.tokenUsage": "Використання токенів",
  "dashboard.tokenUsageLimited": "{{used}} / {{limit}}",
  "dashboard.tokenUsageUnlimited": "{{used}} (без обмежень)",
  "dashboard.premiumPlan": "Преміум-план — без місячного ліміту.",
};

export default uk;
