"""Preferencias visuales inmutables, independientes de los recursos del tema.

Los campos se pasan por nombre y tienen valores predeterminados. Para variar una
configuración se utiliza dataclasses.replace. Sin slots: la definición de esta
clase puede ampliarse con nuevos campos y métodos.
"""

from dataclasses import dataclass
from enum import Enum


IDENTIFICADOR_TEMA_PREDETERMINADO = "club.liso_mate"


class ModoResaltadoJaque(Enum):
    REY_PERMANENTE = "rey_permanente"
    INTERMITENTE_TRAS_RECHAZO = "intermitente_tras_rechazo"
    REY_Y_ATACANTES = "rey_y_atacantes"


@dataclass(frozen = True, kw_only = True)
class OpcionesVisuales:
    modo_resaltado_jaque: ModoResaltadoJaque = ModoResaltadoJaque.REY_PERMANENTE
    intervalo_parpadeo_jaque_ms: int = 300
    repeticiones_parpadeo_jaque: int = 3

    def __post_init__(self) -> None:
        if not isinstance(self.modo_resaltado_jaque, ModoResaltadoJaque):
            raise TypeError("modo_resaltado_jaque debe ser un ModoResaltadoJaque")
        for nombre in ("intervalo_parpadeo_jaque_ms", "repeticiones_parpadeo_jaque"):
            valor = getattr(self, nombre)
            if type(valor) is not int or valor <= 0:
                raise ValueError(f"{nombre} debe ser un entero positivo")


OPCIONES_VISUALES_PREDETERMINADAS = OpcionesVisuales()
