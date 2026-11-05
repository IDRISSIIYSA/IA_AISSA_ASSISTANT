"""
Les réseaux de neurones d'IA AISSA, isolés ici pour que PyTorch ne soit importé qu'au premier usage d'un cerveau
(démarrage à froid du serveur plus rapide : la page s'affiche avant que PyTorch soit chargé).

`torch` et `nn` exposés par ce module sont « paresseux » : le vrai module n'est importé qu'au premier attribut lu.
Les classes qui héritent de nn.Module, elles, sont définies à la demande (fonctions ci-dessous, avec cache).
"""

import importlib


class Paresseux:
    """Se comporte comme le module nommé, importé seulement au premier attribut demandé."""

    def __init__(self, nom):
        self._nom, self._module = nom, None

    def __getattr__(self, attribut):
        if self._module is None:
            self._module = importlib.import_module(self._nom)
        return getattr(self._module, attribut)

    def charge(self):
        return self._module is not None


torch = Paresseux("torch")
nn = Paresseux("torch.nn")
_CLASSES = {}


def classe_cerveau_ecole():
    """Le cerveau d'une matière de l'école : deux couches cachées de 128 neurones."""
    if "ecole" not in _CLASSES:
        import torch.nn as vrai_nn

        class Cerveau(vrai_nn.Module):
            def __init__(self, dim, n_actions, cache=128):
                super().__init__()
                self.reseau = vrai_nn.Sequential(vrai_nn.Linear(dim, cache), vrai_nn.ReLU(),
                                                 vrai_nn.Linear(cache, cache), vrai_nn.ReLU(),
                                                 vrai_nn.Linear(cache, n_actions))

            def forward(self, x):
                return self.reseau(x)

        _CLASSES["ecole"] = Cerveau
    return _CLASSES["ecole"]


def classe_cerveau_controle(n_features, n_actions_defaut):
    """Le cerveau de l'agent de contrôle de gestion : deux couches cachées de 64 neurones."""
    if "controle" not in _CLASSES:
        import torch.nn as vrai_nn

        class Cerveau(vrai_nn.Module):
            def __init__(self, n_entrees=n_features, n_actions=n_actions_defaut):
                super().__init__()
                self.reseau = vrai_nn.Sequential(
                    vrai_nn.Linear(n_entrees, 64), vrai_nn.ReLU(),
                    vrai_nn.Linear(64, 64), vrai_nn.ReLU(),
                    vrai_nn.Linear(64, n_actions),
                )

            def forward(self, x):
                return self.reseau(x)

        _CLASSES["controle"] = Cerveau
    return _CLASSES["controle"]
