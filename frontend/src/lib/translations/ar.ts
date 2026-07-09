import type { TranslationKey } from "./en";

const ar: Record<TranslationKey, string> = {
  "nav.dashboard": "لوحة التحكم",
  "nav.chat": "المحادثة",
  "nav.timeline": "الجدول الزمني",
  "nav.files": "المستندات",
  "nav.lawyers": "المحامون",
  "nav.signOut": "تسجيل الخروج",
  "nav.login": "تسجيل الدخول",
  "nav.langSwitcherTitle": "سيتم استخدام هذه اللغة في المحادثة والتصدير والنماذج",

  "home.tagline":
    "نظّم أفكارك قبل التحدث مع محامٍ. يطرح فرانتشيسكا الأسئلة الصحيحة، ويجمع الوقائع الخاصة بك، ويساعد في تعبئة النماذج القياسية، وينتج ملخصًا منظمًا يمكنك تسليمه لمحامٍ مؤهل في ألمانيا.",
  "home.getStarted": "ابدأ الآن",
  "home.findLawyer": "ابحث عن محامٍ",

  "common.disclaimer":
    "فرانتشيسكا ليست محامية ولا تقدم استشارات قانونية. احرص دائمًا على مراجعة المستندات من قبل محامٍ مؤهل.",
  "common.loading": "جارٍ التحميل…",

  "login.titleLogin": "تسجيل الدخول",
  "login.titleRegister": "إنشاء حساب",
  "login.fullNamePlaceholder": "الاسم الكامل (اختياري)",
  "login.emailPlaceholder": "البريد الإلكتروني",
  "login.passwordPlaceholder": "كلمة المرور",
  "login.pleaseWait": "يرجى الانتظار…",
  "login.signUp": "إنشاء حساب",
  "login.or": "أو",
  "login.needAccount": "ليس لديك حساب؟ أنشئ حسابًا",
  "login.haveAccount": "لديك حساب بالفعل؟ سجّل الدخول",

  "chat.newConversation": "+ محادثة جديدة",
  "chat.noConversations": "لا توجد محادثات بعد.",
  "chat.tokensRemaining": "{{count}} رمزًا متبقيًا",
  "chat.exportPdf": "تصدير ملخص القضية كملف PDF",
  "chat.generating": "جارٍ الإنشاء…",
  "chat.exportDone": "تم تنزيل ملف PDF لملخص القضية.",
  "chat.emptyPrompt": "أخبرني بما حدث. على سبيل المثال: «تم فصلي من العمل أمس».",
  "chat.typing": "فرانتشيسكا يكتب…",
  "chat.attachDocuments": "إرفاق مستندات:",
  "chat.typeMessage": "اكتب رسالتك…",
  "chat.send": "إرسال",

  "files.title": "المستندات",
  "files.subtitle":
    "قم بتحميل ملفات PDF أو صور أو DOCX أو TXT (بحد أقصى {{maxMb}} ميغابايت). يتم استخراج النص تلقائيًا — بما في ذلك التعرف الضوئي على الحروف للصور — حتى يتمكن فرانتشيسكا من استخدامه.",
  "files.uploadButton": "تحميل مستند",
  "files.uploading": "جارٍ التحميل…",
  "files.textExtracted": "تم استخراج النص",
  "files.noText": "لا يوجد نص",
  "files.noDocuments": "لم يتم تحميل أي مستندات بعد.",
  "files.sizeExceeds": "الملف يتجاوز {{maxMb}} ميغابايت.",
  "files.download": "تنزيل",
  "files.downloadTranslated": "تنزيل الترجمة",
  "files.translating": "جارٍ الترجمة…",
  "files.delete": "حذف",
  "files.deleting": "جارٍ الحذف…",
  "files.deleteConfirm": "هل تريد حذف هذا المستند؟ لا يمكن التراجع عن هذا الإجراء.",
  "files.noTextForTranslation": "لا يوجد نص مستخرج للترجمة",
  "files.actionError": "حدث خطأ ما. يرجى المحاولة مرة أخرى.",

  "lawyers.title": "ابحث عن محامٍ",
  "lawyers.specialization": "التخصص",
  "lawyers.city": "المدينة",
  "lawyers.language": "اللغة",
  "lawyers.search": "بحث",
  "lawyers.searching": "جارٍ البحث…",
  "lawyers.languagesLabel": "اللغات: {{list}}",
  "lawyers.email": "البريد الإلكتروني",
  "lawyers.website": "الموقع الإلكتروني",
  "lawyers.noResults": "لم يتم العثور على محامين يطابقون بحثك.",

  "timeline.title": "الجدول الزمني للقضية",
  "timeline.subtitle":
    "يُبنى تلقائيًا من المستندات التي حمّلتها ورسائل المحادثة — يستخرج فرانتشيسكا كل واقعة مؤرخة حتى لا تضطر لبناء التسلسل الزمني يدويًا.",
  "timeline.loadingTimeline": "جارٍ تحميل الجدول الزمني…",
  "timeline.noEvents":
    "لا توجد أحداث مؤرخة بعد. قم بتحميل مستند أو صِف ما حدث في المحادثة — سيستخرج فرانتشيسكا التواريخ والأحداث هنا تلقائيًا.",
  "timeline.deadline": "موعد نهائي",
  "timeline.fromDocument": "من مستند",
  "timeline.fromChat": "من المحادثة",
  "timeline.undated": "بدون تاريخ",

  "dashboard.welcome": "مرحبًا",
  "dashboard.welcomeName": "مرحبًا، {{name}}",
  "dashboard.tileConversations": "المحادثات",
  "dashboard.tileDocuments": "المستندات",
  "dashboard.tileTimelineEvents": "أحداث الجدول الزمني",
  "dashboard.tileCases": "القضايا",
  "dashboard.tileExports": "التصديرات",
  "dashboard.tokenUsage": "استخدام الرموز",
  "dashboard.tokenUsageLimited": "{{used}} / {{limit}}",
  "dashboard.tokenUsageUnlimited": "{{used}} (غير محدود)",
  "dashboard.premiumPlan": "خطة مميزة — بلا حد شهري.",
};

export default ar;
