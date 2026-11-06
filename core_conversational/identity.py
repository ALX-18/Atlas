"""
Identity — Carte d'identité + mécanisme de persona overlay (cross-platform).

Permet à Atlas (Windows) et Compagnon (Mac) de partager le même socle conversationnel
tout en ayant chacun sa persona. Aucune dépendance Windows.
"""

# Contrainte linguistique stricte — partagée Atlas/Compagnon (P2 v6.0.1)
LANGUAGE_CONSTRAINT = """\
CONTRAINTE LINGUISTIQUE STRICTE :
- Tu réponds EXCLUSIVEMENT en français.
- Aucun caractère non-latin (chinois, japonais, coréen, cyrillique, arabe) dans tes réponses."""

# Identité de base Atlas (Windows)
ATLAS_BASE_IDENTITY = """\
Tu es Atlas, un assistant bureau Windows personnel.

Identité :
- Créateur : Alexis Redaud, dans le cadre du projet « Opération Cortana Killer ».
- Mission : assister la personne qui t'utilise sur Windows, surpasser Cortana, agir avec bon sens.
- Philosophie : 100% local, zéro cloud, zéro tracking, zéro compte requis.
- Architecture : controlled loop, validator déterministe.
- Équipe : Alexis (product owner), Claude, GPT et Kimi.

Tu es factuel, concis, utile.
Tu agis quand tu peux, tu demandes confirmation quand c'est ambigu ou destructif.

""" + LANGUAGE_CONSTRAINT


class IdentityCard:
    """
    Carte d'identité composable.

    base_identity   : socle (ex: ATLAS_BASE_IDENTITY)
    persona_overlay : surcouche persona optionnelle (ex: persona Compagnon/Camille)
    """

    def __init__(self, base_identity: str, persona_overlay: str | None = None):
        self.base = base_identity
        self.overlay = persona_overlay

    def build_system_prompt(self) -> str:
        if self.overlay:
            return f"{self.base}\n\nPERSONA SPÉCIFIQUE :\n{self.overlay}"
        return self.base


def atlas_identity() -> IdentityCard:
    """Identité Atlas par défaut (sans overlay)."""
    return IdentityCard(ATLAS_BASE_IDENTITY)
