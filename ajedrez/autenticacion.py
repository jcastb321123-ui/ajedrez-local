from __future__ import annotations

from typing import Generic, TypeVar


TipoJugador = TypeVar("TipoJugador")


class AutenticadorJugadores(Generic[TipoJugador]):
    """Relaciona claves con identidades de jugadores durante esta ejecución.

    La modalidad de juego genera y recibe las claves. Esta clase únicamente
    registra sus asociaciones e identifica al jugador; no comprueba turnos
    ni conoce la consola, la GUI, la red o las reglas del juego.
    """

    def __init__(self) -> None:
        self._jugadores_por_clave: dict[str, TipoJugador] = {}

    @property
    def jugadores_por_clave(self) -> dict[str, TipoJugador]:
        return self._jugadores_por_clave

    def registrar(self, clave: str, jugador: TipoJugador) -> bool:
        """Asocia una clave nueva al jugador, sin sustituir asociaciones.

        Devuelve False si la clave no es una cadena no vacía, ya está
        registrada o el jugador es None. None se reserva para indicar
        que la autenticación no ha identificado a ningún jugador.
        """
        if not isinstance(clave, str) or not clave or jugador is None:
            return False

        if clave in self.jugadores_por_clave:
            return False

        self.jugadores_por_clave[clave] = jugador
        return True

    def autenticar(self, clave: str) -> TipoJugador | None:
        """Devuelve la identidad asociada, o None sin lanzar un error.

        La comparación es exacta: no elimina espacios ni modifica
        mayúsculas y minúsculas.
        """
        if not isinstance(clave, str):
            return None

        return self.jugadores_por_clave.get(clave)
