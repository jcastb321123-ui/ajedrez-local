"""Comprueba la copia instalada; ejecutar con el Python del entorno nuevo y -I.

No añade las fuentes a sys.path ni sustituye las imágenes o los widgets por dobles.
"""

from importlib.metadata import distribution
from pathlib import Path
from types import SimpleNamespace
import sys
import sysconfig
import tkinter as tk
import unittest

import ajedrez
from ajedrez.aplicacion import AplicacionAjedrez, main
from ajedrez.piezas import Color, PeonBlanco, PeonNegro


class ComprobacionInstalacion(unittest.TestCase):
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
