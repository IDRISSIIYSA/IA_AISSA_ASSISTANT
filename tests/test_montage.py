import io
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from montage import analyser, en_nombres, mois_depuis_entete, monter  # noqa: E402

EXEMPLES = Path(__file__).resolve().parents[1] / "exemples"


def monter_fichier(contenu, nom):
    analyses = analyser(contenu, nom)
    return monter(analyses)


def excel(feuilles):
    tampon = io.BytesIO()
    with pd.ExcelWriter(tampon, engine="openpyxl") as w:
        for nom, (df, debut) in feuilles.items():
            df.to_excel(w, sheet_name=nom, index=False, startrow=debut)
            if debut:
                w.sheets[nom].cell(row=1, column=1, value="Tableau de bord — Société X")
    return tampon.getvalue()


def test_nombres_formats_francais():
    s = pd.Series(["1 234,56 €", "(500)", "1.234.567", "12,5", "Production", "01/02/2024", None])
    assert en_nombres(s).tolist()[:4] == [1234.56, -500.0, 1234567.0, 12.5]
    assert en_nombres(s)[4:].isna().all()


@pytest.mark.parametrize("entete,attendu", [
    ("Janv 2024", "2024-01"), ("févr.-24", "2024-02"), ("2024-03", "2024-03"), ("04/2024", "2024-04"),
    ("M05", "M05"), ("Juin", "M06"), ("Production", None), (pd.Timestamp("2024-07-01"), "2024-07"),
])
def test_mois_depuis_entete(entete, attendu):
    assert mois_depuis_entete(entete)[0] == attendu


def test_format_colonnes_avec_alias_et_accents():
    csv = "Mois;Service;Budget prévu;Réalisé;CA\n2024-01;Achats;1000;1200;1500\n2024-02;Achats;1000;980;1400\n"
    out, _ = monter_fichier(csv.encode("utf-8"), "a.csv")
    assert out[["budget", "reel", "revenus"]].values.tolist() == [[1000, 1200, 1500], [1000, 980, 1400]]


def test_journal_comptable_debit_credit_sans_budget():
    csv = (
        "Date;Compte;Libellé;Section;Débit;Crédit\n"
        "05/01/2024;601000;Achat matières;Production;1 000,00;\n"
        "12/01/2024;706000;Facture client;Commercial;;2 500,00\n"
        "20/01/2024;623000;Publicité;Commercial;300,00;\n"
        "15/01/2024;512000;Banque;;2 500,00;\n"
        "03/02/2024;601000;Achat matières;Production;1 300,00;\n"
        "10/02/2024;641000;Salaires;Production;500,00;\n"
    )
    out, rapport = monter_fichier(csv.encode("cp1252"), "journal.csv")
    prod = out[out.centre == "Production"].set_index("periode")
    assert prod.loc["2024-01", "reel"] == 1000 and prod.loc["2024-02", "reel"] == 1800
    assert prod.loc["2024-02", "budget"] == 1000           # reconstruit : moyenne des mois précédents
    assert out[out.centre == "Commercial"]["revenus"].iloc[0] == 2500
    assert "512" not in out.to_string()                      # compte de banque exclu
    assert any("reconstruit" in r for r in rapport)


def test_excel_large_feuilles_budget_et_reel_avec_titre_et_total():
    mois = ["Janv", "Févr", "Mars"]
    budget = pd.DataFrame({"Centre": ["Production", "R&D", "Total"], **{m: [100, 50, 150] for m in mois}})
    reel = pd.DataFrame({"Centre": ["Production", "R&D", "Total"],
                         **{m: [110 + i, 40, 150] for i, m in enumerate(mois)}})
    out, _ = monter_fichier(excel({"Budget 2024": (budget, 2), "Réalisé 2024": (reel, 2)}), "b.xlsx")
    assert set(out.centre) == {"Production", "R&D"}            # ligne Total exclue
    assert out.periode.unique().tolist() == ["2024-01", "2024-02", "2024-03"]  # année du nom de feuille
    p = out[out.centre == "Production"]
    assert p.budget.tolist() == [100, 100, 100] and p.reel.tolist() == [110, 111, 112]


def test_large_une_feuille_type_en_ligne_et_ca():
    df = pd.DataFrame({
        "Poste": ["Production", "Production", "Chiffre d'affaires"],
        "Type": ["Budget", "Réel", "Réel"],
        "2024-01": [100, 120, 300], "2024-02": [100, 90, 280],
    })
    out, _ = monter_fichier(excel({"Suivi": (df, 0)}), "c.xlsx")
    prod = out[out.centre == "Production"]
    assert prod.budget.tolist() == [100, 100] and prod.reel.tolist() == [120, 90]


def test_exemples_fournis_se_montent():
    for fichier in sorted(EXEMPLES.glob("*")):
        out, _ = monter_fichier(fichier.read_bytes(), fichier.name)
        assert len(out) > 0 and out["reel"].notna().all() and out["budget"].notna().all(), fichier.name
