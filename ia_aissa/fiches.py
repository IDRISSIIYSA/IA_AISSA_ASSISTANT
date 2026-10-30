"""
Les fiches de synthèse d'IA AISSA : « parle de la TVA », « c'est quoi l'IS », « explique la paie »…

Sans grand moteur, elle rassemble tout ce qu'elle sait d'un sujet en un exposé structuré : définition, règles et
taux de sa base marocaine, exemples tirés de ses matières, un calcul d'exemple fait par ses calculateurs, l'évolution
dans le temps, et ce que disent ses lectures (CGI, cours…) avec leurs sources. Pour un sujet qui est une de ses
matières (dynasties, incoterms, philosophes…), elle présente la matière et un exemple de chaque réponse.
"""

import re

from . import connaissances as K
from .ecole import MATIERES, PAR_CLE, mots

PARLER = re.compile(r"(\b(p?arle[rz]?|parle-moi|explique|expliquer|expliquez|présente|presente|définition|definition|"
                    r"définis|resume|résume|c'?est quoi|qu'?est[- ]ce (que|qu)|dis[- ]moi (tout )?(sur|de)|"
                    r"tout sur|3tini 3la|hdar 3la|chno hiya|chno howa|chnou)\b|ما هو|ما هي|اشرح|عرف|تكلم)", re.I)


def montant(v):
    return f"{v:,.0f}".replace(",", " ") + " DH"


def _tva():
    exemples = {taux: ", ".join(ops[:5]) for taux, ops in K.TVA_OPERATIONS.items()}
    c = K.calculer_tva(10_000, 0.2)
    return ("## 🧾 La TVA au Maroc\n\n"
            "**Ce que c'est** : la taxe sur la valeur ajoutée est un impôt sur la consommation. L'entreprise la "
            "**collecte** sur ses ventes, **déduit** celle payée sur ses achats, et reverse la différence à l'État : "
            "c'est le client final qui la supporte.\n\n"
            "**Les taux depuis le 1er janvier 2026** :\n\n| Taux | Exemples d'opérations |\n|---|---|\n"
            f"| 20 % (normal) | {exemples['20 %']}… |\n| 10 % (réduit) | {exemples['10 %']}… |\n"
            f"| Exonéré | {exemples['Exonéré']}… |\n\n"
            f"**Exemple de calcul** : une vente de {montant(10_000)} HT au taux normal → TVA {montant(c['tva'])}, "
            f"TTC {montant(c['ttc'])}.\n\n"
            "**TVA due** = TVA collectée − TVA déductible ; si le résultat est négatif, c'est un **crédit de TVA** "
            "reportable.\n\n" + K.EVOLUTIONS["tva"].split("\n\n", 1)[1])


def _is():
    exemple = K.calculer_is_du(1_000_000, 8_000_000)
    return ("## 🏢 L'impôt sur les sociétés (IS) au Maroc\n\n"
            "**Ce que c'est** : l'impôt sur le bénéfice fiscal des sociétés (SARL, SA…).\n\n"
            f"**Taux 2026** : {K.TAUX_IS_NORMAL:.0%} si le bénéfice est inférieur à {montant(K.SEUIL_IS)}, "
            f"{K.TAUX_IS_GRANDES:.0%} au-delà (40 % pour les banques et assurances).\n\n"
            f"**Cotisation minimale** : {K.TAUX_CM:.2%} des produits, au moins {montant(K.MINIMUM_CM)} ; elle est due même "
            "en cas de perte. L'entreprise paie le plus élevé des deux.\n\n"
            f"**Exemple** : bénéfice {montant(1_000_000)}, chiffre d'affaires {montant(8_000_000)} → IS "
            f"{montant(exemple['is'])}, cotisation minimale {montant(exemple['cotisation_minimale'])} → "
            f"**dû : {montant(exemple['is_du'])}**.\n\n" + K.EVOLUTIONS["is"].split("\n\n", 1)[1])


