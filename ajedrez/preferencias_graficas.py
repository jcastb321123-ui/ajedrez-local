"""Configuración gráfica del usuario, separada de las partidas y de los widgets.

El archivo conserva identificadores y valores, nunca imágenes ni objetos de Tk.
Leer no crea ni repara archivos; el guardado sólo se solicita al confirmar.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .gráficos.opciones_visuales import (
    IDENTIFICADOR_TEMA_PREDETERMINADO, ModoResaltadoJaque,
    OpcionesVisuales, OPCIONES_VISUALES_PREDETERMINADAS,
)


VERSION_FORMATO_PREFERENCIAS = 1


class ErrorPreferencias(ValueError):
    """El archivo no contiene una configuración gráfica compatible."""


@dataclass(frozen=True, kw_only=True)
class PreferenciasGraficas:
    identificador_tema: str = IDENTIFICADOR_TEMA_PREDETERMINADO
    opciones_visuales: OpcionesVisuales = OPCIONES_VISUALES_PREDETERMINADAS

    def __post_init__(self) -> None:
        if not isinstance(self.identificador_tema, str) or not self.identificador_tema.strip():
            raise ErrorPreferencias('El identificador del tema debe ser una cadena no vacía.')
        if not isinstance(self.opciones_visuales, OpcionesVisuales):
            raise ErrorPreferencias('Las opciones visuales no son válidas.')


def obtener_ruta_preferencias_predeterminada() -> Path:
    """No crea carpetas; la ruta pertenece al usuario, no al paquete instalado."""
    carpeta = Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.config')
    return carpeta / 'ajedrez-local' / 'preferencias.json'


def preferencias_a_datos(preferencias: PreferenciasGraficas) -> dict:
    opciones = preferencias.opciones_visuales
    return {
        'formato': 'ajedrez-local-preferencias',
        'version': VERSION_FORMATO_PREFERENCIAS,
        'tema': preferencias.identificador_tema,
        'opciones_visuales': {
            'modo_resaltado_jaque': opciones.modo_resaltado_jaque.value,
            'intervalo_parpadeo_jaque_ms': opciones.intervalo_parpadeo_jaque_ms,
            'repeticiones_parpadeo_jaque': opciones.repeticiones_parpadeo_jaque,
        },
    }


def preferencias_desde_datos(datos: dict) -> PreferenciasGraficas:
    if not isinstance(datos, dict) or datos.get('formato') != 'ajedrez-local-preferencias':
        raise ErrorPreferencias('El archivo no es una configuración gráfica de Ajedrez local.')
    version = datos.get('version')
    if type(version) is not int or version != VERSION_FORMATO_PREFERENCIAS:
        raise ErrorPreferencias('La versión del formato de preferencias no es compatible.')
    opciones = datos.get('opciones_visuales', {})
    if not isinstance(opciones, dict):
        raise ErrorPreferencias('Las opciones visuales deben ser un objeto JSON.')
    opciones = dict(opciones)
    try:
        modo = opciones.get('modo_resaltado_jaque', OPCIONES_VISUALES_PREDETERMINADAS.modo_resaltado_jaque.value)
        opciones['modo_resaltado_jaque'] = ModoResaltadoJaque(modo)
        return PreferenciasGraficas(
            identificador_tema=datos.get('tema', IDENTIFICADOR_TEMA_PREDETERMINADO),
            opciones_visuales=OpcionesVisuales(**opciones),
        )
    except (ValueError, TypeError) as error:
        raise ErrorPreferencias(f'La configuración gráfica contiene valores no válidos: {error}') from error


def cargar_preferencias(ruta: str | Path) -> PreferenciasGraficas:
    """Devuelve los valores predeterminados si no existe el archivo.

    Los errores de lectura y de formato se comunican al llamador. El archivo
    original se conserva incluso si no se puede utilizar.
    """
    try:
        datos = json.loads(Path(ruta).read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        return PreferenciasGraficas()
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ErrorPreferencias('El archivo de preferencias no contiene JSON válido.') from error
    return preferencias_desde_datos(datos)


def guardar_preferencias(preferencias: PreferenciasGraficas, ruta: str | Path) -> None:
    """Escribe primero un temporal vecino y sustituye el destino al terminar."""
    contenido = json.dumps(preferencias_a_datos(preferencias), ensure_ascii=False, indent=2) + '\n'
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                dir=destino.parent, prefix='.preferencias-', suffix='.tmp',
                                delete=False) as archivo:
            temporal = Path(archivo.name)
            archivo.write(contenido)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, destino)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
