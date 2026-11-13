"""Comprueba la copia instalada; ejecutar con el Python del entorno nuevo y -I.

No añade las fuentes a sys.path ni sustituye las imágenes o los widgets por dobles.
"""

from importlib.metadata import distribution
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import sys
import sysconfig
import tkinter as tk
import unittest
from unittest.mock import patch

import ajedrez
from ajedrez.aplicacion import AplicacionAjedrez, main
from ajedrez.piezas import Color, PeonBlanco, PeonNegro
from ajedrez.partida import Partida
from ajedrez.persistencia import cargar_partida, guardar_partida
from ajedrez.repositorio_partidas import RepositorioPartidasSQLite


class ComprobacionInstalacion(unittest.TestCase):
    def test_biblioteca_sqlite_con_la_interfaz_instalada(self):
        with TemporaryDirectory() as carpeta:
            repositorio = RepositorioPartidasSQLite(Path(carpeta) / 'biblioteca.sqlite3')
            ventana = tk.Tk()
            ventana.withdraw()
            errores = []
            ventana.report_callback_exception = lambda tipo, error, traza: errores.append(error)
            try:
                aplicacion = AplicacionAjedrez(ventana=ventana, repositorio=repositorio)
                partida = aplicacion.interfaz_partida.sesion.partida
                self.assertIsNone(partida.procesar_solicitud((1, 4), (3, 4)))
                with patch('ajedrez.aplicacion.simpledialog.askstring', return_value='Instalación comprobada'):
                    self.assertTrue(aplicacion.solicitar_guardar_en_biblioteca())
                identificador = aplicacion._id_partida_biblioteca
                self.assertIsNone(partida.procesar_solicitud((6, 4), (4, 4)))
                self.assertTrue(aplicacion.solicitar_guardar_partida())
                aplicacion._boton_biblioteca.invoke()
                biblioteca = aplicacion._biblioteca
                biblioteca._boton_abrir.invoke()
                self.assertEqual(aplicacion.interfaz_partida.sesion.partida.contador_jugadas, 2)
                self.assertEqual(len(repositorio.listar_partidas()), 1)
                self.assertEqual(repositorio.cargar_partida(identificador).contador_jugadas, 2)
                aplicacion._boton_biblioteca.invoke()
                with patch('ajedrez.aplicacion.messagebox.askyesno', return_value=True):
                    aplicacion._biblioteca._boton_eliminar.invoke()
                self.assertEqual(repositorio.listar_partidas(), ())
                self.assertEqual(aplicacion.interfaz_partida.sesion.partida.contador_jugadas, 2)
                self.assertTrue(aplicacion._hay_cambios_sin_guardar())
                self.assertFalse(errores, repr(errores))
            finally:
                ventana.destroy()

    def test_guardado_y_recuperacion_del_paquete_instalado(self):
        partida = Partida()
        self.assertIsNone(partida.procesar_solicitud((1, 4), (3, 4)))
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'partida.json'
            guardar_partida(partida, ruta)
            recuperada = cargar_partida(ruta)
        self.assertIsNot(recuperada, partida)
        self.assertEqual(recuperada.contador_jugadas, 1)
        self.assertIs(recuperada.jugador, Color.Negro)
        self.assertIsNone(recuperada.procesar_solicitud((6, 4), (4, 4)))
        self.assertEqual(recuperada.contador_jugadas, 2)
        self.assertIs(recuperada.ultima_jugada.anterior.siguiente, recuperada.ultima_jugada)

    def test_paquete_metadatos_y_lanzador_instalados(self):
        self.assertTrue(sys.flags.isolated, 'Ejecuta este archivo con python -I.')
        ruta_paquete = Path(ajedrez.__file__).resolve()
        carpeta_instalacion = Path(sysconfig.get_path('purelib')).resolve()
        self.assertTrue(ruta_paquete.is_relative_to(carpeta_instalacion),
                        f'Se ha importado una copia externa al entorno: {ruta_paquete}')

        paquete = distribution('ajedrez-local')
        self.assertEqual(ruta_paquete, Path(paquete.locate_file('ajedrez/__init__.py')).resolve())
        self.assertEqual(paquete.metadata['Description-Content-Type'], 'text/markdown')
        self.assertTrue(paquete.metadata.get_payload().strip(), 'Falta el README del paquete.')
        lanzadores = [entrada for entrada in paquete.entry_points
                      if entrada.group == 'gui_scripts' and entrada.name == 'ajedrez']
        self.assertEqual(len(lanzadores), 1)
        self.assertIs(lanzadores[0].load(), main)
        nombre_lanzador = 'ajedrez.exe' if sys.platform == 'win32' else 'ajedrez'
        self.assertTrue((Path(sysconfig.get_path('scripts')) / nombre_lanzador).is_file())
        print(f'\nPaquete {paquete.version}: {ruta_paquete}', flush=True)

    def test_arranque_imagenes_y_movimientos_de_ambos_colores(self):
        ventana = tk.Tk()
        ventana.withdraw()
        self.addCleanup(ventana.destroy)
        aplicacion = AplicacionAjedrez(ventana=ventana)
        vista = aplicacion.interfaz_partida
        casillero = vista.casillero
        errores = []
        completado = False

        def registrar_error(tipo, error, traza):
            errores.append(error)
            ventana.quit()

        def comprobar():
            nonlocal completado
            try:
                self.assertEqual(len(casillero.casillas), 64)
                self.assertEqual(len(casillero.canvas.find_withtag('pieza')), 32)
                movimientos = (
                    ((1, 4), (3, 4), Color.Blanco, Color.Negro),
                    ((6, 4), (4, 4), Color.Negro, Color.Blanco),
                )
                for numero, (origen, destino, color, siguiente) in enumerate(movimientos, 1):
                    for fila, columna in (origen, destino):
                        evento = SimpleNamespace(
                            x=int((columna + 0.5) * casillero.tamanno_casilla),
                            y=int((7 - fila + 0.5) * casillero.tamanno_casilla),
                        )
                        vista.gestionar_clic_izquierdo(evento)

                    partida = vista.sesion.partida
                    jugada = partida.ultima_jugada
                    self.assertEqual((jugada.origen, jugada.destino), (origen, destino))
                    self.assertEqual(partida.contador_jugadas, numero)
                    self.assertIs(partida.jugador, siguiente)
                    self.assertIs(vista.estado_mostrado, vista.sesion.estado_actual)
                    tablero = vista.estado_mostrado.tablero
                    self.assertIsNone(tablero.pieza_en(origen))
                    pieza = tablero.pieza_en(destino)
                    self.assertIsInstance(pieza, (PeonBlanco, PeonNegro))
                    self.assertIs(pieza.color, color)
                    self.assertIsNone(casillero.casillas[origen].id_pieza)
                    imagen = casillero.casillas[destino].id_pieza
                    self.assertIsNotNone(imagen)
                    self.assertEqual(casillero.canvas.type(imagen), 'image')

                self.assertEqual(len(casillero.canvas.find_withtag('pieza')), 32)
                completado = True
            finally:
                ventana.quit()

        ventana.report_callback_exception = registrar_error
        ventana.after(0, comprobar)
        aplicacion.ejecutar()
        if errores:
            raise errores[0]
        self.assertTrue(completado, 'El bucle de eventos no ejecutó la comprobación.')


if __name__ == '__main__':
    unittest.main(verbosity=2)