def _ir():
    lignes = "\n".join(f"| jusqu'à {montant(p)} | {t:.0%} | {montant(d)} |" if p != float("inf")
                       else f"| au-delà | {t:.0%} | {montant(d)} |" for p, t, d in K.BAREME_IR)
    r = K.calculer_ir(120_000)
    return ("## 👤 L'impôt sur le revenu (IR) au Maroc\n\n"
            "**Ce que c'est** : l'impôt sur les revenus des personnes physiques (salaires, loyers, revenus "
            "professionnels, plus-values…).\n\n**Barème annuel 2026** :\n\n| Revenu net imposable | Taux | Somme à déduire |\n"
            f"|---|---|---|\n{lignes}\n\n**Exemple** : {montant(120_000)} de revenu net imposable annuel → IR "
            f"{montant(r['ir_annuel'])} ({montant(r['ir_mensuel'])} par mois, taux moyen {r['taux_moyen']:.1%}).\n\n"
            + K.EVOLUTIONS["ir"].split("\n\n", 1)[1])


def _paie():
    p = K.calculer_paie(8_000)
    return ("## 💼 La paie au Maroc (CNSS, AMO, IR)\n\n"
            f"**Retenues du salarié** : CNSS {K.CNSS_SALARIE:.2%} du brut plafonné à {montant(K.PLAFOND_CNSS_MENSUEL)} "
            f"par mois, AMO {K.AMO_SALARIE:.2%} du brut sans plafond, puis l'IR sur le net imposable (après frais "
            "professionnels de 35 % ou 25 %).\n\n"
            f"**Charges patronales** : CNSS {K.CNSS_EMPLOYEUR:.2%} (plafonnée) et AMO {K.AMO_EMPLOYEUR:.2%}, hors "
            "allocations familiales et taxe de formation professionnelle.\n\n"
            f"**Exemple** : brut {montant(8_000)} → net {montant(p['salaire_net'])} ; coût employeur "
            f"{montant(8_000 + p['charges_patronales'])}.\n\nDemande-moi « bulletin de paie 8000 » ou « salaire net "
            "6000 → brut » pour le détail ligne par ligne.")


def _impots():
    lignes = "\n".join(f"- **{impot}** : par exemple {exemples[0]}" for impot, exemples in K.QUEL_IMPOT.items())
    return ("## 🏛️ Les impôts au Maroc\n\n"
            "**Impôts de l'État** (Code général des impôts) : IS sur le bénéfice des sociétés (20 % / 35 %), IR sur les "
            "revenus des personnes (barème 0 à 37 %), TVA sur la consommation (20 % et 10 % depuis 2026), droits "
            "d'enregistrement et de timbre ; **impôts locaux** : taxe professionnelle, taxe d'habitation, taxe de "
            "services communaux ; **douane** : droits d'importation et taxes intérieures de consommation (TIC).\n\n"
            f"**À quel impôt s'attendre ?**\n{lignes}\n\nDemande-moi « parle de la TVA », « de l'IS » ou « de l'IR » "
            "pour le détail, ou donne-moi un montant à calculer.")


def _budget():
    b = K.BUDGET_ETAT_2026
    return ("## 🏦 Recettes et dépenses de l'État (loi de finances 2026)\n\n"
            f"- **Recettes ordinaires prévues** : {b['recettes_ordinaires']} milliards de DH, dont {b['recettes_non_fiscales']} "
            "de recettes non fiscales (le reste : impôts — TVA, IS, IR — et droits de douane).\n"
            f"- **Dépenses totales prévues** : {b['depenses_totales']} milliards de DH, dont {b['masse_salariale']} de masse "
            f"salariale et {b['investissement']} d'investissement.\n"
            f"- **Déficit prévu** : {b['deficit_prevu']} milliards de DH, soit **{b['deficit_pib']:.0f} % du PIB**.\n"
            f"- **Exécution à fin août 2026** (TGR) : recettes ordinaires {b['fin_aout_recettes']} milliards "
            f"(+{b['fin_aout_recettes_hausse']} %), déficit {b['fin_aout_deficit']} milliards (contre "
            f"{b['fin_aout_deficit_2025']} un an plus tôt).\n\n"
            "_Chiffres de la presse économique citant la TGR et le ministère des Finances, vérifiés le 30/10/2026._")


