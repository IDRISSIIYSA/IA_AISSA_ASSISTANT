"""
Coefficients de réévaluation du prix d'acquisition pour l'IR sur les profits fonciers (CGI, art. 65-II), fixés chaque
année par arrêté du ministre de l'Économie et des Finances.

Année 2026 (cessions réalisées en 2026) : arrêté du 6 février 2026 (n° 230-26 selon CAE Experts), publié au Bulletin
officiel n° 7486 du 26 février 2026 selon Le Matin (n° 7488 selon CAE Experts). Tableau complet recopié de CAE Experts
le 06/11/2026 ; les six valeurs que cite Le Matin (1980, 2000, 2010, 2022, 2024, 2025) concordent exactement. Le
Bulletin officiel (sgg.gov.ma) refuse les connexions automatiques : tableau à confirmer sur le BO au besoin.

Acquisitions de 1945 et avant : « taux forfaitaire de 3 % » par an, dont les modalités ne sont pas détaillées par ces
sources — non calculé (saisie manuelle).
"""

ANNEE_DU_TABLEAU = 2026
SOURCE = ("Arrêté du ministre de l'Économie et des Finances du 6 février 2026 (BO n° 7486 du 26/02/2026 selon Le Matin) ; "
          "tableau lu sur CAE Experts et Le Matin le 06/11/2026")
_VALEURS = """
1946 57,773 1947 44,991 1948 31,717 1949 25,479 1950 24,885 1951 22,105 1952 18,862 1953 18,262 1954 19,916
1955 18,862 1956 16,018 1957 16,880 1958 13,803 1959 13,803 1960 13,280 1961 12,671 1962 12,459 1963 11,463
1964 11,032 1965 10,660 1966 10,705 1967 10,898 1968 10,822 1969 10,453 1970 10,348 1971 9,870 1972 9,366
1973 9,247 1974 8,264 1975 7,160 1976 6,536 1977 6,016 1978 5,407 1979 5,020 1980 4,646 1981 4,143 1982 3,722
1983 3,576 1984 3,085 1985 2,921 1986 2,655 1987 2,609 1988 2,550 1989 2,460 1990 2,300 1991 2,101 1992 1,999
1993 1,896 1994 1,819 1995 1,732 1996 1,686 1997 1,673 1998 1,628 1999 1,614 2000 1,585 2001 1,569 2002 1,536
2003 1,523 2004 1,492 2005 1,478 2006 1,432 2007 1,402 2008 1,351 2009 1,309 2010 1,296 2011 1,285 2012 1,270
2013 1,248 2014 1,243 2015 1,223 2016 1,205 2017 1,196 2018 1,175 2019 1,173 2020 1,164 2021 1,150 2022 1,078
2023 1,017 2024 1,008 2025 1,000
"""
_mots = _VALEURS.split()
COEFFICIENTS_2026 = {int(a): float(c.replace(",", ".")) for a, c in zip(_mots[::2], _mots[1::2])}


def coefficient(annee_acquisition, annee_cession=ANNEE_DU_TABLEAU):
    """Le coefficient officiel, ou None (autre année de cession que celle du tableau, ou acquisition avant 1946)."""
    if annee_cession != ANNEE_DU_TABLEAU:
        return None
    if annee_acquisition >= ANNEE_DU_TABLEAU:
        return 1.0                                 # acquis l'année même de la cession : pas de réévaluation
    return COEFFICIENTS_2026.get(int(annee_acquisition))
