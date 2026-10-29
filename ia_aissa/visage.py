"""Les salutations d'IA AISSA selon le moment de la journée (heure du Maroc), dans chaque langue."""

SALUTATIONS = {
    "Français": {"matin": "Bonjour {nom}, bonne journée !", "apres_midi": "Bon après-midi {nom} !",
                 "soir": "Bonsoir {nom} !", "nuit": "Bonsoir {nom}, il est tard : pensez à vous reposer."},
    "Arabe": {"matin": "صباح الخير يا {nom}", "apres_midi": "مساء الخير يا {nom}",
              "soir": "مساء الخير يا {nom}", "nuit": "مساء الخير يا {nom}، الوقت متأخر، خذ قسطا من الراحة"},
    "Darija": {"matin": "صباح الخير آ {nom}، لاباس عليك؟", "apres_midi": "مسا الخير آ {nom}، كيداير؟",
               "soir": "مسا الخير آ {nom}، كيف داز نهارك؟", "nuit": "مسا الخير آ {nom}، الليل طاح، خصك ترتاح شوية"},
    "English": {"matin": "Good morning {nom}!", "apres_midi": "Good afternoon {nom}!",
                "soir": "Good evening {nom}!", "nuit": "Good evening {nom}, it's late: get some rest."},
    "Español": {"matin": "¡Buenos días {nom}!", "apres_midi": "¡Buenas tardes {nom}!",
                "soir": "¡Buenas noches {nom}!", "nuit": "Buenas noches {nom}, ya es tarde: descansa un poco."},
}
