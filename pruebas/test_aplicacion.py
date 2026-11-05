"""Contrato del paquete y arranque de la aplicación con sus recursos incluidos."""

from contextlib import chdir
import importlib
import pickle
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import patch

from ajedrez.gráficos.temas_graficos import (
    CARPETA_RECURSOS_PREDETERMINADA, cargar_tema,
)


RAIZ_PROYECTO = Path(__file__).resolve().parents[1]


class PruebasPaquete(unittest.TestCase):
    def ejecutar_python(self, codigo):
        resultado = subprocess.run(
            [sys.executable, '-B', '-X', 'utf8', '-c', codigo],
            cwd=RAIZ_PROYECTO, capture_output=True, text=True,
            encoding='utf-8', timeout=30,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    def test_importar_no_abre_ventanas_ni_carga_modulos_sueltos(self):
        self.ejecutar_python('''
import sys
from unittest.mock import patch
with patch('tkinter.Tk', side_effect=AssertionError('Ventana al importar')):
    import ajedrez.aplicacion
    import ajedrez.gráficos.panel_analisis
    import pruebas.gui_prueba4
assert callable(ajedrez.aplicacion.main)
assert not {'partida', 'piezas', 'sesion', 'tablero', 'gráficos'} & sys.modules.keys()
''')

    def test_ejecutar_como_modulo_invoca_main(self):
        self.ejecutar_python('''
import runpy
from unittest.mock import patch
with (patch('tkinter.Tk') as ventana,
      patch('tkinter.Frame') as frame,
      patch('tkinter.Button'),
      patch('ajedrez.gráficos.temas_graficos.cargar_tema') as tema,
      patch('ajedrez.gráficos.graficos_tablero.Casillero') as casillero,
      patch('ajedrez.gráficos.interfaz_partida.InterfazPartida') as interfaz):
    runpy.run_module('ajedrez.aplicacion', run_name='__main__')
    ventana.assert_called_once_with()
    ventana.return_value.title.assert_called_once_with('Ajedrez')
    ventana.return_value.mainloop.assert_called_once_with()
    assert frame.call_count == 2
    assert all(llamada.args == (ventana.return_value,) for llamada in frame.call_args_list)
    tema.assert_called_once_with(ventana.return_value)
    casillero.assert_called_once_with(frame.return_value, tema.return_value)
    assert interfaz.call_args.kwargs['contenedor'] is frame.return_value
''')

    def test_recursos_incluidos_no_dependen_del_directorio_actual(self):
        carpeta_esperada = RAIZ_PROYECTO / 'ajedrez' / 'recursos' / 'ajedrez-recursos-v1'
        self.assertEqual(CARPETA_RECURSOS_PREDETERMINADA, carpeta_esperada)
        self.assertTrue((carpeta_esperada / 'catalogo.json').is_file())
        with chdir(RAIZ_PROYECTO / 'pruebas'):
            with patch('ajedrez.gráficos.temas_graficos.tk.PhotoImage',
                       side_effect=lambda **datos: SimpleNamespace(**datos)) as imagen:
                cargar_tema(object())
                self.assertGreater(imagen.call_count, 0)
                for llamada in imagen.call_args_list:
                    ruta = Path(llamada.kwargs['file'])
                    self.assertTrue(ruta.is_relative_to(carpeta_esperada))
                    self.assertTrue(ruta.is_file(), str(ruta))

    def test_aplicacion_y_demo_arrancan_y_permiten_e2_e4(self):
        crear_tk = tk.Tk
        for nombre in ('ajedrez.aplicacion', 'pruebas.gui_prueba4'):
            with self.subTest(modulo=nombre):
                modulo = importlib.import_module(nombre)
                crear_interfaz = modulo.InterfazPartida
                ventanas, vistas, errores = [], [], []
                completado = False

                def registrar_interfaz(*args, **kwargs):
                    vista = crear_interfaz(*args, **kwargs)
                    vistas.append(vista)
                    return vista

                def comprobar(ventana):
                    nonlocal completado
                    try:
                        if nombre == 'ajedrez.aplicacion':
                            self.assertEqual(ventana.title(), 'Ajedrez')
                        self.assertEqual(len(vistas), 1)
                        vista = vistas[0]
                        self.assertIs(vista.panel_navegacion.master, vista.contenedor)
                        self.assertIs(vista.casillero.contenedor.master, vista.contenedor)
                        self.assertEqual(len(vista.casillero.casillas), 64)
                        vista.gestionar_clic_izquierdo(SimpleNamespace(x=270, y=390))
                        vista.gestionar_clic_izquierdo(SimpleNamespace(x=270, y=270))
                        jugada = vista.sesion.partida.ultima_jugada
                        self.assertEqual((jugada.origen, jugada.destino), ((1, 4), (3, 4)))
                        completado = True
                    except Exception as error:
                        errores.append(error)
                    finally:
                        ventana.destroy()

                def crear_ventana(*args, **kwargs):
                    try:
                        ventana = crear_tk(*args, **kwargs)
                    except tk.TclError as error:
                        raise unittest.SkipTest(str(error)) from error
                    ventanas.append(ventana)
                    ventana.withdraw()
                    ventana.report_callback_exception = lambda tipo, error, traza: errores.append(error)
                    ventana.after(0, comprobar, ventana)
                    return ventana

                try:
                    with (patch.object(modulo.tk, 'Tk', side_effect=crear_ventana),
                          patch.object(modulo, 'InterfazPartida', side_effect=registrar_interfaz)):
                        modulo.main()
                    self.assertFalse(errores, repr(errores))
                    self.assertTrue(completado, 'No se ejecutó la comprobación del bucle de eventos.')
                finally:
                    for ventana in ventanas:
                        try:
                            ventana.destroy()
                        except tk.TclError:
                            pass


class PruebasNuevaPartida(unittest.TestCase):
    def setUp(self):
        self.modulo = importlib.import_module('ajedrez.aplicacion')
        self.crear_tk = tk.Tk
        self.errores = []
        self.addCleanup(self.assertFalse, self.errores)

    def crear_ventana(self):
        ventana = self.crear_tk()
        ventana.withdraw()
        ventana.report_callback_exception = lambda tipo, error, traza: self.errores.append(error)
        self.addCleanup(ventana.destroy)
        return ventana

    def crear_aplicacion(self):
        return self.modulo.AplicacionAjedrez(ventana=self.crear_ventana())

    def mover_e2_e4(self, vista):
        vista.gestionar_clic_izquierdo(SimpleNamespace(x=270, y=390))
        vista.gestionar_clic_izquierdo(SimpleNamespace(x=270, y=270))
        self.assertEqual(vista.sesion.partida.contador_jugadas, 1)

    def test_reutiliza_ventana_proporcionada_y_arranca_sin_confirmacion(self):
        ventana = self.crear_ventana()
        with (patch.object(self.modulo.tk, 'Tk') as construir,
              patch('tkinter.messagebox.askyesno') as preguntar):
            aplicacion = self.modulo.AplicacionAjedrez(ventana=ventana)
        construir.assert_not_called()
        preguntar.assert_not_called()
        self.assertIs(aplicacion.ventana, ventana)
        self.assertEqual(ventana.title(), 'Ajedrez')
        self.assertIs(aplicacion.panel_controles.master, ventana)
        self.assertIs(aplicacion.contenedor_partida.master, ventana)
        self.assertEqual(len(aplicacion.interfaz_partida.casillero.casillas), 64)
        self.mover_e2_e4(aplicacion.interfaz_partida)

    def test_crea_una_ventana_cuando_se_omite_el_argumento(self):
        with patch.object(self.modulo.tk, 'Tk', side_effect=self.crear_ventana) as construir:
            aplicacion = self.modulo.AplicacionAjedrez()
        construir.assert_called_once_with()
        self.assertTrue(aplicacion.ventana.winfo_exists())
        self.assertIs(aplicacion.contenedor_partida.master, aplicacion.ventana)

    def test_cancelar_conserva_partida_y_anotaciones(self):
        aplicacion = self.crear_aplicacion()
        vista = aplicacion.interfaz_partida
        contenedor = aplicacion.contenedor_partida
        self.mover_e2_e4(vista)
        vista.casillero.aplicar_marca((2, 0), 'fondo_azul')
        dibujos = vista.casillero.canvas.find_all()
        partida = pickle.dumps(vista.sesion.partida)
        with patch('tkinter.messagebox.askyesno', return_value=False) as preguntar:
            aplicacion.boton_nueva_partida.invoke()
        preguntar.assert_called_once()
        self.assertIs(aplicacion.interfaz_partida, vista)
        self.assertIs(aplicacion.contenedor_partida, contenedor)
        self.assertTrue(contenedor.winfo_exists())
        self.assertEqual(pickle.dumps(vista.sesion.partida), partida)
        self.assertEqual(vista.casillero.canvas.find_all(), dibujos)

    def test_confirmar_sustituye_partida_conservando_ventana_tema_y_controles(self):
        with patch.object(self.modulo, 'cargar_tema', wraps=self.modulo.cargar_tema) as cargar:
            aplicacion = self.crear_aplicacion()
            ventana, tema = aplicacion.ventana, aplicacion.tema
            controles, boton = aplicacion.panel_controles, aplicacion.boton_nueva_partida
            for _ in range(2):
                anterior = aplicacion.interfaz_partida
                contenedor = aplicacion.contenedor_partida
                self.mover_e2_e4(anterior)
                anterior.casillero.aplicar_marca((2, 0), 'fondo_azul')
                with patch('tkinter.messagebox.askyesno', return_value=True) as preguntar:
                    boton.invoke()
                preguntar.assert_called_once()
                actual = aplicacion.interfaz_partida
                self.assertIsNot(actual, anterior)
                self.assertIsNot(actual.sesion, anterior.sesion)
                self.assertFalse(contenedor.winfo_exists())
                self.assertIs(aplicacion.ventana, ventana)
                self.assertIs(aplicacion.tema, tema)
                self.assertIs(aplicacion.panel_controles, controles)
                self.assertIs(aplicacion.boton_nueva_partida, boton)
                self.assertIs(actual.casillero.tema, tema)
                self.assertEqual(actual.sesion.partida.contador_jugadas, 0)
                self.assertIsNone(actual.sesion.partida.ultima_jugada)
                self.assertFalse(actual.casillero.anotaciones_estrategicas)
                self.assertEqual(actual.indicador_estado_partida.cget('text'), 'Turno de blancas')
                self.assertEqual(len(actual.casillero.canvas.find_withtag('pieza')), 32)
            cargar.assert_called_once_with(ventana)


if __name__ == '__main__':
    unittest.main()