def _balance():
    c = K.BALANCE_COMMERCIALE_2025
    return ("## 🚢 La balance commerciale du Maroc (2025)\n\n"
            f"- **Importations** : {c['importations']} milliards de DH ; **exportations** : {c['exportations']} milliards.\n"
            f"- **Déficit commercial** : environ **{c['deficit']} milliards de DH** (+{c['deficit_hausse']} % sur un an, "
            f"contre {c['deficit_2024']} en 2024), soit {c['deficit_pib']} % du PIB.\n"
            f"- **Taux de couverture** (exportations / importations) : **{c['couverture']} %** (contre "
            f"{c['couverture_2024']} % en 2024).\n"
            "- **Ce qui progresse** : phosphates et dérivés (+13,8 %), aéronautique (+8,5 %) ; **ce qui recule** : "
            "automobile, textile, électronique ; le déficit vient surtout de la hausse des importations.\n"
            f"- **Compte courant** : environ {c['compte_courant']:.0f} milliards de DH (les transferts des Marocains du "
            "monde, le tourisme et les investissements étrangers compensent une partie du déficit commercial).\n\n"
            "_Chiffres de l'Office des changes repris par la presse économique, vérifiés le 30/10/2026._")


FICHES = [(re.compile(r"\btva\b|taxe sur la valeur|الضريبة على القيمة", re.I), _tva),
          (re.compile(r"\bis\b|impôt sur les sociétés|impot sur les societes|الضريبة على الشركات", re.I), _is),
          (re.compile(r"\bir\b|impôt sur le revenu|impot sur le revenu|الضريبة على الدخل", re.I), _ir),
          (re.compile(r"\b(paie|cnss|amo|bulletin de salaire|charges sociales)\b", re.I), _paie),
          (re.compile(r"(\bimp[ôo]ts?\b|fiscalit\w*|\btaxes\b|الضرائب)", re.I), _impots),
          (re.compile(r"(rec+et+es|d[ée]penses?\b.{0,25}([ée]tat|public)|budget de l.?[ée]tat|finances publiques|"
                      r"d[ée]ficit budg\w*|loi de finances|الميزانية)", re.I), _budget),
          (re.compile(r"(balance comm\w*|commerce ext[ée]rieur|importations|exportations|d[ée]ficit commercial|"
                      r"taux de couverture|الميزان التجاري)", re.I), _balance)]
GENERIQUES = set(mots("maroc marocain marocaine marocains etat general generale plan brievement bievement moi"))


MOTS_DES_SUJETS = set(mots("tva is ir paie cnss amo impot impots sur les societes revenu taxe la valeur ajoutee "
                            "le au du de des maroc marocaine charges sociales"))


def fiche_matiere(texte):
    """La matière dont parle la question (par son nom), présentée avec un exemple de chaque réponse."""
    q = {m for m in mots(texte) if len(m) > 3} - {"parle", "arle", "explique", "presente"} - GENERIQUES
    if not q:
        return None
    meilleure = max((m for m in MATIERES if m.exemples and m.cle != "orientation"),
                    key=lambda m: len(q & set(mots(f"{m.nom} {m.domaine}"))), default=None)
    communs = q & set(mots(f"{meilleure.nom} {meilleure.domaine}")) if meilleure else set()
    if not communs or len(communs) < min(2, len(q)):      # un seul mot vague (« marocain ») ne suffit pas
        return None
    lignes = "\n".join(f"- **{a}** : par exemple « {ex[0]} »" for a, ex in zip(meilleure.actions, meilleure.exemples) if ex)
    return f"## 🎓 {meilleure.nom} ({meilleure.domaine})\n\n{meilleure.note}\n\n{lignes}"


def fiche(texte, memoire=None, utilisateur=None):
    """Une fiche de synthèse si la question demande de parler d'un sujet connu ; sinon None. Renvoie (texte, sources)."""
    demande = bool(PARLER.search(texte))
    seul_le_sujet = not (set(mots(texte)) - MOTS_DES_SUJETS)    # « TVA ? », « la TVA au Maroc »
    if not (demande or seul_le_sujet):
        return None
    trouvees = [f for motif, f in FICHES if motif.search(texte)]
    if _impots in trouvees and len(trouvees) > 1 and any(f in trouvees for f in (_tva, _is, _ir)):
        trouvees.remove(_impots)                          # « la TVA » : la fiche précise suffit
    contenu = "\n\n".join(f() for f in trouvees) or (fiche_matiere(texte) if demande else None)
    if contenu is None:
        return None
    sources = ["base de connaissances marocaine (vérifiée le " + K.MISE_A_JOUR + ")"]
    if memoire is not None:
        from .lecture import repondre_par_lecture
        lu = repondre_par_lecture(texte, memoire, utilisateur, n=3, strict=True)
        if lu:
            contenu += "\n\n### 📚 Ce que disent mes lectures\n\n" + lu["reponse"]
            sources += lu["sources"]
    return contenu, sources
