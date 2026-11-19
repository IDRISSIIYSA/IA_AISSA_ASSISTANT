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
    # Banque
    ("bghit n7el compte f lbanka", "Je voudrais ouvrir un compte à la banque"),
    ("chhal kayn f lcompte dyali", "Combien y a-t-il sur mon compte ?"),
    ("bghit ndir virement", "Je voudrais faire un virement"),
    ("lcarte dyali tblokat", "Ma carte bancaire est bloquée"),
    ("chhal lfayda dyal had lkredi", "Quel est le taux d'intérêt de ce crédit ?"),
    ("khassni carnet dyal chèque", "J'ai besoin d'un chéquier"),
    ("wach lflous wslo", "L'argent est-il arrivé ?"),
    # Administration
    ("fin kayna lmo9ata3a", "Où se trouve l'arrondissement ?"),
    ("khassni nsawb la carte nationale", "Je dois faire ma carte nationale"),
    ("chno lwata2i9 li khassni njib", "Quels documents dois-je apporter ?"),
    ("bghit nsawb chahadat ssokna", "Je voudrais une attestation de résidence"),
    ("imta ghadi ykoun lwra9 wajed", "Quand les papiers seront-ils prêts ?"),
    ("fin ghadi nsini", "Où dois-je signer ?"),
    ("khassni nkhlles ttanber", "Je dois payer le timbre"),
    # Douane et commerce extérieur
    ("had sel3a jat mn lkharij", "Cette marchandise vient de l'étranger"),
    ("chhal ddiwana 3la had sel3a", "Combien de droits de douane sur cette marchandise ?"),
    ("fin l'facture dyal chchira", "Où est la facture d'achat ?"),
    ("sel3a ba9a f lport", "La marchandise est restée au port"),
    ("khassna transitaire", "Nous avons besoin d'un transitaire"),
    ("imta ghadi nkhrjo sel3a mn ddiwana", "Quand allons-nous sortir la marchandise de la douane ?"),
]

# La même phrase en écriture arabe (darija telle qu'on l'écrit au Maroc, mots français gardés tels qu'ils se disent).
# Les 20 phrases ajoutées le 19/11/2026 (banque, administration, douane) sont à relire par un locuteur marocain.
ECRITURE_ARABE = {
    "salam, bghit nhder m3a lmoudir 3afak": "سلام، بغيت نهضر مع المدير عافاك",
    "l'facture ghadi nsifetha lik lyoum": "الفاكتورة غادي نصيفطها ليك اليوم",
    "chhal taman dyal had l'commande": "شحال ثمن ديال هاد الكوموند",
    "3ndna ijtima3 ghda m3a l9 dyal sba7": "عندنا اجتماع غدا مع التسعة ديال الصباح",
    "lclient ba9i ma khlsch": "الكليان باقي ما خلصش",
    "khasna n9ess mn lmasarif had chhar": "خاصنا نقص من المصاريف هاد الشهر",
    "wach lbudget wajed": "واش البودجي واجد",
    "sift lia devis 3afak": "صيفط ليا الدوفي عافاك",
    "l'marchandise wslat f lw9t": "الماركانديز وصلات فالوقت",
    "chokran 3la l'khedma dyalkom": "شكرا على الخدمة ديالكم",
    "bghit n7el compte f lbanka": "بغيت نحل كونط فالبنكة",
    "chhal kayn f lcompte dyali": "شحال كاين فالكونط ديالي",
    "bghit ndir virement": "بغيت ندير فيرمون",
    "lcarte dyali tblokat": "لاكارط ديالي تبلوكات",
    "chhal lfayda dyal had lkredi": "شحال الفايدة ديال هاد الكريدي",
    "khassni carnet dyal chèque": "خاصني كارني ديال الشيك",
    "wach lflous wslo": "واش الفلوس وصلو",
    "fin kayna lmo9ata3a": "فين كاينة المقاطعة",
    "khassni nsawb la carte nationale": "خاصني نصاوب لاكارط ناسيونال",
    "chno lwata2i9 li khassni njib": "شنو الوثائق اللي خاصني نجيب",
    "bghit nsawb chahadat ssokna": "بغيت نصاوب شهادة السكنى",
    "imta ghadi ykoun lwra9 wajed": "إمتى غادي يكون الوراق واجد",
    "fin ghadi nsini": "فين غادي نسيني",
    "khassni nkhlles ttanber": "خاصني نخلص التنبر",
    "had sel3a jat mn lkharij": "هاد السلعة جات من الخارج",
    "chhal ddiwana 3la had sel3a": "شحال الديوانة على هاد السلعة",
    "fin l'facture dyal chchira": "فين الفاكتورة ديال الشرية",
    "sel3a ba9a f lport": "السلعة باقة فالبور",
    "khassna transitaire": "خاصنا ترانزيتير",
    "imta ghadi nkhrjo sel3a mn ddiwana": "إمتى غادي نخرجو السلعة من الديوانة",
}
SCORE_INCONNU = 60      # une phrase jamais essayée : ni facile ni difficile, elle passe avant une phrase bien maîtrisée


