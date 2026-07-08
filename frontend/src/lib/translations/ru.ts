import type { TranslationKey } from "./en";

const ru: Record<TranslationKey, string> = {
  "nav.dashboard": "Панель",
  "nav.chat": "Чат",
  "nav.timeline": "Хронология",
  "nav.files": "Документы",
  "nav.lawyers": "Юристы",
  "nav.signOut": "Выйти",
  "nav.login": "Войти",
  "nav.langSwitcherTitle": "Чат, экспорт и формы будут использовать этот язык",

  "home.tagline":
    "Подготовьтесь, прежде чем обращаться к юристу. Francessca задаёт нужные вопросы, собирает факты, помогает заполнить стандартные формы и формирует структурированное резюме, которое можно передать квалифицированному юристу в Германии.",
  "home.getStarted": "Начать",
  "home.findLawyer": "Найти юриста",

  "common.disclaimer":
    "Francessca не является юристом и не даёт юридических консультаций. Всегда проверяйте документы у квалифицированного юриста.",
  "common.loading": "Загрузка…",

  "login.titleLogin": "Войти",
  "login.titleRegister": "Создать аккаунт",
  "login.fullNamePlaceholder": "Полное имя (необязательно)",
  "login.emailPlaceholder": "Электронная почта",
  "login.passwordPlaceholder": "Пароль",
  "login.pleaseWait": "Пожалуйста, подождите…",
  "login.signUp": "Зарегистрироваться",
  "login.or": "или",
  "login.needAccount": "Нет аккаунта? Зарегистрироваться",
  "login.haveAccount": "Уже есть аккаунт? Войти",

  "chat.newConversation": "+ Новый разговор",
  "chat.noConversations": "Разговоров пока нет.",
  "chat.tokensRemaining": "Осталось токенов: {{count}}",
  "chat.exportPdf": "Экспортировать резюме дела в PDF",
  "chat.generating": "Создание…",
  "chat.exportDone": "PDF-резюме дела загружено.",
  "chat.emptyPrompt": "Расскажите, что произошло. Например: «Меня уволили вчера».",
  "chat.typing": "Francessca печатает…",
  "chat.attachDocuments": "Прикрепить документы:",
  "chat.typeMessage": "Введите сообщение…",
  "chat.send": "Отправить",

  "files.title": "Документы",
  "files.subtitle":
    "Загрузите файлы PDF, изображение, DOCX или TXT (макс. {{maxMb}} МБ). Текст извлекается автоматически — включая OCR для изображений, — чтобы Francessca могла его использовать.",
  "files.uploadButton": "Загрузить документ",
  "files.uploading": "Загрузка…",
  "files.textExtracted": "Текст извлечён",
  "files.noText": "Нет текста",
  "files.noDocuments": "Документы ещё не загружены.",
  "files.sizeExceeds": "Файл превышает {{maxMb}} МБ.",

  "lawyers.title": "Найти юриста",
  "lawyers.specialization": "Специализация",
  "lawyers.city": "Город",
  "lawyers.language": "Язык",
  "lawyers.search": "Поиск",
  "lawyers.searching": "Поиск…",
  "lawyers.languagesLabel": "Языки: {{list}}",
  "lawyers.email": "Эл. почта",
  "lawyers.website": "Веб-сайт",
  "lawyers.noResults": "Юристы, соответствующие вашему запросу, не найдены.",

  "timeline.title": "Хронология дела",
  "timeline.subtitle":
    "Формируется автоматически из загруженных документов и сообщений чата — Francessca извлекает каждый датированный факт, чтобы вам не пришлось составлять хронологию вручную.",
  "timeline.loadingTimeline": "Загрузка хронологии…",
  "timeline.noEvents":
    "Датированных событий пока нет. Загрузите документ или опишите, что произошло, в чате — Francessca автоматически извлечёт даты и события сюда.",
  "timeline.deadline": "Срок",
  "timeline.fromDocument": "Из документа",
  "timeline.fromChat": "Из чата",
  "timeline.undated": "Без даты",

  "dashboard.welcome": "Добро пожаловать",
  "dashboard.welcomeName": "Добро пожаловать, {{name}}",
  "dashboard.tileConversations": "Разговоры",
  "dashboard.tileDocuments": "Документы",
  "dashboard.tileTimelineEvents": "События хронологии",
  "dashboard.tileCases": "Дела",
  "dashboard.tileExports": "Экспорты",
  "dashboard.tokenUsage": "Использование токенов",
  "dashboard.tokenUsageLimited": "{{used}} / {{limit}}",
  "dashboard.tokenUsageUnlimited": "{{used}} (без ограничений)",
  "dashboard.premiumPlan": "Премиум-план — без месячного лимита.",
};

export default ru;
