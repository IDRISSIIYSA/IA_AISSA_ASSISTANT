"""Langues étudiées par IA AISSA : phrases d'apprentissage et voix de synthèse du navigateur."""

LANGUES = {
    "Arabe": {
        "voix": "ar-SA",
        "phrases": ["كيف حالك اليوم", "ما هو رقم معاملات الشركة", "هذا التقرير المالي للسنة", "أين يوجد مكتب المدير",
                    "سوف نجتمع غدا في الصباح", "ما هي نسبة الضريبة على القيمة المضافة", "الشركة حققت أرباحا مهمة",
                    "أريد أن أفهم الميزانية", "شكرا جزيلا على مساعدتك", "متى سيتم دفع الأجور",
                    "يجب علينا تخفيض التكاليف", "ما هو الربح الصافي"],
    },
    "Darija": {
        "voix": "ar-MA",
        "phrases": ["كيداير لاباس عليك", "واش كاين شي مشكل", "بغيت نفهم هاد الحساب", "شحال كيخلص فالشهر",
                    "دابا غادي نصيفط ليك الفاتورة", "هادشي زوين بزاف", "فين كاين البيرو ديال المدير",
                    "kidayr labas 3lik", "wach kayn chi mochkil", "bghit nfhem had l7sab", "chhal kaykhles f chhar",
                    "daba ghadi nsifet lik la facture", "hadchi zwin bzaf", "safi mzyan nchoufou ghda",
                    # au travail et les chiffres
                    "عندنا اجتماع مع المدير مع العشرة", "الكليان باقي ما خلصش الفاتورة", "خاصنا نقصو من المصاريف",
                    "الميزانية ديال هاد العام طلعات", "عطيني الحساب ديال الشهر لي فات", "واحد جوج ثلاثة ربعة خمسة",
                    "ستة سبعة ثمنية تسعود عشرة", "الف ومية درهم", "عشرين الف ريال",
                    "3ndna ijtima3 m3a lmoudir m3a l3achra", "lclient ba9i ma khlsch la facture",
                    "khasna n9ess mn lmasarif", "lbudget dyal had l3am tla3", "3tini l7sab dyal chhar li fat",
                    "wa7ed jouj tlata reb3a khamsa", "stta seb3a tmenya ts3oud 3achra", "alf w mya dirham",
                    "3echrin alf ryal", "l'commande wslat lyoum", "sift lia devis 3afak"],
    },
    "Français": {
        "voix": "fr-FR",
        "phrases": ["bonjour comment allez-vous", "quel est le chiffre d'affaires de la société",
                    "voici le rapport financier de l'année", "nous devons réduire les coûts",
                    "merci beaucoup pour votre aide", "quand les salaires seront-ils payés",
                    "le bénéfice net a augmenté", "je voudrais comprendre le budget", "où se trouve le bureau du directeur",
                    "la réunion aura lieu demain matin"],
    },
    "English": {
        "voix": "en-US",
        "phrases": ["hello how are you today", "what is the company's turnover", "here is the annual financial report",
                    "we need to reduce our costs", "thank you very much for your help", "when will salaries be paid",
                    "net profit has increased", "I would like to understand the budget", "where is the manager's office",
                    "the meeting will take place tomorrow morning"],
    },
    "Español": {
        "voix": "es-ES",
        "phrases": ["hola cómo estás hoy", "cuál es la facturación de la empresa", "aquí está el informe financiero anual",
                    "tenemos que reducir los costes", "muchas gracias por tu ayuda", "cuándo se pagarán los salarios",
                    "el beneficio neto ha aumentado", "quiero entender el presupuesto", "dónde está la oficina del director",
                    "la reunión será mañana por la mañana"],
    },
}


# Atelier de prononciation en darija : phrases du quotidien professionnel (darija en lettres latines, sens en français).
PHRASES_PRO_DARIJA = [
    ("salam, bghit nhder m3a lmoudir 3afak", "Bonjour, je voudrais parler au directeur s'il vous plaît"),
    ("l'facture ghadi nsifetha lik lyoum", "Je vous envoie la facture aujourd'hui"),
    ("chhal taman dyal had l'commande", "Quel est le prix de cette commande ?"),
    ("3ndna ijtima3 ghda m3a l9 dyal sba7", "Nous avons une réunion demain à 9 heures du matin"),
    ("lclient ba9i ma khlsch", "Le client n'a pas encore payé"),
    ("khasna n9ess mn lmasarif had chhar", "Nous devons réduire les dépenses ce mois-ci"),
    ("wach lbudget wajed", "Le budget est-il prêt ?"),
    ("sift lia devis 3afak", "Envoyez-moi un devis s'il vous plaît"),
    ("l'marchandise wslat f lw9t", "La marchandise est arrivée à temps"),
    ("chokran 3la l'khedma dyalkom", "Merci pour votre travail"),
]
