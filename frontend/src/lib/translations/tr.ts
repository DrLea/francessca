import type { TranslationKey } from "./en";

const tr: Record<TranslationKey, string> = {
  "nav.dashboard": "Panel",
  "nav.chat": "Sohbet",
  "nav.timeline": "Zaman Çizelgesi",
  "nav.files": "Belgeler",
  "nav.lawyers": "Avukatlar",
  "nav.signOut": "Çıkış yap",
  "nav.login": "Giriş yap",
  "nav.langSwitcherTitle": "Sohbet, dışa aktarımlar ve formlar bu dili kullanacak",

  "home.tagline":
    "Bir avukatla konuşmadan önce hazırlıklı olun. Francessca doğru soruları sorar, bilgilerinizi toplar, standart formları doldurmanıza yardımcı olur ve Almanya'da yetkin bir avukata verebileceğiniz yapılandırılmış bir özet hazırlar.",
  "home.getStarted": "Başlayın",
  "home.findLawyer": "Avukat bulun",

  "common.disclaimer":
    "Francessca bir avukat değildir ve hukuki tavsiye vermez. Belgeleri her zaman yetkin bir avukata inceletin.",
  "common.loading": "Yükleniyor…",

  "login.titleLogin": "Giriş yap",
  "login.titleRegister": "Hesap oluştur",
  "login.fullNamePlaceholder": "Ad soyad (isteğe bağlı)",
  "login.emailPlaceholder": "E-posta",
  "login.passwordPlaceholder": "Şifre",
  "login.pleaseWait": "Lütfen bekleyin…",
  "login.signUp": "Kaydol",
  "login.or": "veya",
  "login.needAccount": "Hesabınız yok mu? Kaydolun",
  "login.haveAccount": "Hesabınız var mı? Giriş yapın",

  "chat.newConversation": "+ Yeni konuşma",
  "chat.noConversations": "Henüz konuşma yok.",
  "chat.tokensRemaining": "{{count}} token kaldı",
  "chat.exportPdf": "Dava özetini PDF olarak dışa aktar",
  "chat.generating": "Oluşturuluyor…",
  "chat.exportDone": "Dava özeti PDF'i indirildi.",
  "chat.emptyPrompt": "Ne olduğunu anlatın. Örneğin: “Dün işten çıkarıldım.”",
  "chat.typing": "Francessca yazıyor…",
  "chat.attachDocuments": "Belge ekle:",
  "chat.typeMessage": "Mesajınızı yazın…",
  "chat.send": "Gönder",

  "files.title": "Belgeler",
  "files.subtitle":
    "PDF, görsel, DOCX veya TXT dosyaları yükleyin (en fazla {{maxMb}} MB). Francessca'nın kullanabilmesi için metin otomatik olarak çıkarılır — görseller için OCR dahil.",
  "files.uploadButton": "Belge yükle",
  "files.uploading": "Yükleniyor…",
  "files.textExtracted": "Metin çıkarıldı",
  "files.noText": "Metin yok",
  "files.noDocuments": "Henüz belge yüklenmedi.",
  "files.sizeExceeds": "Dosya {{maxMb}} MB sınırını aşıyor.",
  "files.download": "İndir",
  "files.downloadTranslated": "Çeviriyi indir",
  "files.translating": "Çevriliyor…",
  "files.delete": "Sil",
  "files.deleting": "Siliniyor…",
  "files.deleteConfirm": "Bu belge silinsin mi? Bu işlem geri alınamaz.",
  "files.noTextForTranslation": "Çevrilecek metin bulunamadı",
  "files.actionError": "Bir şeyler ters gitti. Lütfen tekrar deneyin.",

  "lawyers.title": "Avukat bulun",
  "lawyers.specialization": "Uzmanlık alanı",
  "lawyers.city": "Şehir",
  "lawyers.language": "Dil",
  "lawyers.search": "Ara",
  "lawyers.searching": "Aranıyor…",
  "lawyers.languagesLabel": "Diller: {{list}}",
  "lawyers.email": "E-posta",
  "lawyers.website": "Web sitesi",
  "lawyers.noResults": "Aramanızla eşleşen avukat bulunamadı.",

  "timeline.title": "Dava zaman çizelgesi",
  "timeline.subtitle":
    "Yüklediğiniz belgeler ve sohbet mesajlarından otomatik olarak oluşturulur — Francessca, elle bir kronoloji oluşturmanıza gerek kalmadan tarihli her bilgiyi çıkarır.",
  "timeline.loadingTimeline": "Zaman çizelgesi yükleniyor…",
  "timeline.noEvents":
    "Henüz tarihli olay yok. Bir belge yükleyin veya sohbette ne olduğunu anlatın — Francessca tarihleri ve olayları burada otomatik olarak çıkaracaktır.",
  "timeline.deadline": "Son tarih",
  "timeline.fromDocument": "Bir belgeden",
  "timeline.fromChat": "Sohbetten",
  "timeline.undated": "Tarihsiz",

  "dashboard.welcome": "Hoş geldiniz",
  "dashboard.welcomeName": "Hoş geldiniz, {{name}}",
  "dashboard.tileConversations": "Konuşmalar",
  "dashboard.tileDocuments": "Belgeler",
  "dashboard.tileTimelineEvents": "Zaman çizelgesi olayları",
  "dashboard.tileCases": "Davalar",
  "dashboard.tileExports": "Dışa aktarımlar",
  "dashboard.tokenUsage": "Token kullanımı",
  "dashboard.tokenUsageLimited": "{{used}} / {{limit}}",
  "dashboard.tokenUsageUnlimited": "{{used}} (sınırsız)",
  "dashboard.premiumPlan": "Premium plan — aylık sınır yok.",
};

export default tr;
