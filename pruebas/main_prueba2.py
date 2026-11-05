"""Segunda etapa de la consola: SesionLocal, claves automáticas y promoción.

Se conserva main_prueba1.py como versión histórica. Este adaptador sólo recoge
texto y presenta resultados: los emisores y el modelo siguen validando el juego.
"""

from __future__ import annotations

from collections.abc import Callable

# Permite ejecutar este archivo directamente o como módulo desde el proyecto.
if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ajedrez.interfaz_juego import PiezaPromocion
from ajedrez.partida import EstadoPartida
from ajedrez.piezas import Color
from ajedrez.sesion import AsignacionColores, ModalidadAsignacion, SesionLocal


def convertir_posicion(texto: str) -> tuple[int, int] | None:
    """Admite e2, 1,4 o (1, 4); rechaza silenciosamente el resto."""
    texto = texto.strip().lower()
    if len(texto) == 2 and texto[0] in "abcdefgh" and texto[1] in "12345678":
        return int(texto[1]) - 1, ord(texto[0]) - ord("a")

    if texto.startswith("(") and texto.endswith(")"):
        texto = texto[1:-1]
    partes = [parte.strip() for parte in texto.split(",")]
    if len(partes) != 2 or any(
        len(parte) != 1 or parte not in "01234567" for parte in partes
    ):
        return None
    return int(partes[0]), int(partes[1])


def _nombre_casilla(posicion: tuple[int, int]) -> str:
    fila, columna = posicion
    return f"{chr(ord('a') + columna)}{fila + 1}"


def _leer_texto(mensaje: str, leer: Callable[[str], str]) -> str | None:
    """La salida y la interrupción cierran la consola, no adjudican la partida."""
    try:
        texto = leer(mensaje).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return None
    return None if texto == "salir" else texto


def ejecutar_sesion(
    sesion: SesionLocal,
    leer: Callable[[str], str] = input,
    escribir: Callable[[str], None] = print,
) -> None:
    """Bucle de consola; leer/escribir son sustituibles para probar la interacción.

    En un teclado compartido se habilita el emisor del turno. No se identifica
    a la persona física que escribe ni se elige identidad según la pieza movida.
    Una GUI sustituirá este bucle por eventos, conservando las llamadas al modelo.
    """
    partida = sesion.partida
    nombres = {Color.Blanco: "blancas", Color.Negro: "negras"}
    jugadores = {}
    for numero, emisor in enumerate((sesion.emisor_1, sesion.emisor_2), start=1):
        color = sesion.autenticador.autenticar(emisor.clave)
        jugadores[color] = numero
        escribir(f"Jugador {numero}: {nombres[color]}.")

    escribir("Casillas: e2 o (1, 4). Coordenadas: fila y columna de 0 a 7; a1 = (0, 0).")
    escribir("Escribe salir en cualquier pregunta para cerrar sin guardar.")

    opciones_promocion = {
        "d": PiezaPromocion.REINA,
        "t": PiezaPromocion.TORRE,
        "a": PiezaPromocion.ALFIL,
        "c": PiezaPromocion.CABALLO,
    }
    resultados = {
        EstadoPartida.VICTORIA_BLANCA: "Victoria de las blancas.",
        EstadoPartida.VICTORIA_NEGRA: "Victoria de las negras.",
        EstadoPartida.TABLAS: "Tablas.",
    }

    while partida.estado_partida == EstadoPartida.EN_CURSO:
        numero = jugadores[partida.jugador]
        escribir(f"Turno: jugador {numero} ({nombres[partida.jugador]}).")

        # Mientras exista pendiente, no se recoge ninguna solicitud de movimiento.
        pendiente = sesion.jugada_pendiente
        if pendiente is not None:
            texto = _leer_texto(
                f"Promoción en {_nombre_casilla(pendiente.destino)}: "
                "dama [d], torre [t], alfil [a], caballo [c]: ",
                leer,
            )
            if texto is None:
                return
            tipo = opciones_promocion.get(texto)
            if tipo is None:
                continue
            sesion.elegir_promocion(tipo)
            escribir("Promoción completada.")
            continue

        texto = _leer_texto("Origen: ", leer)
        if texto is None:
            return
        origen = convertir_posicion(texto)
        if origen is None:
            continue

        texto = _leer_texto("Destino: ", leer)
        if texto is None:
            return
        destino = convertir_posicion(texto)
        if destino is None:
            continue

        contador_anterior = partida.contador_jugadas
        sesion.solicitar_movimiento(origen, destino)
        # Los rechazos devuelven un motivo; el contador confirma la aceptación.
        if sesion.jugada_pendiente is not None:
            escribir("Desplazamiento válido; falta elegir la pieza de promoción.")
        elif partida.contador_jugadas > contador_anterior:
            escribir(f"Movimiento aceptado: {_nombre_casilla(origen)} -> {_nombre_casilla(destino)}.")

    escribir(resultados[partida.estado_partida])


def main(
    leer: Callable[[str], str] = input,
    escribir: Callable[[str], None] = print,
) -> None:
    """Prepara una partida local nueva y cede el control al adaptador de consola."""
    escribir("Ajedrez local - consola 2 (sin tablero).")
    escribir("Reparto: [1] aleatorio; [2] jugador 1 blancas; [3] jugador 1 negras.")
    modalidades = {
        "": ModalidadAsignacion.ALEATORIA,
        "1": ModalidadAsignacion.ALEATORIA,
        "2": ModalidadAsignacion.BLANCO_NEGRO,
        "3": ModalidadAsignacion.NEGRO_BLANCO,
    }
    while True:
        texto = _leer_texto("Reparto [1 por defecto; salir para cerrar]: ", leer)
        if texto is None:
            return
        modalidad = modalidades.get(texto)
        if modalidad is not None:
            break

    sesion = SesionLocal(AsignacionColores(modalidad))
    ejecutar_sesion(sesion, leer, escribir)


if __name__ == "__main__":
    main()
