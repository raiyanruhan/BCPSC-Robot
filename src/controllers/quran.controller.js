// Controller for the get_quran_verse tool.
// Resolves surah names, validates inputs, calls the Quran service, and shapes
// the response in a way that is easy for the ElevenLabs agent to narrate.

const { getQuranVerse } = require('../services/quran.service');

// Hardcoded lookup table of all 114 surah names so the server can resolve
// either numeric IDs or human-readable names without another network hop.
// English names follow common transliteration used by many APIs.
const SURAH_LOOKUP = [
  { number: 1, ar: 'الفاتحة', en: 'Al-Fatihah' },
  { number: 2, ar: 'البقرة', en: 'Al-Baqarah' },
  { number: 3, ar: 'آل عمران', en: 'Ali Imran' },
  { number: 4, ar: 'النساء', en: 'An-Nisa' },
  { number: 5, ar: 'المائدة', en: 'Al-Ma\'idah' },
  { number: 6, ar: 'الأنعام', en: 'Al-An\'am' },
  { number: 7, ar: 'الأعراف', en: 'Al-A\'raf' },
  { number: 8, ar: 'الأنفال', en: 'Al-Anfal' },
  { number: 9, ar: 'التوبة', en: 'At-Tawbah' },
  { number: 10, ar: 'يونس', en: 'Yunus' },
  { number: 11, ar: 'هود', en: 'Hud' },
  { number: 12, ar: 'يوسف', en: 'Yusuf' },
  { number: 13, ar: 'الرعد', en: 'Ar-Ra\'d' },
  { number: 14, ar: 'إبراهيم', en: 'Ibrahim' },
  { number: 15, ar: 'الحجر', en: 'Al-Hijr' },
  { number: 16, ar: 'النحل', en: 'An-Nahl' },
  { number: 17, ar: 'الإسراء', en: 'Al-Isra' },
  { number: 18, ar: 'الكهف', en: 'Al-Kahf' },
  { number: 19, ar: 'مريم', en: 'Maryam' },
  { number: 20, ar: 'طه', en: 'Ta-Ha' },
  { number: 21, ar: 'الأنبياء', en: 'Al-Anbiya' },
  { number: 22, ar: 'الحج', en: 'Al-Hajj' },
  { number: 23, ar: 'المؤمنون', en: 'Al-Mu\'minun' },
  { number: 24, ar: 'النور', en: 'An-Nur' },
  { number: 25, ar: 'الفرقان', en: 'Al-Furqan' },
  { number: 26, ar: 'الشعراء', en: 'Ash-Shu\'ara' },
  { number: 27, ar: 'النمل', en: 'An-Naml' },
  { number: 28, ar: 'القصص', en: 'Al-Qasas' },
  { number: 29, ar: 'العنكبوت', en: 'Al-Ankabut' },
  { number: 30, ar: 'الروم', en: 'Ar-Rum' },
  { number: 31, ar: 'لقمان', en: 'Luqman' },
  { number: 32, ar: 'السجدة', en: 'As-Sajdah' },
  { number: 33, ar: 'الأحزاب', en: 'Al-Ahzab' },
  { number: 34, ar: 'سبإ', en: 'Saba' },
  { number: 35, ar: 'فاطر', en: 'Fatir' },
  { number: 36, ar: 'يس', en: 'Ya-Sin' },
  { number: 37, ar: 'الصافات', en: 'As-Saffat' },
  { number: 38, ar: 'ص', en: 'Sad' },
  { number: 39, ar: 'الزمر', en: 'Az-Zumar' },
  { number: 40, ar: 'غافر', en: 'Ghafir' },
  { number: 41, ar: 'فصلت', en: 'Fussilat' },
  { number: 42, ar: 'الشورى', en: 'Ash-Shura' },
  { number: 43, ar: 'الزخرف', en: 'Az-Zukhruf' },
  { number: 44, ar: 'الدخان', en: 'Ad-Dukhan' },
  { number: 45, ar: 'الجاثية', en: 'Al-Jathiyah' },
  { number: 46, ar: 'الأحقاف', en: 'Al-Ahqaf' },
  { number: 47, ar: 'محمد', en: 'Muhammad' },
  { number: 48, ar: 'الفتح', en: 'Al-Fath' },
  { number: 49, ar: 'الحجرات', en: 'Al-Hujurat' },
  { number: 50, ar: 'ق', en: 'Qaf' },
  { number: 51, ar: 'الذاريات', en: 'Adh-Dhariyat' },
  { number: 52, ar: 'الطور', en: 'At-Tur' },
  { number: 53, ar: 'النجم', en: 'An-Najm' },
  { number: 54, ar: 'القمر', en: 'Al-Qamar' },
  { number: 55, ar: 'الرحمن', en: 'Ar-Rahman' },
  { number: 56, ar: 'الواقعة', en: 'Al-Waqi\'ah' },
  { number: 57, ar: 'الحديد', en: 'Al-Hadid' },
  { number: 58, ar: 'المجادلة', en: 'Al-Mujadila' },
  { number: 59, ar: 'الحشر', en: 'Al-Hashr' },
  { number: 60, ar: 'الممتحنة', en: 'Al-Mumtahanah' },
  { number: 61, ar: 'الصف', en: 'As-Saff' },
  { number: 62, ar: 'الجمعة', en: 'Al-Jumu\'ah' },
  { number: 63, ar: 'المنافقون', en: 'Al-Munafiqun' },
  { number: 64, ar: 'التغابن', en: 'At-Taghabun' },
  { number: 65, ar: 'الطلاق', en: 'At-Talaq' },
  { number: 66, ar: 'التحريم', en: 'At-Tahrim' },
  { number: 67, ar: 'الملك', en: 'Al-Mulk' },
  { number: 68, ar: 'القلم', en: 'Al-Qalam' },
  { number: 69, ar: 'الحاقة', en: 'Al-Haqqah' },
  { number: 70, ar: 'المعارج', en: 'Al-Ma\'arij' },
  { number: 71, ar: 'نوح', en: 'Nuh' },
  { number: 72, ar: 'الجن', en: 'Al-Jinn' },
  { number: 73, ar: 'المزمل', en: 'Al-Muzzammil' },
  { number: 74, ar: 'المدثر', en: 'Al-Muddaththir' },
  { number: 75, ar: 'القيامة', en: 'Al-Qiyamah' },
  { number: 76, ar: 'الإنسان', en: 'Al-Insan' },
  { number: 77, ar: 'المرسلات', en: 'Al-Mursalat' },
  { number: 78, ar: 'النبأ', en: 'An-Naba' },
  { number: 79, ar: 'النازعات', en: 'An-Nazi\'at' },
  { number: 80, ar: 'عبس', en: 'Abasa' },
  { number: 81, ar: 'التكوير', en: 'At-Takwir' },
  { number: 82, ar: 'الإنفطار', en: 'Al-Infitar' },
  { number: 83, ar: 'المطففين', en: 'Al-Mutaffifin' },
  { number: 84, ar: 'الإنشقاق', en: 'Al-Inshiqaq' },
  { number: 85, ar: 'البروج', en: 'Al-Buruj' },
  { number: 86, ar: 'الطارق', en: 'At-Tariq' },
  { number: 87, ar: 'الأعلى', en: 'Al-A\'la' },
  { number: 88, ar: 'الغاشية', en: 'Al-Ghashiyah' },
  { number: 89, ar: 'الفجر', en: 'Al-Fajr' },
  { number: 90, ar: 'البلد', en: 'Al-Balad' },
  { number: 91, ar: 'الشمس', en: 'Ash-Shams' },
  { number: 92, ar: 'الليل', en: 'Al-Layl' },
  { number: 93, ar: 'الضحى', en: 'Ad-Duha' },
  { number: 94, ar: 'الشرح', en: 'Ash-Sharh' },
  { number: 95, ar: 'التين', en: 'At-Tin' },
  { number: 96, ar: 'العلق', en: 'Al-\'Alaq' },
  { number: 97, ar: 'القدر', en: 'Al-Qadr' },
  { number: 98, ar: 'البينة', en: 'Al-Bayyinah' },
  { number: 99, ar: 'الزلزلة', en: 'Az-Zalzalah' },
  { number: 100, ar: 'العاديات', en: 'Al-\'Adiyat' },
  { number: 101, ar: 'القارعة', en: 'Al-Qari\'ah' },
  { number: 102, ar: 'التكاثر', en: 'At-Takathur' },
  { number: 103, ar: 'العصر', en: 'Al-\'Asr' },
  { number: 104, ar: 'الهمزة', en: 'Al-Humazah' },
  { number: 105, ar: 'الفيل', en: 'Al-Fil' },
  { number: 106, ar: 'قريش', en: 'Quraysh' },
  { number: 107, ar: 'الماعون', en: 'Al-Ma\'un' },
  { number: 108, ar: 'الكوثر', en: 'Al-Kawthar' },
  { number: 109, ar: 'الكافرون', en: 'Al-Kafirun' },
  { number: 110, ar: 'النصر', en: 'An-Nasr' },
  { number: 111, ar: 'المسد', en: 'Al-Masad' },
  { number: 112, ar: 'الإخلاص', en: 'Al-Ikhlas' },
  { number: 113, ar: 'الفلق', en: 'Al-Falaq' },
  { number: 114, ar: 'الناس', en: 'An-Nas' }
];

