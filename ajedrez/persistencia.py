"""Formato JSON versionado de una partida local, independiente de Tkinter.

Se guarda una raíz y los movimientos confirmados. La reconstrucción pasa por
el modelo, que vuelve a enlazar estados y jugadas y a calcular los contadores.
Las claves de autenticación, los dibujos y las variantes no pertenecen al archivo.
"""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .editor_posicion import EditorPosicion
from .partida import EstadoPartida, EstadoPosicion, Jugada, Partida
from .piezas import (
    Alfil, Caballo, Color, PeonBlanco, PeonNegro, PiezaConPrimerMovimiento,
    Reina, Rey, Torre,
)
from .tablero import Tablero


VERSION_FORMATO = 1
_CLASES_PIEZAS = {
    "rey": Rey, "reina": Reina, "torre": Torre, "alfil": Alfil, "caballo": Caballo,
}
_NOMBRES_PIEZAS = {clase: nombre for nombre, clase in _CLASES_PIEZAS.items()}
_NOMBRES_PIEZAS.update({PeonBlanco: "peon", PeonNegro: "peon"})
_PROMOCIONES = {nombre: clase for nombre, clase in _CLASES_PIEZAS.items() if nombre != "rey"}


class ErrorArchivoPartida(ValueError):
    """El documento no representa una partida compatible y coherente."""


def partida_a_datos(partida: Partida) -> dict:
    """Produce sólo valores JSON y no altera la partida recibida."""
    if partida.promocion_pendiente:
        raise ErrorArchivoPartida("Elige la pieza de promoción antes de guardar la partida.")

    inicial = partida.estado_inicial
    piezas = [
        {
            "casilla": list(casilla),
            "tipo": _NOMBRES_PIEZAS[type(pieza)],
            "color": pieza.color.name,
            "ha_movido": pieza.ha_movido if isinstance(pieza, PiezaConPrimerMovimiento) else None,
        }
        for casilla, pieza in sorted(inicial.tablero.casillas.items())
        if pieza is not None
    ]
    movimientos = []
    estados = iter(partida.iterar_estados())
    next(estados)  # La raíz se representa por separado.
    for estado in estados:
        pieza_destino = estado.tablero.pieza_en(estado.destino)
        es_promocion = (
            isinstance(estado.pieza, (PeonBlanco, PeonNegro))
            and not isinstance(pieza_destino, (PeonBlanco, PeonNegro))
        )
        movimientos.append({
            "origen": list(estado.origen),
            "destino": list(estado.destino),
            "promocion": _NOMBRES_PIEZAS[type(pieza_destino)] if es_promocion else None,
        })

    peon_al_paso = inicial.tablero.posicion_de_captura_al_paso
    return {
        "formato": "ajedrez-local",
        "version": VERSION_FORMATO,
        "posicion_inicial": {
            "piezas": piezas,
            "turno": partida.primer_jugador.name,
            "peon_capturable_al_paso": list(peon_al_paso) if peon_al_paso is not None else None,
            "jugadas_sin_captura_ni_peon": inicial.jugadas_sin_captura_ni_peon,
        },
        "jugadas": movimientos,
        "resultado": partida.estado_partida.name,
    }


def partida_desde_datos(datos: dict) -> Partida:
    """Valida datos externos antes de devolver una partida independiente."""
    _comprobar_campos(datos, {"formato", "version", "posicion_inicial", "jugadas", "resultado"})
    if datos["formato"] != "ajedrez-local":
        raise ErrorArchivoPartida("El archivo no es una partida de Ajedrez local.")
    if type(datos["version"]) is not int or datos["version"] != VERSION_FORMATO:
        raise ErrorArchivoPartida("La versión del formato de guardado no es compatible.")
    inicial, turno = _leer_posicion_inicial(datos["posicion_inicial"])
    if not isinstance(datos["jugadas"], list):
        raise ErrorArchivoPartida("El historial debe ser una lista de jugadas.")
    resultado = _leer_enum(EstadoPartida, datos["resultado"], "resultado")
    partida = Partida(estado_inicial=inicial, turno_inicial=turno)
    for numero, movimiento in enumerate(datos["jugadas"], start=1):
        _comprobar_campos(movimiento, {"origen", "destino", "promocion"})
        origen = _leer_casilla(movimiento["origen"])
        destino = _leer_casilla(movimiento["destino"])
        promocion = movimiento["promocion"]
        if promocion is not None and (
            not isinstance(promocion, str) or promocion not in _PROMOCIONES
        ):
            raise ErrorArchivoPartida(f"La promoción de la jugada {numero} no es válida.")
        if partida.estado_partida is not EstadoPartida.EN_CURSO:
            raise ErrorArchivoPartida(f"La jugada {numero} aparece después de finalizar la partida.")
        respuesta = partida.procesar_solicitud(origen, destino)
        if isinstance(respuesta, Jugada):
            if promocion is None:
                raise ErrorArchivoPartida(f"Falta elegir la promoción de la jugada {numero}.")
            pieza = _PROMOCIONES[promocion](respuesta.pieza.color)
            partida.promocionar(destino, pieza, respuesta)
        elif respuesta is not None or promocion is not None:
            raise ErrorArchivoPartida(f"La jugada {numero} no es válida en esta posición.")

    # Mate, ahogado y tablas automáticas deben coincidir con la reconstrucción.
    # Abandono, acuerdo y reclamación pueden finalizar una posición jugable.
    if partida.estado_partida is not EstadoPartida.EN_CURSO and resultado is not partida.estado_partida:
        raise ErrorArchivoPartida("El resultado guardado contradice la posición final.")
    partida.estado_partida = resultado
    return partida


