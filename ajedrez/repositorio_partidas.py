"""Biblioteca SQLite de partidas, independiente de la modalidad de juego.

Almacena el modelo Partida. La sesión decide cuándo permite guardarlo; sus
credenciales y la configuración de IA o red no forman parte de ese modelo.
La carga devuelve una Partida independiente; el llamador elige su sesión.
"""

from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3

from .partida import Partida
from .persistencia import ErrorArchivoPartida, partida_a_datos, partida_desde_datos


def obtener_ruta_biblioteca_predeterminada() -> Path:
    """Ubica los datos del usuario fuera del código y del paquete instalado."""
    carpeta = Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.local' / 'share')
    return carpeta / 'ajedrez-local' / 'biblioteca.sqlite3'


@dataclass(frozen=True)
class ResumenPartida:
    """Datos de una entrada de la biblioteca, con fechas en UTC.

    Es una instantánea inmutable de sus metadatos, independiente del modelo
    y de la sesión que vaya a utilizarlo.
    """

    id_partida: int
    titulo: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class RepositorioPartidasSQLite:
    def __init__(self, ruta_base_datos: str | Path):
        """Recibe la ruta del archivo; su carpeta debe existir previamente."""
        self._ruta_base_datos = Path(ruta_base_datos)
        self._inicializar_base_datos()

    def guardar_partida(self, partida: Partida, titulo: str) -> int:
        """Inserta una instantánea nueva y devuelve su identificador confirmado.

        Cada llamada crea un registro, aunque se repita el título. Las fechas
        iniciales coinciden y se expresan en UTC con formato ISO 8601.
        """
        contenido_json = json.dumps(partida_a_datos(partida), ensure_ascii=False)
        fecha = datetime.now(UTC).isoformat()
        with closing(sqlite3.connect(self._ruta_base_datos, autocommit=False)) as conexion:
            with conexion:
                cursor = conexion.execute(
                    """
                    INSERT INTO partidas (
                        titulo, contenido_json, fecha_creacion, fecha_actualizacion
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (titulo, contenido_json, fecha, fecha),
                )
                id_partida = cursor.lastrowid
        return id_partida

    def actualizar_partida(self, id_partida: int, partida: Partida, titulo: str) -> None:
        """Sustituye el contenido y el título conservando id y fecha de creación.

        Renueva la fecha de actualización en UTC, incluso si el contenido es
        igual. Lanza KeyError si el identificador no existe. Una promoción
        pendiente provoca ErrorArchivoPartida, igual que al guardar.
        Si falla la escritura, se revierte toda la actualización.
        """
        contenido_json = json.dumps(partida_a_datos(partida), ensure_ascii=False)
        fecha = datetime.now(UTC).isoformat()
        with closing(sqlite3.connect(self._ruta_base_datos, autocommit=False)) as conexion:
            with conexion:
                cursor = conexion.execute(
                    """
                    UPDATE partidas
                    SET titulo = ?, contenido_json = ?, fecha_actualizacion = ?
                    WHERE id_partida = ?
                    """,
                    (titulo, contenido_json, fecha, id_partida),
                )
                if cursor.rowcount == 0:
                    raise KeyError(id_partida)

    def cargar_partida(self, id_partida: int) -> Partida:
        """Reconstruye el registro indicado sin modificarlo ni crear una sesión.

        Lanza KeyError si el identificador no existe y ErrorArchivoPartida si
        el contenido guardado no es válido. Los errores de SQLite se propagan.
        Cada carga devuelve un modelo nuevo con su historial reconstruido.
        """
        with closing(sqlite3.connect(self._ruta_base_datos, autocommit=False)) as conexion:
            registro = conexion.execute(
                'SELECT contenido_json FROM partidas WHERE id_partida = ?',
                (id_partida,),
            ).fetchone()

        if registro is None:
            raise KeyError(id_partida)
        try:
            datos = json.loads(registro[0])
        except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
            raise ErrorArchivoPartida(
                f'La partida {id_partida} no contiene un documento JSON válido.'
            ) from error
        return partida_desde_datos(datos)

    def listar_partidas(self) -> tuple[ResumenPartida, ...]:
        """Devuelve los metadatos sin leer ni reconstruir los historiales.

        Ordena por fecha de actualización descendente y, en caso de empate,
        por identificador descendente. Una biblioteca vacía devuelve ().
        El resultado queda disponible después de cerrar la conexión.
        """
        with closing(sqlite3.connect(self._ruta_base_datos, autocommit=False)) as conexion:
            registros = conexion.execute(
                """
                SELECT id_partida, titulo, fecha_creacion, fecha_actualizacion
                FROM partidas
                ORDER BY fecha_actualizacion DESC, id_partida DESC
                """
            ).fetchall()
        return tuple(
            ResumenPartida(
                id_partida=identificador,
                titulo=titulo,
                fecha_creacion=datetime.fromisoformat(creacion),
                fecha_actualizacion=datetime.fromisoformat(actualizacion),
            )
            for identificador, titulo, creacion, actualizacion in registros
        )

    def eliminar_partida(self, id_partida: int) -> None:
        """Elimina sólo el registro indicado; lanza KeyError si no existe."""
        with closing(sqlite3.connect(self._ruta_base_datos, autocommit=False)) as conexion:
            with conexion:
                cursor = conexion.execute('DELETE FROM partidas WHERE id_partida = ?', (id_partida,))
                if cursor.rowcount == 0:
                    raise KeyError(id_partida)

    def _inicializar_base_datos(self) -> None:
        """Crea la tabla cuando falta y deja cerrada la conexión al terminar."""
        with closing(sqlite3.connect(self._ruta_base_datos, autocommit=False)) as conexion:
            # Este contexto confirma la transacción o la revierte si falla.
            # closing se ocupa del cierre, también si se produce una excepción.
            with conexion:
                conexion.execute("""
                    CREATE TABLE IF NOT EXISTS partidas (
                        id_partida INTEGER PRIMARY KEY,
                        titulo TEXT NOT NULL,
                        contenido_json TEXT NOT NULL,
                        fecha_creacion TEXT NOT NULL,
                        fecha_actualizacion TEXT NOT NULL
                    )
                """)