def phrase_a_travailler(essais, phrases=None, rng=None):
    """Répétition espacée : la phrase dont le score récent (moyenne des 2 derniers essais) est le plus faible ; une
    phrase jamais essayée compte pour SCORE_INCONNU ; la phrase qui vient d'être essayée attend son tour.
    Renvoie (phrase, sens, score récent ou None)."""
    import random as _random
    phrases = phrases or PHRASES_PRO_DARIJA
    rng = rng or _random.Random()
    par_phrase = {}
    for e in essais:
        par_phrase.setdefault(e["phrase"], []).append(e["score"])
    recent = {p: sum(par_phrase[p][-2:]) / len(par_phrase[p][-2:]) for p, _ in phrases if p in par_phrase}
    derniere = essais[-1]["phrase"] if essais else None
    candidates = [(p, s) for p, s in phrases if p != derniere] or list(phrases)
    plus_faible = min(recent.get(p, SCORE_INCONNU) for p, _ in candidates)
    phrase, sens = rng.choice([(p, s) for p, s in candidates if recent.get(p, SCORE_INCONNU) == plus_faible])
    return phrase, sens, recent.get(phrase)


# ==========================================
# Langue d'une réponse, pour choisir la voix (écriture d'abord, puis mots caractéristiques)
# ==========================================
import re as _re

MOTS = {
    "Français": {"le", "la", "les", "des", "du", "de", "est", "et", "vous", "je", "tu", "pour", "avec", "une", "un",
                 "sur", "dans", "pas", "que", "qui", "au", "aux", "ce", "cette", "à", "il", "elle", "sont", "par",
                 "mais", "ou", "votre", "mon", "ton", "bonjour", "bonsoir", "merci", "impôt", "taux", "être", "avez"},
    "English": {"the", "is", "and", "you", "of", "to", "in", "for", "with", "this", "that", "are", "it", "your",
                "what", "how", "hello", "thanks", "can", "will", "have", "has", "be"},
    "Español": {"el", "los", "las", "es", "y", "usted", "para", "con", "una", "por", "del", "está", "son", "como",
                "pero", "muy", "hola", "gracias", "tiene", "su", "más", "qué"},
    "Darija": {"wach", "kifach", "bghit", "dyal", "mzyan", "bzaf", "labas", "chno", "chnou", "daba", "kayn", "walakin",
               "safi", "hna", "nta", "nti", "ana", "3lik", "3lach", "fin", "kidayr", "ghadi", "machi", "had", "hadchi",
               "smahli", "baraka", "chokran", "salam", "zwin", "khoya", "khti", "mezyan", "kolchi", "dima"},
}
DARIJA_ARABE = {"واش", "ديال", "بغيت", "كيفاش", "دابا", "هاد", "هادشي", "شنو", "بزاف", "كاين", "غادي", "ماشي",
                "كيداير", "لاباس", "مزيان", "فين", "علاش", "شحال", "واخا", "صافي", "داز", "نهارك", "كنبغي", "ديالك"}
ARABE = _re.compile(r"[؀-ۿ]")
LATIN = _re.compile(r"[A-Za-zÀ-ÿ]")