def guardar_partida(partida: Partida, ruta: str | Path) -> None:
    """Sustituye el archivo sólo después de escribirlo completamente."""
    contenido = json.dumps(partida_a_datos(partida), ensure_ascii=False, indent=2) + "\n"
    destino = Path(ruta)
    temporal = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                dir=destino.parent, prefix=".ajedrez-", suffix=".tmp",
                                delete=False) as archivo:
            temporal = Path(archivo.name)
            archivo.write(contenido)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, destino)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


def cargar_partida(ruta: str | Path) -> Partida:
    """Lee JSON; nunca ejecuta código ni deserializa objetos Python."""
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ErrorArchivoPartida("El archivo no contiene un documento JSON válido.") from error
    return partida_desde_datos(datos)


def _comprobar_campos(datos, campos: set[str]) -> None:
    if not isinstance(datos, dict) or set(datos) != campos:
        raise ErrorArchivoPartida("La estructura del archivo de partida no es válida.")


def _leer_casilla(valor) -> tuple[int, int]:
    if (not isinstance(valor, list) or len(valor) != 2
            or any(type(coordenada) is not int or not 0 <= coordenada < 8 for coordenada in valor)):
        raise ErrorArchivoPartida("Las casillas deben contener fila y columna entre 0 y 7.")
    return tuple(valor)


def _leer_enum(clase, valor, nombre):
    if not isinstance(valor, str) or valor not in clase.__members__:
        raise ErrorArchivoPartida(f"El valor de {nombre} no es válido.")
    return clase[valor]


def _leer_posicion_inicial(datos) -> tuple[EstadoPosicion, Color]:
    _comprobar_campos(datos, {"piezas", "turno", "peon_capturable_al_paso", "jugadas_sin_captura_ni_peon"})
    turno = _leer_enum(Color, datos["turno"], "turno")
    contador = datos["jugadas_sin_captura_ni_peon"]
    if type(contador) is not int or contador < 0:
        raise ErrorArchivoPartida("El contador de medios movimientos debe ser un entero no negativo.")
    if not isinstance(datos["piezas"], list):
        raise ErrorArchivoPartida("La distribución debe contener una lista de piezas.")
    tablero = Tablero()
    for casilla in tablero.casillas:
        tablero.colocar(None, casilla)
    for guardada in datos["piezas"]:
        _comprobar_campos(guardada, {"casilla", "tipo", "color", "ha_movido"})
        casilla = _leer_casilla(guardada["casilla"])
        if tablero.pieza_en(casilla) is not None:
            raise ErrorArchivoPartida("Hay más de una pieza en la misma casilla.")
        color = _leer_enum(Color, guardada["color"], "color")
        nombre = guardada["tipo"]
        if nombre == "peon":
            pieza = PeonBlanco() if color is Color.Blanco else PeonNegro()
        elif isinstance(nombre, str) and nombre in _CLASES_PIEZAS:
            pieza = _CLASES_PIEZAS[nombre](color)
        else:
            raise ErrorArchivoPartida("El tipo de pieza no es válido.")
        ha_movido = guardada["ha_movido"]
        if isinstance(pieza, PiezaConPrimerMovimiento):
            if type(ha_movido) is not bool:
                raise ErrorArchivoPartida("Falta el indicador de primer movimiento de una pieza.")
            if ha_movido:
                pieza.movimiento_realizado()
        elif ha_movido is not None:
            raise ErrorArchivoPartida("Esta pieza no utiliza el indicador de primer movimiento.")
        tablero.colocar(pieza, casilla)
    peon = datos["peon_capturable_al_paso"]
    tablero.posicion_de_captura_al_paso = None if peon is None else _leer_casilla(peon)
    estado = EstadoPosicion(tablero=tablero, jugadas_sin_captura_ni_peon=contador)
    try:
        # Reutiliza la comprobación de posiciones del editor sin adoptar su
        # normalización: el archivo conserva los ha_movido originales.
        EditorPosicion(estado, turno).construir_estado(
            turno=turno, enroques=set(tablero.obtener_derechos_enroque()),
            peon_al_paso=tablero.posicion_de_captura_al_paso,
        )
    except ValueError as error:
        raise ErrorArchivoPartida(str(error)) from error
    return estado, turno
