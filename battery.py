from dataclasses import dataclass


@dataclass
class EtatBatterie:
    tension: float
    etat: str
    niveau: str
    tendance: str


class GestionBatterie:
    """
    Interprétation simple de la tension d'une batterie
    lithium 12 V.

    ATTENTION :
    La tension seule ne permet pas de connaître précisément
    le pourcentage réel de charge.
    """

    def __init__(self):
        self.ancienne_tension = None

    def analyser(self, tension):
        """
        Analyse la tension et détermine :

        - l'état de la batterie
        - le niveau
        - la tendance
        """

        if tension < 12.60:
            etat = "Batterie très faible"
            niveau = "tres_faible"

        elif tension < 13.00:
            etat = "Batterie faible"
            niveau = "faible"

        elif tension < 13.60:
            etat = "Batterie disponible"
            niveau = "disponible"

        elif tension < 14.00:
            etat = "Batterie en charge"
            niveau = "charge"

        elif tension < 14.50:
            etat = "Batterie presque chargée"
            niveau = "presque_chargee"

        else:
            etat = "Batterie chargée"
            niveau = "chargee"

        # ----------------------------------------------------
        # TENDANCE
        # ----------------------------------------------------

        if self.ancienne_tension is None:
            tendance = "stable"

        elif tension > self.ancienne_tension + 0.02:
            tendance = "hausse"

        elif tension < self.ancienne_tension - 0.02:
            tendance = "baisse"

        else:
            tendance = "stable"

        self.ancienne_tension = tension

        return EtatBatterie(
            tension=round(tension, 2),
            etat=etat,
            niveau=niveau,
            tendance=tendance
        )