def detecter_langue(texte, defaut="Français"):
    """Langue de la voix pour un texte : Arabe ou Darija pour l'écriture arabe (mots darija reconnus), sinon Français,
    English ou Español selon les mots caractéristiques. Français par défaut (langue de l'application)."""
    texte = texte or ""
    nb_arabe, nb_latin = len(ARABE.findall(texte)), len(LATIN.findall(texte))
    if nb_arabe > nb_latin:
        mots_arabes = set(_re.findall(r"[؀-ۿ]+", texte))
        return "Darija" if mots_arabes & DARIJA_ARABE else "Arabe"
    # Écriture latine : la voix marocaine lit mal le darija en lettres latines (3lik, l7sab) ; on choisit la voix
    # française, anglaise ou espagnole qui lit le mieux le texte
    mots = _re.findall(r"[a-zà-ÿ0-9']+", texte.lower())
    scores = {langue: sum(1 for m in mots if m in liste) for langue, liste in MOTS.items() if langue != "Darija"}
    meilleure = max(scores, key=scores.get)
    return meilleure if scores[meilleure] > 0 else defaut


def partie_dans_la_langue(texte, langue):
    """Ce que la voix doit lire : les lignes écrites dans l'écriture de la langue (le salut en darija n'est pas lu
    par la voix française, et inversement)."""
    arabe = langue in ("Arabe", "Darija") and len(ARABE.findall(texte or "")) > 0
    lignes = []
    for ligne in (texte or "").splitlines():
        a, l = len(ARABE.findall(ligne)), len(LATIN.findall(ligne))
        if (arabe and a >= l and a) or (not arabe and l >= a and l) or (not a and not l):
            lignes.append(ligne)
    garde = "\n".join(lignes).strip()
    if not arabe:                      # dans une ligne mixte, retirer les mots en écriture arabe
        garde = _re.sub(r"[؀-ۿ][؀-ۿ\s،؟]*", " ", garde)
    return garde or texte


MAX_SEGMENTS = 6
MIN_CARACTERES_SEGMENT = 12


def segments_par_langue(texte, langue_principale=None):
    """Une réponse mixte découpée pour la voix : [(langue, morceau)], chaque phrase avec sa langue, les phrases
    voisines de même langue regroupées. Écriture arabe → Darija ou Arabe ; écriture latine → langue reconnue par ses
    mots, sinon la langue principale. Au plus MAX_SEGMENTS morceaux (les plus courts rejoignent leur voisin)."""
    texte = (texte or "").strip()
    principale = langue_principale or detecter_langue(texte)
    phrases = [p.strip() for p in _re.split(r"(?<=[.!?؟…])\s+|\n+|\s+[—–]\s+", texte) if p and p.strip()]
    segments = []
    for p in phrases:
        if not (ARABE.search(p) or LATIN.search(p)):          # chiffres, ponctuation : avec le morceau précédent
            langue = segments[-1][0] if segments else principale
        elif len(ARABE.findall(p)) > len(LATIN.findall(p)):
            langue = detecter_langue(p)
        else:
            langue = detecter_langue(p, defaut=principale if principale not in ("Arabe", "Darija") else "Français")
        if segments and segments[-1][0] == langue:
            segments[-1] = (langue, segments[-1][1] + " " + p)
        else:
            segments.append((langue, p))
    # les morceaux trop courts (« OK. », « Salam ! ») rejoignent leur voisin plutôt que changer de voix pour un mot
    i = 0
    while len(segments) > 1 and i < len(segments):
        if len(segments[i][1]) < MIN_CARACTERES_SEGMENT and (ARABE.search(segments[i][1]) is None) == (
                segments[i][0] not in ("Arabe", "Darija")):
            voisin = i - 1 if i > 0 else i + 1
            langue = segments[voisin][0]
            a, b = sorted((i, voisin))
            segments[a:b + 1] = [(langue, segments[a][1] + " " + segments[b][1])]
            i = max(0, a - 1)
            continue
        i += 1
    fusion = []
    for langue, morceau in segments:
        if fusion and fusion[-1][0] == langue:
            fusion[-1] = (langue, fusion[-1][1] + " " + morceau)
        else:
            fusion.append((langue, morceau))
    while len(fusion) > MAX_SEGMENTS:                          # trop de changements : on garde les plus longs morceaux
        i = min(range(len(fusion)), key=lambda k: len(fusion[k][1]))
        voisin = i - 1 if i > 0 else i + 1
        a, b = sorted((i, voisin))
        fusion[a:b + 1] = [(fusion[a if len(fusion[a][1]) >= len(fusion[b][1]) else b][0],
                            fusion[a][1] + " " + fusion[b][1])]
    fusion = [(langue, morceau.strip(" —–-")) for langue, morceau in fusion if morceau.strip(" —–-")]
    return fusion or [(principale, texte)]
