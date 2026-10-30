"""
La suite des simulations : obligations et feuille de route, fiscalité, RH, comptabilité, banque, finance, technique,
bâtiment, immobilier, énergie, statistiques, études de projets et business plans.
"""

import datetime

import pandas as pd
import streamlit as st

from . import baremes as B
from . import decortiqueur as D
from . import obligations as O
from . import projets as P
from . import simulations as S
from .espace_simulations import CNSS_AMO, CODE_TRAVAIL, categorie_de, dh, pc
from .rapports import rapport


def liste(texte):
    return [float(v.replace(" ", "").replace(",", ".")) for v in texte.split(";") if v.strip()]


def construire_plus(nom, memoire, c):
    aujourdhui = datetime.date.today()
    # ------------------------------------------------------------------ Mes obligations
    if nom == "Mes impôts et déclarations (calendrier)":
        st.caption("Dites-moi qui vous êtes : je vous dis ce que vous payez, ce que vous déclarez, quand, et je vous "
                   "rappelle la prochaine échéance.")
        forme = c[0].selectbox("Vous êtes", O.FORMES, key="ob_forme")
        debut = c[1].date_input("Début d'activité", value=datetime.date(2024, 1, 1), key="ob_debut", format="DD/MM/YYYY")
        annee = c[2].number_input("Année", 2024, 2030, aujourdhui.year, key="ob_annee")
        c2 = st.columns(3)
        ca = c2[0].number_input("Chiffre d'affaires annuel HT (DH)", 0.0, value=1_500_000.0, step=50_000.0, key="ob_ca")
        benefice = c2[1].number_input("Bénéfice estimé (DH)", value=200_000.0, step=10_000.0, key="ob_ben")
        salaries = c2[2].number_input("Nombre de salariés", 0, 10_000, 2, key="ob_sal")
        c3 = st.columns(3)
        masse = c3[0].number_input("Masse salariale brute mensuelle (DH)", 0.0, value=12_000.0, step=1_000.0, key="ob_masse")
        is_prec = c3[1].number_input("IS de l'exercice précédent (DH)", 0.0, value=40_000.0, step=1_000.0, key="ob_isp",
                                     help="Sert à calculer les 4 acomptes provisionnels (25 % chacun).")
        tva = c3[2].number_input("TVA à payer par mois, estimée (DH)", 0.0, value=10_000.0, step=500.0, key="ob_tva")
        cal = O.calendrier(forme, annee, debut, ca, salaries if masse else 0, masse, is_prec, tva, aujourdhui)
        paie = O.ce_que_je_paie(forme, ca, benefice, debut, annee, salaries if masse else 0, masse)
        st.markdown("#### 💸 Ce que vous payez")
        st.dataframe(paie, hide_index=True, width="stretch")
        p = cal["prochaine"]
        if p:
            (st.error if p["jours"] < 15 else st.info)(f"⏰ Prochaine échéance dans **{p['jours']} jours** "
                                                        f"({p['Date limite']}) : {p['Obligation']} — {p['Base légale']}.")
        conseils = ["Payez et déclarez en ligne avant la date limite : un retard coûte une pénalité et une majoration "
                    "(voir la simulation « Pénalités de retard »).",
                    "Mettez de côté chaque mois la TVA collectée et les retenues des salariés : cet argent n'est pas à "
                    "vous, vous le reversez à l'État."]
        if forme.startswith("Société") and (annee - debut.year) * 12 + 12 - debut.month + 1 <= 36:
            conseils.append("Société de moins de 36 mois : exonérée de la cotisation minimale (CGI, art. 144).")
        if ca >= O.SEUIL_TVA_MENSUELLE and not forme.endswith("auto-entrepreneur"):
            conseils.append("Chiffre d'affaires d'au moins 1 000 000 DH : TVA déclarée chaque mois (CGI, art. 108).")
        if forme.endswith("auto-entrepreneur") and ca > 200_000:
            conseils.append("⚠️ Au-delà de 200 000 DH en services (500 000 DH en commerce) deux années de suite, le "
                            "statut d'auto-entrepreneur est perdu : préparez le passage au réel ou en société.")
        return rapport(nom, categorie_de(nom), {"Statut": forme, "Début d'activité": debut.strftime("%d/%m/%Y"),
                                                "Année": annee, "Chiffre d'affaires HT": dh(ca), "Salariés": salaries},
                       {"Échéances dans l'année": cal["nombre"], "Montant total estimé à verser": dh(cal["total_estime"]),
                        "Prochaine échéance": f"{p['Date limite']} — {p['Obligation']}" if p else "aucune cette année"},
                       ["Chaque échéance est datée selon le texte qui la fixe (colonne « Base légale »).",
                        "Montants estimés à partir de vos chiffres : CNSS et AMO selon les taux 2026, IR des salariés "
                        "selon le barème 2026, acomptes d'IS = 25 % de l'IS de l'exercice précédent.",
                        "TVA : mensuelle à partir de 1 000 000 DH de chiffre d'affaires, trimestrielle sinon et "
                        "l'année du début d'activité."],
                       ["CGI : art. 20 (déclaration IS), 79 (état des salaires), 82 (IR), 108 à 111 (TVA), 144 "
                        "(cotisation minimale), 155 (télédéclaration), 156 et 174 (retenue à la source), 170 "
                        "(acomptes et liquidation de l'IS)", CNSS_AMO, "Loi n° 47-06 relative à la fiscalité locale",
                        "Loi n° 9-88 relative aux obligations comptables", f"Vérifié le {B.VERIFIE_LE}"], annee,
                       tableau=cal["tableau"], remarques=["Non traités : exercice décalé, zones d'accélération "
                       "industrielle, exportateurs, retenues à la source sur honoraires et loyers, droits de timbre, "
                       "taxes sectorielles."], conseils=conseils)
    if nom == "Feuille de route du débutant":
        st.caption("Vous ne savez rien ? Suivez les étapes une par une. Cochez ce qui est fait : je vous dis ce qui "
                   "reste, et par quoi commencer.")
        faits = []
        for etape, quoi, base in O.FEUILLE_DE_ROUTE:
            if st.checkbox(f"**{etape}** — {quoi}", key=f"fr_{etape}"):
                faits.append(etape)
            st.caption(f"📜 {base}")
        restantes = [e for e, _, _ in O.FEUILLE_DE_ROUTE if e not in faits]
        conseils = ([f"👉 Votre prochaine étape : **{restantes[0]}**."] if restantes else
                    ["✅ Toutes les étapes sont faites : ouvrez « Mes impôts et déclarations (calendrier) » pour suivre "
                     "vos échéances."])
        if "5. Tenir une comptabilité" in restantes and len(faits) >= 2:
            conseils.append("⚠️ Sans comptabilité, impossible de déclarer correctement : c'est l'étape à ne pas reporter.")
        tableau = pd.DataFrame([{"Étape": e, "Ce qu'il faut faire": q, "Base légale": b,
                                 "Fait": "✅" if e in faits else "⬜"} for e, q, b in O.FEUILLE_DE_ROUTE])
        return rapport(nom, categorie_de(nom), {"Étapes cochées": len(faits)},
                       {"Avancement": f"{len(faits)}/{len(O.FEUILLE_DE_ROUTE)}",
                        "Prochaine étape": restantes[0] if restantes else "aucune"},
                       ["Ordre des étapes : statut, création, banque, télédéclaration, comptabilité, salariés, "
                        "calendrier, conservation."],
                       [b for _, _, b in O.FEUILLE_DE_ROUTE], aujourdhui.year, tableau=tableau, conseils=conseils)
    # ------------------------------------------------------------------ Fiscalité
    if nom == "Retenue sur dividendes":
        montant = c[0].number_input("Dividendes bruts distribués (DH)", 0.0, value=100_000.0, step=5_000.0, key="dv_m")
        annee = c[1].selectbox("Année de distribution", sorted(S.RAS_DIVIDENDES, reverse=True), key="dv_a")
        x = S.retenue_dividendes(montant, annee)
        return rapport(nom, categorie_de(nom), {"Dividendes bruts": dh(montant), "Année": annee},
                       {"Taux de retenue": pc(x["taux"]), "Retenue à la source": dh(x["retenue"]),
                        "Dividende net perçu": dh(x["net"])},
                       ["Retenue = dividendes bruts × taux de l'année ; elle est libératoire de l'IR pour l'associé "
                        "personne physique résidente.",
                        "Taux : 15 % (2013-2022), 13,75 % (2023), 12,5 % (2024 et 2025), 11,25 % (2026), 10 % à partir "
                        "de 2027 ; le taux dépend de la date de mise en distribution (LF 2025)."],
                       ["CGI, art. 13, 19-IV, 73-II et 247-XXXVII-C ; lois de finances 2023 et 2025",
                        "Versement par la société distributrice avant la fin du mois suivant la mise en distribution "
                        "(CGI, art. 174)", f"Vérifié le {B.VERIFIE_LE}"], annee,
                       remarques=["Non traités : conventions fiscales pour les non-résidents, sociétés soumises à l'IS "
                                  "bénéficiaires (abattement de 100 %)."],
                       conseils=["Comparez dividende et rémunération du dirigeant : la rémunération est déductible de "
                                 "l'IS mais supporte l'IR et les cotisations ; le dividende supporte l'IS puis la retenue."])
    if nom == "Pénalités de retard (IS, TVA, IR)":
        montant = c[0].number_input("Impôt payé en retard (DH)", 0.0, value=50_000.0, step=1_000.0, key="pr_m")
        echeance = c[1].date_input("Date limite légale", value=datetime.date(2026, 3, 31), key="pr_e", format="DD/MM/YYYY")
        paiement = c[2].date_input("Date du paiement", value=datetime.date(2026, 6, 15), key="pr_p", format="DD/MM/YYYY")
        jours = max(0, (paiement - echeance).days)
        x = S.penalites_retard(montant, 0, jours)
        return rapport(nom, categorie_de(nom), {"Impôt": dh(montant), "Date limite": echeance.strftime("%d/%m/%Y"),
                                                "Payé le": paiement.strftime("%d/%m/%Y")},
                       {"Retard": f"{jours} jours ({x['mois']} mois ou fraction)", "Pénalité": f"{dh(x['penalite'])} "
                        f"({pc(x['taux_penalite'])})", "Majoration de retard": f"{dh(x['majoration'])} "
                        f"({pc(x['taux_majoration'])})", "Surcoût total": dh(x["surcout"]), "Total à payer": dh(x["total"])},
                       ["Pénalité : 10 % du montant, réduite à 5 % si le retard ne dépasse pas 30 jours.",
                        "Majoration : 5 % pour le premier mois de retard, plus 0,50 % par mois ou fraction de mois "
                        "supplémentaire."],
                       ["CGI, art. 208 (sanctions pour paiement tardif)", "CGI, art. 184 (défaut ou retard de déclaration)",
                        f"Vérifié le {B.VERIFIE_LE}"], echeance.year,
                       remarques=["Un défaut de déclaration (et non seulement de paiement) entraîne en plus les sanctions "
                                  "de l'art. 184 : non cumulées ici.", "Une remise gracieuse peut être demandée à "
                                  "l'administration (CGI, art. 236)."],
                       conseils=[f"Chaque mois de retard en plus coûte {dh(montant * 0.005)} : régularisez au plus vite.",
                                 "Si vous ne pouvez pas payer, déposez quand même la déclaration à temps : les sanctions "
                                 "de défaut de déclaration sont évitées."])
    # ------------------------------------------------------------------ RH
    if nom == "Masse salariale et augmentation":
        effectif = c[0].number_input("Effectif", 1, 100_000, 10, key="ms_n")
        base = c[1].number_input("Salaire de base mensuel (DH)", 0.0, value=6_000.0, step=250.0, key="ms_b")
        anc = c[2].number_input("Ancienneté moyenne (ans)", 0, 45, 3, key="ms_a")
        c2 = st.columns(3)
        aug = c2[0].number_input("Augmentation envisagée (%)", 0.0, 50.0, 5.0, 0.5, key="ms_aug") / 100
        mois = c2[1].selectbox("Mois payés par an", [12, 13, 14], key="ms_mois")
        x = S.masse_salariale(effectif, base, anc, mois, aug)
        ratio = x["gain_net_salarie"] / (x["surcout"] / effectif) if x["surcout"] else 0
        return rapport(nom, categorie_de(nom), {"Effectif": effectif, "Salaire de base": dh(base), "Ancienneté": f"{anc} ans",
                                                "Augmentation": pc(aug), "Mois payés": mois},
                       {"Coût annuel actuel": dh(x["cout_annuel"]), "Coût annuel après augmentation": dh(x["cout_annuel_apres"]),
                        "Surcoût pour l'entreprise": dh(x["surcout"]),
                        "Gain net annuel par salarié": dh(x["gain_net_salarie"])},
                       ["Chaque salarié : bulletin complet 2026 (prime d'ancienneté, CNSS, AMO, IR, charges patronales).",
                        "Coût annuel = coût employeur mensuel × effectif × mois payés."],
                       [f"{CODE_TRAVAIL}, art. 350 (ancienneté)", CNSS_AMO, "CGI, art. 59 et 73"], 2026,
                       tableau=x["tableau"],
                       conseils=[f"Pour 1 DH de surcoût, le salarié gagne {ratio:.2f} DH net : comparez avec des "
                                 "avantages exonérés et justifiés (transport, panier) ou une prime d'objectif.",
                                 "Étalez l'augmentation sur l'année si la trésorerie est tendue (voir « Trésorerie sur "
                                 "12 mois »)."])
    if nom == "Retraite CNSS (pension)":
        salaire = c[0].number_input("Salaire moyen mensuel des 96 derniers mois (DH)", 0.0, value=5_000.0, step=250.0, key="rt_s")
        jours = c[1].number_input("Jours déclarés à la CNSS", 0, 20_000, 5_000, key="rt_j")
        x = S.pension_cnss(salaire, jours)
        if not x["eligible"]:
            conseils = [f"Il manque {x['jours_manquants']} jours pour avoir droit à la pension (3 240 jours minimum) ; à "
                        "défaut, remboursement des cotisations salariales et patronales sur demande (selon les textes en vigueur)."]
        else:
            conseils = ([f"Encore {x['jours_pour_70']} jours (≈ {x['jours_pour_70'] / 312:.1f} ans) pour atteindre le taux "
                         "maximal de 70 %."] if x["jours_pour_70"] else ["Taux maximal de 70 % atteint."])
        if salaire > 6_000:
            conseils.append("Salaire au-dessus du plafond CNSS de 6 000 DH : la part au-delà ne compte pas — une retraite "
                            "complémentaire (CIMR ou contrat d'assurance) est nécessaire pour maintenir le niveau de vie.")
        return rapport(nom, categorie_de(nom), {"Salaire moyen": dh(salaire), "Jours déclarés": jours},
                       {"Droit à pension": "oui" if x["eligible"] else "non", "Salaire de référence (plafonné)": dh(x["base"]),
                        "Taux de pension": pc(x["taux"]), "Pension mensuelle estimée": dh(x["pension"])},
                       ["Droit à pension : 3 240 jours de cotisation au moins, à l'âge légal.",
                        "Taux : 50 % pour 3 240 jours, + 1 % par tranche de 216 jours supplémentaires, au plus 70 %.",
                        "Salaire de référence : moyenne des salaires des 96 derniers mois, plafonnée à 6 000 DH."],
                       ["Dahir portant loi n° 1-72-184 relatif au régime de sécurité sociale, art. 53 et suivants"],
                       2026, remarques=["Non traités : pension minimale, revalorisations, réforme en cours des retraites, "
                                        "rachat de périodes."], conseils=conseils)
    # ------------------------------------------------------------------ Comptabilité
    if nom == "Ratios financiers (bilan)":
        ac = c[0].number_input("Actif circulant (DH)", 0.0, value=800_000.0, step=10_000.0, key="ra_ac")
        stocks = c[1].number_input("dont stocks (DH)", 0.0, value=250_000.0, step=10_000.0, key="ra_st")
        tres = c[2].number_input("Trésorerie actif (DH)", 0.0, value=100_000.0, step=10_000.0, key="ra_tr")
        c2 = st.columns(3)
        dct = c2[0].number_input("Dettes à court terme (DH)", 0.0, value=600_000.0, step=10_000.0, key="ra_dct")
        cp = c2[1].number_input("Capitaux propres (DH)", value=700_000.0, step=10_000.0, key="ra_cp")
        df = c2[2].number_input("Dettes de financement (DH)", 0.0, value=500_000.0, step=10_000.0, key="ra_df")
        c3 = st.columns(3)
        ca = c3[0].number_input("Chiffre d'affaires (DH)", 0.0, value=3_000_000.0, step=50_000.0, key="ra_ca")
        rn = c3[1].number_input("Résultat net (DH)", value=150_000.0, step=10_000.0, key="ra_rn")
        total = c3[2].number_input("Total du bilan (DH)", 0.0, value=1_800_000.0, step=10_000.0, key="ra_tot")
        x = S.ratios_financiers(ac, stocks, tres, dct, cp, df, ca, rn, total)
        actions = {"Liquidité générale": "renforcez le fonds de roulement (apport, emprunt à long terme au lieu du découvert)",
                   "Liquidité réduite": "réduisez les stocks dormants ou négociez des délais fournisseurs",
                   "Liquidité immédiate": "gardez un matelas de trésorerie ou une facilité de caisse négociée",
                   "Autonomie financière": "renforcez les fonds propres (mise en réserve, augmentation de capital)",
                   "Endettement (gearing)": "limitez les nouveaux emprunts, remboursez par anticipation les plus chers",
                   "Marge nette": "analysez le coût de revient (voir « Coût de revient complet ») et vos prix",
                   "Rentabilité des fonds propres (ROE)": "améliorez la marge ou la rotation des actifs"}
        conseils = [f"⚠️ {f} : {actions[f]}." for f in x["faibles"]] or ["Tous les ratios sont dans les repères usuels."]
        return rapport(nom, categorie_de(nom), {"Actif circulant": dh(ac), "Stocks": dh(stocks), "Trésorerie": dh(tres),
                                                "Dettes à court terme": dh(dct), "Capitaux propres": dh(cp),
                                                "Dettes de financement": dh(df), "Chiffre d'affaires": dh(ca),
                                                "Résultat net": dh(rn), "Total du bilan": dh(total)},
                       {k: ("—" if v is None else f"{v:.2f}" if "Liquidité" in k or "gearing" in k else pc(v))
                        for k, v in x["ratios"].items()},
                       ["Liquidité générale = actif circulant ÷ dettes à court terme ; réduite : sans les stocks ; "
                        "immédiate : trésorerie seule.", "Autonomie = capitaux propres ÷ total du bilan ; gearing = "
                        "dettes de financement ÷ capitaux propres.", "Marge nette = résultat net ÷ CA ; ROE = résultat "
                        "net ÷ capitaux propres."],
                       ["Bilan et CPC du modèle normal du CGNC (loi n° 9-88)", "Analyse financière (repères usuels des "
                        "banques et analystes, à adapter au secteur)"], tableau=x["tableau"], conseils=conseils)
    if nom == "Coût de revient complet":
        mat = c[0].number_input("Matières consommées (DH)", 0.0, value=400_000.0, step=10_000.0, key="cv_m")
        mod = c[1].number_input("Main-d'œuvre directe (DH)", 0.0, value=250_000.0, step=10_000.0, key="cv_mo")
        ind = c[2].number_input("Charges indirectes (DH)", 0.0, value=150_000.0, step=10_000.0, key="cv_i")
        c2 = st.columns(3)
        dist = c2[0].number_input("Frais de distribution (DH)", 0.0, value=50_000.0, step=5_000.0, key="cv_d")
        q = c2[1].number_input("Quantité produite et vendue", 1, 10_000_000, 10_000, key="cv_q")
        pv = c2[2].number_input("Prix de vente unitaire HT (DH)", 0.0, value=100.0, step=1.0, key="cv_pv")
        x = S.cout_de_revient(mat, mod, ind, dist, q, pv)
        conseils = [f"Le premier poste est « {x['poste_principal']} » : c'est là qu'un gain de 5 % rapporte le plus "
                    f"({dh(x['tableau']['Montant'].max() * 0.05)}).",
                    "Prix inférieur au coût de revient : chaque vente détruit de la marge — revoyez le prix ou le procédé."
                    if x["marge_unitaire"] < 0 else f"Marge unitaire {dh(x['marge_unitaire'])} ({pc(x['taux_marge'])} du prix)."]
        return rapport(nom, categorie_de(nom), {"Matières": dh(mat), "Main-d'œuvre directe": dh(mod),
                                                "Charges indirectes": dh(ind), "Distribution": dh(dist), "Quantité": q,
                                                "Prix de vente unitaire": dh(pv)},
                       {"Coût de revient total": dh(x["total"]), "Coût de revient unitaire": dh(x["unitaire"]),
                        "Marge unitaire": dh(x["marge_unitaire"]), "Taux de marge sur prix": pc(x["taux_marge"])},
                       ["Coût de revient = coût de production (matières + main-d'œuvre directe + charges indirectes) "
                        "+ coûts hors production (distribution).", "Unitaire = total ÷ quantité."],
                       ["Comptabilité analytique (méthode des coûts complets, CGNC)"], tableau=x["tableau"],
                       remarques=["Charges indirectes réparties globalement : pour plusieurs produits, utilisez des "
                                  "unités d'œuvre (sections homogènes) ou la méthode ABC."], conseils=conseils)
    # ------------------------------------------------------------------ Banque
    if nom == "TEG d'un crédit":
        capital = c[0].number_input("Capital (DH)", 0.0, value=200_000.0, step=10_000.0, key="teg_c")
        taux = c[1].number_input("Taux nominal annuel (%)", 0.0, 30.0, 6.0, 0.1, key="teg_t") / 100
        mois = c[2].number_input("Durée (mois)", 1, 360, 120, key="teg_n")
        c2 = st.columns(2)
        frais = c2[0].number_input("Frais de dossier (DH)", 0.0, value=2_000.0, step=100.0, key="teg_f")
        ass = c2[1].number_input("Assurance (DH/mois)", 0.0, value=60.0, step=5.0, key="teg_a")
        x = S.taux_effectif_global(capital, taux, mois, frais, ass)
        return rapport(nom, categorie_de(nom), {"Capital": dh(capital), "Taux nominal": pc(taux), "Durée": f"{mois} mois",
                                                "Frais de dossier": dh(frais), "Assurance": dh(ass) + "/mois"},
                       {"Mensualité totale": dh(x["mensualite_totale"]), "TEG": pc(x["teg"]),
                        "Écart avec le taux nominal": f"{(x['teg'] - taux) * 100:.2f} points",
                        "Coût total du crédit": dh(x["cout_total"])},
                       ["Le TEG est le taux annuel t tel que : capital − frais = Σ (mensualité + assurance) ÷ (1 + t/12)^k.",
                        "Résolu par dichotomie (précision < 0,0001 %)."],
                       ["Loi n° 31-08 édictant des mesures de protection du consommateur (art. 75 et suivants : TEG)",
                        "Plafond : taux maximum des intérêts conventionnels fixé par Bank Al-Maghrib"],
                       tableau=pd.DataFrame([{"Composante": "Intérêts", "Montant": round(x["cout_total"] - frais - ass * mois, 2)},
                                             {"Composante": "Frais de dossier", "Montant": frais},
                                             {"Composante": "Assurance", "Montant": round(ass * mois, 2)}]),
                       conseils=["Comparez les offres sur le TEG, jamais sur le seul taux nominal.",
                                 "Une assurance déléguée (autre assureur) peut réduire le coût : demandez si la banque "
                                 "l'accepte."])
    if nom == "Leasing ou crédit":
        prix = c[0].number_input("Prix HT du bien (DH)", 0.0, value=300_000.0, step=10_000.0, key="lc_p")
        loyer = c[1].number_input("Loyer de leasing HT (DH/mois)", 0.0, value=7_000.0, step=100.0, key="lc_l")
        mois = c[2].number_input("Durée (mois)", 12, 120, 48, key="lc_n")
        c2 = st.columns(4)
        vr = c2[0].number_input("Valeur résiduelle (DH)", 0.0, value=3_000.0, step=500.0, key="lc_vr")
        tc = c2[1].number_input("Taux du crédit (%)", 0.0, 20.0, 6.0, 0.1, key="lc_tc") / 100
        tis = c2[2].selectbox("Taux d'IS", [0.20, 0.35], format_func=pc, key="lc_is")
        ta = c2[3].number_input("Taux d'actualisation (%)", 0.0, 30.0, 8.0, 0.5, key="lc_ta") / 100
        x = S.leasing_ou_credit(prix, loyer, mois, vr, tc, tis, ta)
        return rapport(nom, categorie_de(nom), {"Prix HT": dh(prix), "Loyer": dh(loyer), "Durée": f"{mois} mois",
                                                "Valeur résiduelle": dh(vr), "Taux du crédit": pc(tc), "IS": pc(tis),
                                                "Actualisation": pc(ta)},
                       {"Coût actualisé du leasing (après IS)": dh(x["leasing"]),
                        "Coût actualisé du crédit (après IS)": dh(x["credit"]), "Solution la moins chère": x["meilleur"],
                        "Écart": dh(x["ecart"])},
                       ["Leasing : loyers déductibles (économie d'IS), plus la levée d'option en fin de contrat.",
                        "Crédit : mensualités, moins l'économie d'IS sur les intérêts et les amortissements (linéaire "
                        "sur la durée).", "Tous les flux sont actualisés mensuellement."],
                       ["CGI, art. 10 (charges déductibles : loyers de crédit-bail, intérêts, amortissements)",
                        "Loi n° 103-12 relative aux établissements de crédit (crédit-bail)"],
                       remarques=["TVA supposée récupérable. Pour un véhicule de tourisme, la déduction est plafonnée "
                                  "(300 000 DH TTC) dans les deux cas."],
                       conseils=["Le leasing préserve la trésorerie et l'endettement apparent ; le crédit donne la "
                                 "propriété immédiate. Négociez le loyer et l'option d'achat.",
                                 "Refaites le calcul avec votre vrai taux d'actualisation (coût de vos ressources)."])
    # ------------------------------------------------------------------ Finance
    if nom == "Valorisation d'entreprise (DCF)":
        flux = c[0].text_input("Flux de trésorerie disponibles prévus (;)", "500000; 550000; 600000; 650000; 700000", key="vd_f")
        taux = c[1].number_input("Coût du capital (%)", 1.0, 40.0, 12.0, 0.5, key="vd_t") / 100
        g = c[2].number_input("Croissance à l'infini (%)", -5.0, 10.0, 2.0, 0.5, key="vd_g") / 100
        dette = st.number_input("Dette nette (DH)", value=1_000_000.0, step=50_000.0, key="vd_d")
        try:
            f = liste(flux)
        except ValueError:
            st.error("Écris les flux comme ceci : 500000; 550000; 600000")
            return None
        if not f or taux <= g:
            st.error("Il faut au moins un flux, et un coût du capital supérieur à la croissance à l'infini.")
            return None
        x = S.valorisation_dcf(f, taux, g, dette)
        conseils = [f"La valeur terminale pèse {pc(x['part_terminale'])} de la valeur : "
                    + ("très sensible aux hypothèses de long terme, testez plusieurs taux." if x["part_terminale"] > 0.6
                       else "la valeur repose surtout sur les années prévues."),
                    "Croisez avec une méthode des multiples (comparables du secteur) avant toute négociation."]
        return rapport(nom, categorie_de(nom), {"Flux": flux, "Coût du capital": pc(taux), "Croissance à l'infini": pc(g),
                                                "Dette nette": dh(dette)},
                       {"Valeur d'entreprise": dh(x["valeur_entreprise"]),
                        "Valeur terminale actualisée": dh(x["valeur_terminale_actualisee"]),
                        "Valeur des titres (fonds propres)": dh(x["valeur_titres"])},
                       ["Valeur d'entreprise = Σ flux ÷ (1 + k)^n + valeur terminale actualisée.",
                        "Valeur terminale = dernier flux × (1 + g) ÷ (k − g) (Gordon-Shapiro).",
                        "Valeur des titres = valeur d'entreprise − dette nette."],
                       ["Méthode des flux de trésorerie actualisés (DCF), finance d'entreprise"], tableau=x["tableau"],
                       conseils=conseils)
    if nom == "Effet de levier financier":
        re = c[0].number_input("Résultat d'exploitation (DH)", value=300_000.0, step=10_000.0, key="el_re")
        ae = c[1].number_input("Actif économique (DH)", 1.0, value=2_000_000.0, step=50_000.0, key="el_ae")
        d = c[2].number_input("Dette financière (DH)", 0.0, value=1_000_000.0, step=50_000.0, key="el_d")
        c2 = st.columns(2)
        i = c2[0].number_input("Taux d'intérêt (%)", 0.0, 30.0, 6.0, 0.1, key="el_i") / 100
        tis = c2[1].selectbox("Taux d'IS", [0.20, 0.35], format_func=pc, key="el_is")
        x = S.effet_de_levier(re, ae, d, i, tis)
        return rapport(nom, categorie_de(nom), {"Résultat d'exploitation": dh(re), "Actif économique": dh(ae),
                                                "Dette": dh(d), "Taux d'intérêt": pc(i), "IS": pc(tis)},
                       {"Rentabilité économique (avant IS)": pc(x["rentabilite_economique"]),
                        "Levier (dette ÷ fonds propres)": x["levier"] if x["levier"] is not None else "fonds propres ≤ 0",
                        "Rentabilité financière (après IS)": pc(x["rentabilite_financiere"]) if x["rentabilite_financiere"] is not None else "—",
                        "Effet de levier": "favorable" if x["favorable"] else "défavorable (effet de massue)"},
                       ["Rentabilité financière = [Re + (Re − i) × D ÷ CP] × (1 − IS)."],
                       ["Formule de l'effet de levier (analyse financière)"],
                       conseils=["Tant que la rentabilité économique dépasse le taux d'intérêt, l'endettement augmente "
                                 "la rentabilité des fonds propres — mais aussi le risque."
                                 if x["favorable"] else "Le coût de la dette dépasse la rentabilité économique : chaque "
                                 "dirham emprunté réduit la rentabilité ; désendettez ou améliorez la marge."])
    # ------------------------------------------------------------------ Technique
    if nom == "Section de câble électrique":
        p = c[0].number_input("Puissance (W)", 1.0, value=3_000.0, step=100.0, key="sc_p")
        tri = c[1].radio("Réseau", ["Monophasé 220 V", "Triphasé 380 V"], key="sc_r") == "Triphasé 380 V"
        l = c[2].number_input("Longueur du câble (m)", 1.0, value=30.0, step=1.0, key="sc_l")
        c2 = st.columns(3)
        usage = c2[0].selectbox("Usage", ["Autres usages (5 %)", "Éclairage (3 %)"], key="sc_u")
        cuivre = c2[1].radio("Conducteur", ["Cuivre", "Aluminium"], key="sc_c") == "Cuivre"
        cos = c2[2].number_input("cos φ", 0.5, 1.0, 1.0 if not tri else 0.85, 0.01, key="sc_cos")
        chute = 0.03 if usage.startswith("Éclairage") else 0.05
        x = S.section_cable(p, 380 if tri else 220, l, chute, tri, cuivre, cos)
        return rapport(nom, categorie_de(nom), {"Puissance": f"{p:g} W", "Réseau": "triphasé 380 V" if tri else "monophasé 220 V",
                                                "Longueur": f"{l:g} m", "Chute admise": pc(chute),
                                                "Conducteur": "cuivre" if cuivre else "aluminium"},
                       {"Courant": f"{x['courant']} A", "Section minimale calculée": f"{x['section_calculee']} mm²",
                        "Section normalisée retenue": f"{x['section_normalisee']} mm²" if x["section_normalisee"] else "au-delà de 240 mm²",
                        "Chute de tension réelle": pc(x["chute_reelle"]) if x["chute_reelle"] else "—"},
                       ["I = P ÷ (U × cos φ) en monophasé, P ÷ (√3 × U × cos φ) en triphasé.",
                        "S = b × ρ × L × I × cos φ ÷ (ΔU), b = 2 (monophasé) ou 1 (triphasé), ρ = 0,0225 (cuivre) "
                        "ou 0,036 Ω·mm²/m (aluminium)."],
                       ["Règles de chute de tension de la norme NF C 15-100 (référence des installations au Maroc) : "
                        "3 % éclairage, 5 % autres usages"],
                       remarques=["Vérifiez aussi le courant admissible (mode de pose, température) et le calibre de la "
                                  "protection : la section retenue est la plus grande des deux exigences."],
                       conseils=["Faites valider par un électricien qualifié : une section trop faible chauffe et présente "
                                 "un risque d'incendie."])
    if nom == "Pompe (puissance et coût)":
        q = c[0].number_input("Débit (m³/h)", 0.1, value=10.0, step=0.5, key="pp_q")
        h = c[1].number_input("Hauteur manométrique totale (m)", 1.0, value=40.0, step=1.0, key="pp_h")
        r = c[2].number_input("Rendement groupe moto-pompe (%)", 10.0, 95.0, 60.0, 1.0, key="pp_r") / 100
        c2 = st.columns(2)
        hj = c2[0].number_input("Heures de marche par jour", 0.0, 24.0, 8.0, 0.5, key="pp_hj")
        px = c2[1].number_input("Prix du kWh (DH)", 0.0, value=1.2, step=0.05, key="pp_px")
        x = S.puissance_pompe(q, h, r, hj, px)
        return rapport(nom, categorie_de(nom), {"Débit": f"{q:g} m³/h", "HMT": f"{h:g} m", "Rendement": pc(r),
                                                "Marche": f"{hj:g} h/jour", "Prix du kWh": dh(px)},
                       {"Puissance hydraulique": f"{x['p_hydraulique_kw']} kW", "Puissance absorbée": f"{x['p_absorbee_kw']} kW",
                        "Énergie par an": f"{x['energie_an_kwh']:,.0f} kWh".replace(",", " "), "Coût par an": dh(x["cout_an"])},
                       ["P hydraulique = ρ × g × Q × H (ρ = 1 000 kg/m³, g = 9,81 m/s²) ; P absorbée = P hydraulique ÷ rendement."],
                       ["Mécanique des fluides (puissance hydraulique)"],
                       conseils=["Une pompe solaire ou à variation de vitesse réduit fortement la facture en irrigation : "
                                 "comparez avec la simulation photovoltaïque.",
                                 "Choisissez une pompe dont le point de fonctionnement est proche de son meilleur rendement."])
    # ------------------------------------------------------------------ Bâtiment
    if nom == "Ferraillage (poids d'acier)":
        txt = c[0].text_area("Barres : diamètre (mm), nombre, longueur (m) — une ligne par type",
                             "12, 40, 6\n10, 60, 4.5\n8, 120, 1.2", key="fe_t")
        prix = c[1].number_input("Prix de l'acier (DH/kg)", 0.0, value=11.0, step=0.5, key="fe_p")
        try:
            barres = [tuple(float(v) for v in l.split(",")) for l in txt.splitlines() if l.strip()]
            assert all(len(b) == 3 for b in barres)
        except (ValueError, AssertionError):
            st.error("Écris une ligne par type de barre : diamètre, nombre, longueur (ex. 12, 40, 6)")
            return None
        x = S.ferraillage(barres)
        return rapport(nom, categorie_de(nom), {"Barres": txt.replace("\n", " ; "), "Prix": dh(prix) + "/kg"},
                       {"Masse d'acier": f"{x['masse']:,.1f} kg".replace(",", " "), "Avec 5 % de chutes": f"{x['masse'] * 1.05:,.1f} kg".replace(",", " "),
                        "Coût estimé": dh(x["masse"] * 1.05 * prix)},
                       ["Masse linéique = d² ÷ 162 kg/m (acier de masse volumique 7 850 kg/m³).",
                        "Masse = nombre × longueur × masse linéique ; + 5 % de chutes et recouvrements."],
                       ["Physique des matériaux (acier pour béton armé, NM 01.4.096)"], tableau=x["tableau"],
                       conseils=["Les quantités viennent des plans d'un bureau d'études : ce calcul vérifie un métré, il "
                                 "ne dimensionne pas la structure (règlement parasismique RPS 2000)."])
    if nom == "Maçonnerie (blocs et mortier)":
        s_ = c[0].number_input("Surface des murs (m²)", 0.0, value=50.0, step=1.0, key="mc_s")
        o = c[1].number_input("Ouvertures à déduire (m²)", 0.0, value=6.0, step=0.5, key="mc_o")
        bloc = c[2].selectbox("Bloc", ["Parpaing 40 × 20 cm", "Brique 30 × 20 cm", "Brique 22 × 11 cm"], key="mc_b")
        dims = {"Parpaing 40 × 20 cm": (40, 20), "Brique 30 × 20 cm": (30, 20), "Brique 22 × 11 cm": (22, 11)}[bloc]
        x = S.maconnerie(s_, o, *dims)
        return rapport(nom, categorie_de(nom), {"Surface": f"{s_:g} m²", "Ouvertures": f"{o:g} m²", "Bloc": bloc},
                       {"Surface nette": f"{x['surface_nette']} m²", "Blocs par m²": x["par_m2"],
                        "Blocs à commander (+5 %)": x["blocs"], "Mortier": f"{x['mortier_m3']} m³",
                        "Ciment pour le mortier": f"{x['ciment_sacs']} sacs de 50 kg"},
                       ["Blocs par m² = 10 000 ÷ ((longueur + joint) × (hauteur + joint)), joint de 1 cm.",
                        "Mortier ≈ 0,02 m³ par m², dosé à 300 kg de ciment par m³."],
                       ["Règles de métré du bâtiment"],
                       conseils=["Commandez en une fois pour un même lot de fabrication (teinte et dimensions).",
                                 "Pour un mur porteur, suivez les plans et le règlement parasismique RPS 2000."])
    # ------------------------------------------------------------------ Immobilier
    if nom == "Frais d'acquisition immobilière":
        prix = c[0].number_input("Prix d'achat (DH)", 0.0, value=1_000_000.0, step=50_000.0, key="fa_p")
        notaire = c[1].number_input("Honoraires du notaire TTC (DH)", 0.0, value=12_000.0, step=500.0, key="fa_n",
                                    help="Demandez le montant exact à votre notaire.")
        fixes = c[2].number_input("Frais fixes (timbres, certificats) (DH)", 0.0, value=1_500.0, step=100.0, key="fa_f")
        x = S.frais_acquisition(prix, 0.04, 0.015, fixes, notaire)
        return rapport(nom, categorie_de(nom), {"Prix": dh(prix), "Notaire": dh(notaire), "Frais fixes": dh(fixes)},
                       {"Droits d'enregistrement (4 %)": dh(x["enregistrement"]),
                        "Conservation foncière (1,5 %)": dh(x["conservation"]), "Total des frais": dh(x["total"]),
                        "Part des frais": pc(x["part"]), "Coût complet de l'achat": dh(x["cout_complet"])},
                       ["Droits d'enregistrement = 4 % du prix ; conservation foncière = 1,5 % du prix ; + notaire et frais fixes."],
                       ["CGI, art. 133-I-F (droits d'enregistrement de 4 % sur les acquisitions immobilières)",
                        "Tarif de la conservation foncière (ANCFCC)", f"Vérifié le {B.VERIFIE_LE}"], 2026,
                       remarques=["Non traités : taux réduits ou exonérations (logement social, premier logement selon "
                                  "la loi de finances de l'année, terrains destinés à la construction)."],
                       conseils=["Prévoyez ces frais dans l'apport : les banques financent rarement les frais d'acquisition.",
                                 "Vérifiez l'éligibilité aux aides au logement de l'année avant de signer."])
    if nom == "Acheter ou louer":
        prix = c[0].number_input("Prix du bien (DH)", 0.0, value=1_000_000.0, step=50_000.0, key="al_p")
        apport = c[1].number_input("Apport (DH)", 0.0, value=200_000.0, step=10_000.0, key="al_a")
        loyer = c[2].number_input("Loyer équivalent (DH/mois)", 0.0, value=4_500.0, step=100.0, key="al_l")
        c2 = st.columns(4)
        taux = c2[0].number_input("Taux du crédit (%)", 0.0, 20.0, 5.0, 0.1, key="al_t") / 100
        ans = c2[1].number_input("Durée (ans)", 5, 30, 20, key="al_n")
        valo = c2[2].number_input("Valorisation du bien (%/an)", -5.0, 15.0, 2.0, 0.5, key="al_v") / 100
        place = c2[3].number_input("Rendement d'un placement (%/an)", 0.0, 15.0, 3.5, 0.5, key="al_r") / 100
        frais = S.frais_acquisition(prix)["total"]
        x = S.acheter_ou_louer(prix, frais, apport, taux, ans, loyer, 0.02, valo, place, prix * 0.005)
        return rapport(nom, categorie_de(nom), {"Prix": dh(prix), "Apport": dh(apport), "Loyer": dh(loyer),
                                                "Crédit": f"{pc(taux)} sur {ans} ans", "Valorisation": pc(valo),
                                                "Placement": pc(place)},
                       {"Mensualité": dh(x["mensualite"]), f"Patrimoine du propriétaire après {ans} ans": dh(x["patrimoine_proprietaire"]),
                        f"Patrimoine du locataire après {ans} ans": dh(x["patrimoine_locataire"]), "Plus avantageux": x["meilleur"]},
                       ["Propriétaire : paie mensualités et charges (0,5 % du prix par an), possède le bien valorisé.",
                        "Locataire : place l'apport et la différence entre l'effort du propriétaire et le loyer "
                        "(loyer + 2 % par an).", "Frais d'acquisition : 4 % + 1,5 % du prix (CGI, art. 133)."],
                       ["Mathématiques financières ; CGI, art. 133 ; loi n° 67-12 (baux d'habitation)"], tableau=x["tableau"],
                       conseils=["Le résultat dépend surtout de la valorisation du bien et de la durée de détention : "
                                 "testez une valorisation nulle avant de décider.",
                                 "Acheter pour revendre avant 5 ans est rarement gagnant : les frais d'acquisition pèsent."])
    # ------------------------------------------------------------------ Énergie
    if nom == "Chauffe-eau solaire":
        litres = c[0].number_input("Eau chaude par jour (litres)", 10.0, value=200.0, step=10.0, key="ce_l")
        cov = c[1].number_input("Couverture solaire (%)", 10.0, 100.0, 75.0, 5.0, key="ce_c") / 100
        prix = c[2].number_input("Prix du kWh d'appoint (DH)", 0.0, value=1.2, step=0.05, key="ce_p")
        c2 = st.columns(2)
        cout = c2[0].number_input("Coût de l'installation (DH)", 0.0, value=12_000.0, step=500.0, key="ce_k")
        x = S.chauffe_eau_solaire(litres, 15, 55, cov, prix, cout)
        return rapport(nom, categorie_de(nom), {"Eau chaude": f"{litres:g} L/jour", "Couverture solaire": pc(cov),
                                                "Prix du kWh": dh(prix), "Coût": dh(cout)},
                       {"Besoin annuel": f"{x['besoin_kwh_an']:,.0f} kWh".replace(",", " "), "Économie annuelle": dh(x["economie_an"]),
                        "Retour sur investissement": f"{x['retour_ans']} ans" if x["retour_ans"] else "—"},
                       ["Énergie = litres × 1,163 Wh/L/°C × (55 − 15) °C × 365 ÷ rendement de l'appoint (95 %).",
                        "Économie = énergie × couverture solaire × prix du kWh."],
                       ["Thermique (capacité calorifique de l'eau)", "Loi n° 47-09 relative à l'efficacité énergétique"],
                       conseils=["Au Maroc, une couverture de 70 à 80 % est courante : demandez la fiche technique "
                                 "certifiée de l'installateur.", "Si l'appoint est au gaz butane, refaites le calcul avec "
                                 "le prix du kWh gaz (le butane est encore subventionné)."])
    if nom == "Groupe électrogène":
        kva = c[0].number_input("Puissance (kVA)", 1.0, value=60.0, step=5.0, key="ge_k")
        charge = c[1].number_input("Charge moyenne (%)", 10.0, 100.0, 70.0, 5.0, key="ge_c") / 100
        h = c[2].number_input("Heures par jour", 0.5, 24.0, 6.0, 0.5, key="ge_h")
        c2 = st.columns(2)
        j = c2[0].number_input("Jours par an", 1, 365, 300, key="ge_j")
        gas = c2[1].number_input("Prix du gasoil (DH/L)", 0.0, value=12.0, step=0.1, key="ge_g")
        x = S.groupe_electrogene(kva, charge, h, j, gas)
        return rapport(nom, categorie_de(nom), {"Puissance": f"{kva:g} kVA", "Charge": pc(charge),
                                                "Marche": f"{h:g} h × {j} jours", "Gasoil": dh(gas) + "/L"},
                       {"Puissance débitée": f"{x['puissance_kw']} kW", "Gasoil par an": f"{x['litres_an']:,.0f} L".replace(",", " "),
                        "Coût du carburant par an": dh(x["cout_an"]), "Coût du kWh produit": dh(x["cout_kwh"])},
                       ["kW = kVA × cos φ (0,8) × charge ; gasoil ≈ 0,28 L par kWh produit (moteur diesel courant)."],
                       ["Fiches constructeurs des groupes diesel (consommation spécifique)"],
                       remarques=["Hors entretien, vidanges et amortissement du groupe."],
                       conseils=[f"Le kWh du groupe coûte {dh(x['cout_kwh'])} : comparez avec le réseau et avec le solaire "
                                 "pour les heures de jour.", "Un groupe sous-chargé consomme plus par kWh : dimensionnez au "
                                 "plus juste."])
    # ------------------------------------------------------------------ Statistiques
    if nom == "Tendance et prévision (régression)":
        txt = c[0].text_input("Valeurs passées, dans l'ordre (;)", "120; 135; 150; 148; 170; 182", key="tl_v")
        n = c[1].number_input("Périodes à prévoir", 1, 24, 3, key="tl_n")
        try:
            v = liste(txt)
            assert len(v) >= 3
        except (ValueError, AssertionError):
            st.error("Il faut au moins 3 valeurs, séparées par des points-virgules.")
            return None
        x = S.tendance_lineaire(v, n)
        fiab = "forte" if x["r2"] >= 0.8 else "moyenne" if x["r2"] >= 0.5 else "faible"
        return rapport(nom, categorie_de(nom), {"Valeurs": txt, "Périodes à prévoir": n},
                       {"Pente (hausse par période)": x["pente"], "Ordonnée à l'origine": x["ordonnee"],
                        "R² (qualité de l'ajustement)": f"{x['r2']} ({fiab})"},
                       ["Moindres carrés : y = a × t + b, t = 1, 2, 3…", "R² = 1 − Σ(y − ŷ)² ÷ Σ(y − ȳ)²."],
                       ["Statistique : régression linéaire simple"], tableau=x["tableau"],
                       conseils=[f"Fiabilité {fiab} : " + ("la tendance explique bien les données." if fiab == "forte"
                                 else "la tendance seule ne suffit pas ; cherchez une saisonnalité ou un événement."),
                                 "Ne prévoyez pas plus loin que le tiers de l'historique disponible."])
    if nom == "Taille d'échantillon (sondage)":
        marge = c[0].number_input("Marge d'erreur (%)", 0.5, 20.0, 5.0, 0.5, key="te_m") / 100
        conf = c[1].selectbox("Niveau de confiance", [0.95, 0.90, 0.99], format_func=pc, key="te_c")
        pop = c[2].number_input("Taille de la population (0 = très grande)", 0, 100_000_000, 0, key="te_p")
        x = S.taille_echantillon(marge, conf, 0.5, pop or None)
        return rapport(nom, categorie_de(nom), {"Marge d'erreur": pc(marge), "Confiance": pc(conf),
                                                "Population": pop or "très grande"},
                       {"Échantillon nécessaire": x["n"], "Sans correction de population": x["n_infini"], "z": x["z"]},
                       ["n = z² × p × (1 − p) ÷ e², avec p = 0,5 (cas le plus prudent).",
                        "Population finie : n ÷ (1 + (n − 1) ÷ N)."],
                       ["Statistique : estimation d'une proportion (loi normale)"],
                       conseils=["L'échantillon doit être tiré au hasard ou par quotas représentatifs : un grand "
                                 "échantillon biaisé reste faux.", "Prévoyez 20 à 30 % de non-réponses en plus."])
    # ------------------------------------------------------------------ Projets et business plans
    if nom in ("Business plan sur 5 ans", "Étude de sensibilité du projet"):
        st.caption("Renseignez le projet : je construis le compte de résultat, le plan de financement, la trésorerie, "
                   "la rentabilité et la capacité de remboursement, exercice par exercice.")
        e = st.columns(4)
        debut = e[0].date_input("Démarrage de l'activité", value=datetime.date(aujourdhui.year + 1, 1, 1), key="bp_d",
                                format="DD/MM/YYYY")
        ca = e[1].number_input("CA de la 1re année pleine HT (DH)", 0.0, value=1_200_000.0, step=50_000.0, key="bp_ca")
        cr = e[2].number_input("Croissance du CA (%/an)", -50.0, 200.0, 10.0, 1.0, key="bp_cr") / 100
        tcv = e[3].number_input("Coûts variables (% du CA)", 0.0, 99.0, 45.0, 1.0, key="bp_cv") / 100
        e2 = st.columns(4)
        cf = e2[0].number_input("Charges fixes annuelles (DH)", 0.0, value=450_000.0, step=10_000.0, key="bp_cf",
                                help="Salaires et charges sociales, loyer, assurances, honoraires…")
        hcf = e2[1].number_input("Hausse des charges fixes (%/an)", 0.0, 30.0, 3.0, 0.5, key="bp_hcf") / 100
        inv = e2[2].number_input("Investissements HT (DH)", 0.0, value=500_000.0, step=10_000.0, key="bp_inv")
        dur = e2[3].number_input("Durée d'amortissement (ans)", 1, 40, 5, key="bp_dur")
        e3 = st.columns(4)
        apport = e3[0].number_input("Apport des associés (DH)", 0.0, value=200_000.0, step=10_000.0, key="bp_ap")
        emprunt = e3[1].number_input("Emprunt bancaire (DH)", 0.0, value=400_000.0, step=10_000.0, key="bp_em")
        te = e3[2].number_input("Taux de l'emprunt (%)", 0.0, 20.0, 6.0, 0.1, key="bp_te") / 100
        de = e3[3].number_input("Durée de l'emprunt (ans)", 1, 25, 5, key="bp_de")
        e4 = st.columns(4)
        dc = e4[0].number_input("Délai clients (jours)", 0, 180, 60, key="bp_dc", help="Loi 69-21 : 60 jours au plus, sauf accord.")
        dfo = e4[1].number_input("Délai fournisseurs (jours)", 0, 180, 60, key="bp_df")
        sj = e4[2].number_input("Stock (jours d'achats)", 0, 365, 30, key="bp_sj")
        ta = e4[3].number_input("Taux d'actualisation (%)", 0.0, 40.0, 10.0, 0.5, key="bp_ta") / 100
        e5 = st.columns(2)
        sub = e5[0].number_input("Subventions et aides (DH)", 0.0, value=0.0, step=10_000.0, key="bp_sub",
                                 help="Programmes publics de l'année (à vérifier auprès de l'organisme).")
        fe = e5[1].number_input("Frais de démarrage (DH)", 0.0, value=20_000.0, step=1_000.0, key="bp_fe")
        params = dict(ca_annee1=ca, croissance_ca=cr, taux_couts_variables=tcv, charges_fixes=cf, hausse_charges_fixes=hcf,
                      investissement=inv, duree_amortissement=dur, apport=apport, emprunt=emprunt, taux_emprunt=te,
                      duree_emprunt_ans=de, delai_clients_jours=dc, delai_fournisseurs_jours=dfo, stock_jours=sj,
                      taux_actualisation=ta, annee_debut=debut.year, mois_debut=debut.month, subvention=sub,
                      frais_etablissement=fe)
        bp = P.business_plan(**params)
        entrees = {"Démarrage": debut.strftime("%d/%m/%Y"), "CA année pleine": dh(ca), "Croissance": pc(cr),
                   "Coûts variables": pc(tcv), "Charges fixes": dh(cf), "Investissements": dh(inv), "Apport": dh(apport),
                   "Emprunt": f"{dh(emprunt)} à {pc(te)} sur {de} ans", "Délais clients / fournisseurs / stock":
                   f"{dc} / {dfo} / {sj} jours", "Subventions": dh(sub), "Frais de démarrage": dh(fe)}
        conseils = []
        if bp["ecart_financement"] < 0:
            conseils.append(f"⚠️ Financement de départ insuffisant de {dh(-bp['ecart_financement'])} : augmentez l'apport, "
                            "l'emprunt ou cherchez une aide.")
        if bp["part_apport"] is not None and bp["part_apport"] < 0.30:
            conseils.append(f"Apport de {pc(bp['part_apport'])} des besoins : beaucoup de banques demandent au moins "
                            "30 % ; préparez un apport plus élevé ou des garanties (caution, nantissement).")
        if bp["premier_exercice_negatif"]:
            conseils.append(f"⚠️ Trésorerie négative en {bp['premier_exercice_negatif']} (au plus bas "
                            f"{dh(bp['tresorerie_min'])}) : prévoyez un fonds de roulement plus large, un différé de "
                            "remboursement ou des délais clients plus courts.")
        if bp["dscr_min"] is not None and bp["dscr_min"] < 1.2:
            conseils.append(f"⚠️ Capacité de remboursement faible (DSCR minimal {bp['dscr_min']:.2f}, la banque attend en "
                            "général au moins 1,2) : allongez la durée de l'emprunt ou réduisez-le.")
        if bp["seuil_rentabilite"] and bp["seuil_rentabilite"] > ca:
            conseils.append("⚠️ Le seuil de rentabilité dépasse le chiffre d'affaires prévu : le projet perd de l'argent "
                            "tant que les ventes ou la marge n'augmentent pas.")
        conseils.append(f"VAN {dh(bp['van'])} et TRI {pc(bp['tri']) if bp['tri'] is not None else '—'} : "
                        + ("le projet crée de la valeur au taux exigé." if bp["van"] > 0 else
                           "le projet ne rémunère pas le taux exigé ; revoyez prix, coûts ou investissements."))
        conseils.append(f"Réduire le délai clients de 15 jours libère environ {dh(ca * 1.2 * 15 / 360)} de trésorerie.")
        methode = ["Compte de résultat prévisionnel : CA − coûts variables − charges fixes = EBE ; − dotations − intérêts "
                   "= résultat avant impôt ; − IS = résultat net ; CAF = résultat net + dotations.",
                   "1er exercice au prorata des mois d'activité ; amortissements linéaires depuis le mois de démarrage "
                   "(CGI, art. 10) ; intérêts tirés de l'échéancier daté de l'emprunt.",
                   "IS de chaque exercice selon le barème 2026 (20 % jusqu'à 100 MDH de bénéfice) ; cotisation minimale "
                   "(0,25 % du CA, 3 000 DH au moins) dès le 37e mois (CGI, art. 19 et 144).",
                   "BFR = (créances clients TTC + stocks − dettes fournisseurs TTC), TVA 20 %, base 360 jours.",
                   "Trésorerie = ressources initiales − emplois initiaux + Σ (CAF − variation du BFR − capital remboursé).",
                   "DSCR = (CAF + intérêts) ÷ annuité d'emprunt ; VAN et TRI sur les flux d'exploitation après IS, "
                   "BFR et valeur nette comptable récupérés en dernière année."]
        refs = ["Loi n° 9-88 et CGNC (états prévisionnels : CPC, plan de financement)",
                "CGI, art. 10, 19 et 144 (amortissements, IS, cotisation minimale)",
                "Loi n° 69-21 (délais de paiement)", f"Taux vérifiés le {B.VERIFIE_LE}"]
        if nom == "Étude de sensibilité du projet":
            sen = P.sensibilite(params)
            fragiles = sen["tableau"][sen["tableau"]["Verdict"] != "✅ tient"]["Scénario"].tolist()
            conseils = ([f"Le projet reste rentable jusqu'à une baisse des ventes de {pc(sen['baisse_critique_des_ventes'])}."]
                        if sen["baisse_critique_des_ventes"] is not None else
                        ["Le projet n'est déjà pas rentable dans le scénario de référence."])
            conseils += ([f"Scénarios fragiles : {', '.join(fragiles)} — préparez un plan B (charges fixes réductibles, "
                          "financement de secours)."] if fragiles else ["Le projet tient dans tous les scénarios testés."])
            return rapport(nom, categorie_de(nom), entrees,
                           {"Baisse des ventes qui annule la VAN": pc(sen["baisse_critique_des_ventes"])
                            if sen["baisse_critique_des_ventes"] is not None else "déjà négative",
                            "Scénarios fragiles": len(fragiles), "Scénarios testés": len(sen["tableau"])},
                           methode + ["Chaque scénario refait le business plan complet ; la baisse critique est trouvée "
                                      "par dichotomie."], refs, debut.year, tableau=sen["tableau"], conseils=conseils)
        st.markdown("#### 📑 Compte de résultat prévisionnel")
        st.dataframe(bp["compte_de_resultat"], hide_index=True, width="stretch")
        return rapport(nom, categorie_de(nom), entrees,
                       {"Besoins de départ": dh(bp["besoins_initiaux"]), "Ressources de départ": dh(bp["ressources_initiales"]),
                        "Équilibre du financement": dh(bp["ecart_financement"]), "Mensualité de l'emprunt": dh(bp["mensualite"]),
                        "Seuil de rentabilité annuel": dh(bp["seuil_rentabilite"]) if bp["seuil_rentabilite"] else "—",
                        "Point mort": f"{bp['point_mort_jours']} jours d'activité" if bp["point_mort_jours"] else "—",
                        "Résultat net cumulé": dh(bp["resultat_cumule"]), "VAN": dh(bp["van"]),
                        "TRI": pc(bp["tri"]) if bp["tri"] is not None else "—",
                        "Délai de récupération": f"{bp['delai_recuperation']:.2f} ans".replace(".", ",") if bp["delai_recuperation"] else "au-delà du plan",
                        "DSCR minimal": f"{bp['dscr_min']:.2f}".replace(".", ",") if bp["dscr_min"] is not None else "sans emprunt",
                        "Trésorerie la plus basse": dh(bp["tresorerie_min"])},
                       methode, refs, debut.year, tableau=bp["plan_de_financement"],
                       remarques=["Le compte de résultat détaillé est affiché au-dessus ; le tableau ci-dessous est le "
                                  "plan de financement et de trésorerie.", "Non traités : TVA sur investissements "
                                  "(crédit de TVA de départ), saisonnalité mensuelle, distribution de dividendes."],
                       conseils=conseils)
    if nom == "Plan de financement initial":
        st.caption("Une ligne par poste : libellé, montant.")
        b = c[0].text_area("Besoins", "Matériel, 300000\nAménagement du local, 120000\nFrais de démarrage, 20000\n"
                                      "Stock de départ, 60000\nFonds de roulement, 80000", key="pf_b", height=160)
        r = c[1].text_area("Ressources", "Apport des associés, 200000\nEmprunt bancaire, 350000\nSubvention, 0",
                           key="pf_r", height=160)
        try:
            lire = lambda t: {l.rsplit(",", 1)[0].strip(): float(l.rsplit(",", 1)[1].replace(" ", ""))
                              for l in t.splitlines() if l.strip()}
            besoins, ressources = lire(b), lire(r)
        except (ValueError, IndexError):
            st.error("Écris une ligne par poste : libellé, montant (ex. Matériel, 300000)")
            return None
        x = P.plan_de_financement_initial(besoins, ressources)
        apport = sum(v for k, v in ressources.items() if "apport" in k.lower() or "capital" in k.lower())
        conseils = ([f"⚠️ Il manque {dh(-x['ecart'])} : complétez le financement avant de démarrer."] if x["ecart"] < 0 else
                    [f"Plan équilibré, marge de sécurité {dh(x['ecart'])}."])
        if x["total_besoins"] and apport / x["total_besoins"] < 0.2:
            conseils.append("Apport inférieur à 20 % des besoins : la plupart des banques le jugeront insuffisant.")
        if not any("roulement" in k.lower() for k in besoins):
            conseils.append("Ajoutez un fonds de roulement de départ : c'est la cause n° 1 des difficultés des jeunes "
                            "entreprises.")
        return rapport(nom, categorie_de(nom), {"Besoins": b.replace("\n", " ; "), "Ressources": r.replace("\n", " ; ")},
                       {"Total des besoins": dh(x["total_besoins"]), "Total des ressources": dh(x["total_ressources"]),
                        "Écart": dh(x["ecart"]), "Part de l'apport": pc(apport / x["total_besoins"]) if x["total_besoins"] else "—"},
                       ["Un plan de financement initial est équilibré quand les ressources stables couvrent tous les "
                        "besoins de départ, y compris le fonds de roulement."],
                       ["Loi n° 9-88 et CGNC (tableau de financement)"], tableau=x["tableau"], conseils=conseils)
    # ------------------------------------------------------------------ Impôts décortiqués
    if nom in D.FICHES:
        f = D.FICHES[nom]
        secteur = c[0].selectbox("Votre secteur d'activité", D.SECTEURS, key=f"dc_s_{nom}")
        exercice = c[1].number_input("Exercice", 2010, 2030, aujourdhui.year, key=f"dc_e_{nom}")
        for titre, lignes in f["sections"]:
            st.markdown(f"**{titre}**\n\n" + "\n".join(f"- {l}" for l in lignes))
        propre = f["secteurs"].get(secteur)
        if secteur != D.SECTEURS[0]:
            st.info(f"🏷️ **{secteur}** : " + (propre or "pas de règle particulière recensée pour ce secteur : le droit "
                                                     "commun s'applique (vérifiez les régimes particuliers du CGI)."))
        if f["secteurs"]:
            with st.expander("Toutes les règles par secteur"):
                st.markdown("\n".join(f"- **{k}** : {v}" for k, v in f["secteurs"].items()))
        tableau = f["tableau"]() if f["tableau"] else None
        if nom in ("IR décortiqué", "Déclaration du revenu global (personnes physiques)"):
            periode = B.periode("ir", exercice, memoire)
            st.markdown(f"**Barème de l'exercice {exercice}** : " + (periode["loi"] if periode else
                        "non vérifié — je ne l'invente pas ; l'administrateur peut l'ajouter avec sa source."))
        lecture = None
        try:
            from .lecture import repondre_par_lecture
            lecture = repondre_par_lecture(f["question"], memoire, n=3)
        except Exception:
            lecture = None
        if lecture:
            with st.expander("📖 Ce que j'ai lu dans vos documents (CGI…)"):
                st.markdown(lecture["reponse"])
        cols = st.columns(len(f["simulations"]))
        for col, sim in zip(cols, f["simulations"]):
            if col.button(f"🧮 {sim}", key=f"dc_go_{nom}_{sim}", width="stretch"):
                st.session_state["simulation"] = sim
                st.rerun()
        points = {titre: lignes[0][:160] + ("…" if len(lignes[0]) > 160 else "") for titre, lignes in f["sections"][:3]}
        return rapport(nom, categorie_de(nom), {"Secteur": secteur, "Exercice": exercice},
                       {**points, **({f"Règle du secteur « {secteur} »": propre} if propre else {})},
                       [f"{titre} : " + " ".join(lignes) for titre, lignes in f["sections"]], f["references"]
                       + [f"Vérifié le {B.VERIFIE_LE} (CGI et cabinets : Upsilon Consulting, Humantal)"], exercice,
                       tableau=tableau, remarques=["Listes sectorielles : cas les plus courants ; la liste complète "
                       "figure dans les articles cités, dans leur version de l'exercice."],
                       conseils=["Déposez chaque déclaration même sans montant à payer, et gardez l'accusé de réception "
                                 "et la quittance : c'est votre preuve de régularité.",
                                 "Demandez l'attestation de régularité fiscale sur SIMPL avant d'en avoir besoin "
                                 "(marché public, banque, aide) : un oubli se découvre alors à temps."])
    if nom == "Revenus fonciers (loyers)":
        loyers = c[0].number_input("Loyers bruts encaissés dans l'année (DH)", 0.0, value=96_000.0, step=1_000.0, key="rf_l")
        autres = c[1].number_input("Autres revenus nets imposables (salaires…) (DH)", 0.0, value=120_000.0,
                                   step=5_000.0, key="rf_a")
        annee = c[2].selectbox("Exercice", [2026, 2025], key="rf_e")
        locataire = st.radio("Locataire", ["Société ou professionnel (retenue à la source)", "Particulier"],
                             horizontal=True, key="rf_t").startswith("Société")
        x = D.revenus_fonciers(loyers, autres, annee, locataire, memoire)
        conseils = [f"La solution la moins chère est : **{x['meilleur']}**." if x["option_20"] is not None else
                    "Locataire particulier : pas de retenue, l'IR sur les loyers se paie avec la déclaration du revenu global.",
                    "Enregistrez le bail et encaissez les loyers par virement : c'est votre preuve en cas de contrôle."]
        if x["solde"] < 0:
            conseils.append(f"La retenue dépasse l'IR dû sur les loyers : {dh(-x['solde'])} vous sont restitués d'office "
                            "après la déclaration (CGI, art. 241 bis) — déposez-la à temps.")
        return rapport(nom, categorie_de(nom), {"Loyers bruts": dh(loyers), "Autres revenus nets": dh(autres),
                                                "Exercice": annee, "Locataire": "société" if locataire else "particulier"},
                       {"Revenu foncier net (après 40 %)": dh(x["net_foncier"]), "IR dû à cause des loyers": dh(x["ir_loyers"]),
                        "Retenue à la source": f"{dh(x['ras'])} ({pc(x['taux_ras'])})" if x["ras"] else
                        ("dispense (≤ 40 000 DH)" if locataire and x["dispense"] else "aucune"),
                        "Solde à payer (ou à restituer)": dh(x["solde"]),
                        "Option libératoire de 20 %": dh(x["option_20"]) if x["option_20"] is not None else "non applicable"},
                       ["Revenu foncier net = loyers bruts × 60 % (abattement de 40 %, art. 64-II).",
                        f"IR dû à cause des loyers = IR {annee} (autres revenus + revenu foncier net) − IR {annee} "
                        "(autres revenus seuls) : les loyers sont taxés à votre taux marginal.",
                        "Retenue du locataire professionnel : 10 % (< 120 000 DH) ou 15 % (≥ 120 000 DH), imputable "
                        "sur cet IR depuis la LF 2023.", "Option de la LF 2025 : 20 % du brut, libératoire."],
                       ["CGI, art. 61 à 64, 73-II, 82-I, 160 bis, 174-IV, 241 bis", B.periode("ir", annee)["loi"],
                        f"Vérifié le {B.VERIFIE_LE} (Upsilon Consulting — revenus fonciers 2026)"], annee,
                       remarques=["Non traités : profits immobiliers (vente), locations meublées professionnelles, "
                                  "taxe d'habitation et de services communaux, conventions fiscales des non-résidents."],
                       conseils=conseils)
    if nom == "État 9421 (préparation)":
        st.caption("Une ligne par salarié : nom, salaire brut annuel, cotisations CNSS et AMO annuelles, personnes à "
                   "charge, IR retenu dans l'année.")
        txt = st.text_area("Salariés", "Salarié A, 96000, 5370, 2, 4100\nSalarié B, 60000, 4045, 0, 1050", key="9421_t")
        annee = c[0].selectbox("Année des salaires", [y for y in B.annees_couvertes("ir", memoire)][::-1], key="9421_a")
        try:
            lignes = []
            for l in txt.splitlines():
                if l.strip():
                    nom_, *v = [x.strip() for x in l.split(",")]
                    lignes.append((nom_, float(v[0]), float(v[1]), int(float(v[2])), float(v[3])))
        except (ValueError, IndexError):
            st.error("Écris une ligne par salarié : nom, brut annuel, cotisations, personnes à charge, IR retenu")
            return None
        x = D.etat_9421(lignes, annee, memoire)
        st.download_button("⬇️ Télécharger le tableau (CSV)", x["tableau"].to_csv(index=False, sep=";").encode("utf-8-sig"),
                           f"etat_9421_{annee}.csv", "text/csv", key="9421_csv")
        conseils = ([f"⚠️ Écart entre l'IR retenu et l'IR recalculé pour : {', '.join(x['ecarts'])} — régularisez "
                     "(retenue complémentaire ou restitution) avant le dépôt."] if x["ecarts"] else
                    ["✅ IR retenu cohérent avec le barème pour tous les salariés."])
        conseils.append(f"Déposez l'état avant le 1er mars {annee + 1} sur SIMPL (CGI, art. 79).")
        return rapport(nom, categorie_de(nom), {"Année": annee, "Salariés": len(lignes)},
                       {"Total des salaires bruts": dh(x["total_brut"]), "Total de l'IR recalculé": dh(x["total_ir"]),
                        "Salariés avec écart": len(x["ecarts"])},
                       ["Net imposable annuel = brut − cotisations − frais professionnels (35 % jusqu'à 78 000 DH, "
                        "25 % au-delà, plafond 35 000 DH).", f"IR = barème {annee} − 500 DH par personne à charge (au "
                        "plus 6).", "Écart = IR retenu − IR recalculé (tolérance 1 DH)."],
                       ["CGI, art. 59, 73-I, 74, 79, 156 et 174", B.periode("ir", annee)["loi"]], annee,
                       tableau=x["tableau"], remarques=["Avantages en nature, indemnités imposables et régularisations "
                       "d'entrée ou de sortie en cours d'année : à ajouter au brut annuel.",
                       "Déduction pour charges de famille de 500 DH par personne : vérifiez le montant de l'exercice."],
                       conseils=conseils)
    return None
