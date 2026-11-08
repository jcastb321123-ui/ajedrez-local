"""Abrir y guardar desde la GUI sin confundir historial, análisis y partida."""

from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ajedrez.aplicacion import AplicacionAjedrez
from ajedrez.partida import Partida
from ajedrez.persistencia import cargar_partida, guardar_partida, partida_a_datos
from ajedrez.piezas import Color, PeonBlanco, Rey
from pruebas.test_partida_estado_inicial import posicion
from pruebas.test_persistencia import jugar, partida_con_piezas


class PruebasPersistenciaAplicacion(unittest.TestCase):
    def setUp(self):
        self.ventana = tk.Tk()
        self.ventana.withdraw()
        self.errores = []
        self.ventana.report_callback_exception = lambda tipo, error, traza: self.errores.append(error)
        self.addCleanup(self.ventana.destroy)
        self.addCleanup(self.assertFalse, self.errores)
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / 'partida.json'
        self.aplicacion = AplicacionAjedrez(ventana=self.ventana)

    def mover(self, origen, destino):
        vista = self.aplicacion.interfaz_partida
        for casilla in (origen, destino):
            fila, columna = posicion(casilla)
            lado = vista.casillero.tamanno_casilla
            x, y = (columna + 0.5) * lado, (7 - fila + 0.5) * lado
            vista.gestionar_clic_izquierdo(SimpleNamespace(x=x, y=y))

    def guardar(self):
        with patch('ajedrez.aplicacion.filedialog.asksaveasfilename', return_value=str(self.ruta)):
            self.aplicacion._boton_guardar_partida.invoke()
        self.assertTrue(self.ruta.is_file())

    def abrir(self):
        with patch('ajedrez.aplicacion.filedialog.askopenfilename', return_value=str(self.ruta)):
            self.aplicacion._boton_abrir_partida.invoke()

    def test_botones_guardan_abren_y_permiten_continuar_y_navegar(self):
        self.mover('e2', 'e4')
        self.guardar()
        anterior = self.aplicacion.interfaz_partida
        contenedor = self.aplicacion.contenedor_partida
        self.abrir()
        vista = self.aplicacion.interfaz_partida
        self.assertIsNot(vista, anterior)
        self.assertFalse(contenedor.winfo_exists())
        self.assertIs(vista.estado_mostrado, vista.sesion.estado_actual)
        self.assertIsNone(vista.casillero.casillas[posicion('e2')].id_pieza)
        self.assertIsNotNone(vista.casillero.casillas[posicion('e4')].id_pieza)
        self.assertEqual(vista.indicador_estado_partida.cget('text'), 'Turno de negras')
        vista.retroceder_movimiento()
        self.assertIs(vista.estado_mostrado, vista.sesion.partida.estado_inicial)
        vista.avanzar_movimiento()
        self.mover('e7', 'e5')
        self.assertEqual(vista.sesion.partida.contador_jugadas, 2)
        self.aplicacion._boton_guardar_partida.invoke()
        self.assertEqual(cargar_partida(self.ruta).contador_jugadas, 2)

    def test_guardar_desde_historial_o_analisis_conserva_partida_original(self):
        self.mover('e2', 'e4')
        vista = self.aplicacion.interfaz_partida
        vista.retroceder_movimiento()
        self.guardar()
        self.assertEqual(cargar_partida(self.ruta).contador_jugadas, 1)
        vista.alternar_analisis()
        vista.sesion_movimientos.solicitar_movimiento(posicion('d2'), posicion('d4'))
        self.guardar()
        recuperada = cargar_partida(self.ruta)
        self.assertEqual(recuperada.ultima_jugada.origen, posicion('e2'))
        self.assertIsNone(recuperada.tablero.pieza_en(posicion('d4')))
        self.assertFalse(self.aplicacion._hay_cambios_sin_guardar())

    def test_archivo_invalido_no_cambia_interfaz_ni_modelo(self):
        self.mover('e2', 'e4')
        vista = self.aplicacion.interfaz_partida
        self.ruta.write_text('{', encoding='utf-8')
        with (patch('ajedrez.aplicacion.messagebox.showerror') as aviso,
              patch('ajedrez.aplicacion.messagebox.askyesnocancel') as pregunta):
            self.abrir()
        aviso.assert_called_once()
        pregunta.assert_not_called()
        self.assertIs(self.aplicacion.interfaz_partida, vista)
        self.assertEqual(vista.sesion.partida.contador_jugadas, 1)

    def test_cancelar_apertura_y_guardado_conserva_la_partida(self):
        self.mover('e2', 'e4')
        vista = self.aplicacion.interfaz_partida
        guardar_partida(Partida(), self.ruta)
        with patch('ajedrez.aplicacion.messagebox.askyesnocancel', return_value=None):
            self.abrir()
        self.assertIs(self.aplicacion.interfaz_partida, vista)
        with patch('ajedrez.aplicacion.filedialog.asksaveasfilename', return_value=''):
            self.assertFalse(self.aplicacion.solicitar_guardar_partida())
        self.assertIsNone(self.aplicacion._ruta_partida)
        self.assertTrue(self.aplicacion._hay_cambios_sin_guardar())

    def test_no_pierde_cambios_al_fallar_el_guardado(self):
        self.mover('e2', 'e4')
        self.guardar()
        self.mover('e7', 'e5')
        with (patch('ajedrez.aplicacion.guardar_partida', side_effect=OSError('Sin permiso')),
              patch('ajedrez.aplicacion.messagebox.showerror') as error,
              patch('ajedrez.aplicacion.messagebox.askyesnocancel', return_value=True)):
            self.aplicacion.solicitar_cierre()
        self.assertTrue(self.ventana.winfo_exists())
        self.assertTrue(self.aplicacion._hay_cambios_sin_guardar())
        self.assertEqual(cargar_partida(self.ruta).contador_jugadas, 1)
        error.assert_called_once()

    def test_cierre_guarda_antes_de_destruir_ventana(self):
        self.mover('e2', 'e4')
        with (patch('ajedrez.aplicacion.messagebox.askyesnocancel', return_value=True),
              patch('ajedrez.aplicacion.filedialog.asksaveasfilename', return_value=str(self.ruta)),
              patch.object(self.ventana, 'destroy') as cerrar):
            self.aplicacion.solicitar_cierre()
            cerrar.assert_called_once()
        self.assertEqual(cargar_partida(self.ruta).contador_jugadas, 1)

    def test_guardar_al_crear_nueva_partida(self):
        self.mover('e2', 'e4')
        with (patch('ajedrez.aplicacion.messagebox.askyesnocancel', return_value=True),
              patch('ajedrez.aplicacion.filedialog.asksaveasfilename', return_value=str(self.ruta))):
            self.aplicacion.boton_nueva_partida.invoke()
        self.assertEqual(cargar_partida(self.ruta).contador_jugadas, 1)
        self.assertEqual(self.aplicacion.interfaz_partida.sesion.partida.contador_jugadas, 0)
        self.assertIsNone(self.aplicacion._ruta_partida)

    def test_abrir_el_mismo_archivo_despues_de_guardar_lo_actualiza(self):
        self.mover('e2', 'e4')
        self.guardar()
        self.mover('e7', 'e5')
        with patch('ajedrez.aplicacion.messagebox.askyesnocancel', return_value=True):
            self.abrir()
        self.assertEqual(self.aplicacion.interfaz_partida.sesion.partida.contador_jugadas, 2)
        self.assertFalse(self.aplicacion._hay_cambios_sin_guardar())

    def test_avisa_de_promocion_pendiente_antes_de_pedir_archivo(self):
        partida = partida_con_piezas({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                                     'a7': PeonBlanco()})
        self.aplicacion._crear_partida_local(partida=partida)
        self.aplicacion.interfaz_partida.sesion.solicitar_movimiento(posicion('a7'), posicion('a8'))
        with (patch('ajedrez.aplicacion.messagebox.showinfo') as aviso,
              patch('ajedrez.aplicacion.filedialog.asksaveasfilename') as elegir):
            self.assertFalse(self.aplicacion.solicitar_guardar_partida())
        aviso.assert_called_once()
        elegir.assert_not_called()

    def test_recuperar_partida_finalizada_mantiene_resultado_y_analisis(self):
        partida = Partida()
        jugar(partida, 'f2f3 e7e5 g2g4 d8h4')
        guardar_partida(partida, self.ruta)
        self.abrir()
        vista = self.aplicacion.interfaz_partida
        self.assertEqual(vista.sesion.partida.estado_partida, partida.estado_partida)
        self.assertTrue(vista.en_analisis)
        vista.retroceder_movimiento()
        self.assertEqual(vista.estado_mostrado.destino, posicion('g4'))
        self.assertEqual(vista.sesion.partida.contador_jugadas, 4)


if __name__ == '__main__':
    unittest.main()