function resolveSurah(input) {
  if (typeof input === 'number') {
    return SURAH_LOOKUP.find((s) => s.number === input) || null;
  }
  if (typeof input === 'string') {
    const normalized = input.trim().toLowerCase();
    return (
      SURAH_LOOKUP.find(
        (s) =>
          s.en.toLowerCase() === normalized ||
          s.ar.replace(/\s+/g, '').toLowerCase() === normalized.replace(/\s+/g, '')
      ) || null
    );
  }
  return null;
}

async function handleGetQuranVerse(req, res, next) {
  try {
    const body = req.body || {};

    const surahInput = body.surah;
    const ayah = body.ayah;
    const language = body.language === 'bn' ? 'bn' : 'en';

    if (surahInput === undefined || surahInput === null) {
      return res.status(400).json({ error: 'Missing required field: surah' });
    }
    if (ayah === undefined || ayah === null) {
      return res.status(400).json({ error: 'Missing required field: ayah' });
    }

    const surahInfo = resolveSurah(
      typeof surahInput === 'string' && /^[0-9]+$/.test(surahInput)
        ? Number(surahInput)
        : surahInput
    );

    if (!surahInfo) {
      return res.status(400).json({ error: 'Invalid surah. Use 1–114 or a valid surah name.' });
    }

    const ayahNumber = Number(ayah);
    if (!Number.isInteger(ayahNumber) || ayahNumber <= 0) {
      return res
        .status(400)
        .json({ error: 'Invalid ayah. Provide a positive integer ayah number.' });
    }

    const verse = await getQuranVerse(surahInfo.number, ayahNumber, language);

    const summary = `Surah ${surahInfo.en}, Ayah ${ayahNumber} — ${verse.translation}`;

    const responseBody = {
      success: true,
      data: {
        surah_number: surahInfo.number,
        surah_name_arabic: verse.surah_name_arabic || surahInfo.ar,
        surah_name_english: verse.surah_name_english || surahInfo.en,
        ayah_number: ayahNumber,
        arabic_text: verse.arabic_text,
        translation: verse.translation,
        translator: verse.translator,
        language,
        summary
      }
    };

    res.json(responseBody);
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleGetQuranVerse
};

