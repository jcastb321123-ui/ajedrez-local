"""Resaltados del estado mostrado con un Canvas real en una ventana oculta.

Las imágenes vacías permiten comprobar posición, registro y superposición,
no el aspecto del tema. No prueba el manejador de clics ni implementa IA o red.
"""

import pickle
import tkinter as tk
import unittest

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ajedrez.gráficos.graficos_tablero import Casillero
from ajedrez.gráficos.interfaz_partida import InterfazPartida
from ajedrez.interfaz_juego import PiezaPromocion
from ajedrez.partida import Partida
from ajedrez.piezas import Color
from pruebas.test_marcas_graficas import crear_tema
from pruebas.test_sesion import SesionDePrueba, enviar, nueva_sesion


class PruebasResaltadosUltimoMovimiento(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ventana = tk.Tk()
        except tk.TclError as error:
            raise unittest.SkipTest(f"Tk no disponible: {error}") from error
        cls.ventana.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.ventana.destroy()

    def setUp(self):
        self.imagen = tk.PhotoImage(master=self.ventana, width=60, height=60)
        self.tema = crear_tema(self.imagen)
        for nombre in ("peon", "caballo", "alfil", "torre", "dama", "rey"):
            for color in (Color.Blanco, Color.Negro):
                self.tema.piezas[nombre, color, "normal"] = self.imagen
        self.sesion = nueva_sesion()
        self.casillero = Casillero(self.ventana, self.tema)
        self.interfaz = InterfazPartida(self.sesion, self.casillero)
        self.addCleanup(self.casillero.contenedor.destroy)

    def registrar(self, movimiento):
        anterior = self.sesion.partida.ultima_jugada
        enviar(self.sesion, movimiento)
        self.assertIsNot(self.sesion.partida.ultima_jugada, anterior)
        return self.sesion.estado_actual

    def ids_resaltados(self, casillero=None):
        casillero = self.casillero if casillero is None else casillero
        return set(casillero.canvas.find_withtag("marca:ultima_jugada_origen")) | set(
            casillero.canvas.find_withtag("marca:ultima_jugada_destino"))

    def comprobar_resaltados(self, estado, casillero=None):
        casillero = self.casillero if casillero is None else casillero
        canvas = casillero.canvas
        orden = canvas.find_all()
        for clave, coordenadas in (("ultima_jugada_origen", estado.origen),
                                   ("ultima_jugada_destino", estado.destino)):
            clave_elemento = f"marca:{clave}"
            registradas = {
                posicion: casilla.ids_elementos_por_clave[clave_elemento]
                for posicion, casilla in casillero.casillas.items()
                if clave_elemento in casilla.ids_elementos_por_clave
            }
            if estado.origen is None or estado.destino is None:
                self.assertEqual(registradas, {})
                self.assertEqual(canvas.find_withtag(clave_elemento), ())
                continue
            self.assertEqual(set(registradas), {coordenadas})
            id_resaltado = registradas[coordenadas]
            self.assertEqual(canvas.find_withtag(clave_elemento), (id_resaltado,))
            self.assertIn("resaltado", canvas.gettags(id_resaltado))
            self.assertIn("uso:estado", canvas.gettags(id_resaltado))
            casilla = casillero.casillas[coordenadas]
            self.assertIn(id_resaltado, casilla.variables_id["resaltado"])
            self.assertEqual(canvas.coords(id_resaltado), canvas.coords(casilla.id_imagen))
            self.assertLess(orden.index(casilla.id_imagen), orden.index(id_resaltado))
            if casilla.id_pieza is not None:
                self.assertLess(orden.index(id_resaltado), orden.index(casilla.id_pieza))

    def test_posicion_inicial_no_tiene_resaltados(self):
        self.comprobar_resaltados(self.sesion.partida.estado_inicial)
        self.assertEqual(len(self.casillero.canvas.find_all()), 96)

    def test_mostrar_estado_aplica_origen_y_destino_bajo_las_piezas(self):
        estado = self.registrar("e2e4")
        self.interfaz.mostrar_estado(estado)
        self.comprobar_resaltados(estado)
        self.assertIsNone(self.casillero.casillas[(1, 4)].id_pieza)
        self.assertIsNotNone(self.casillero.casillas[(3, 4)].id_pieza)

    def test_actualizar_reemplaza_solo_los_resaltados_sin_redibujar_tablero(self):
        primera = self.registrar("e2e4")
        self.interfaz.mostrar_estado(primera)
        anteriores = self.ids_resaltados()
        otros_dibujos = set(self.casillero.canvas.find_all()) - anteriores
        segunda = self.registrar("e7e5")
        self.interfaz.estado_mostrado = segunda
        modelo_antes = pickle.dumps(self.sesion.partida)
        self.interfaz.actualizar_resaltados_ultimo_movimiento()
        self.comprobar_resaltados(segunda)
        self.assertEqual(set(self.casillero.canvas.find_all()) - self.ids_resaltados(),
                         otros_dibujos)
        self.assertTrue(anteriores.isdisjoint(self.casillero.canvas.find_all()))
        self.assertEqual(pickle.dumps(self.sesion.partida), modelo_antes)

    def test_actualizar_conserva_seleccion_jaque_y_anotaciones(self):
        estado = self.registrar("e2e4")
        self.interfaz.mostrar_estado(estado)
        posicion = (3, 4)
        self.interfaz.origen_seleccionado = posicion
        claves = ("seleccion", "jaque", "fondo_azul", "circulo_rojo", "destino_legal")
        for clave in claves:
            self.casillero.aplicar_marca(posicion, clave)
        casilla = self.casillero.casillas[posicion]
        conservados = {clave: casilla.ids_elementos_por_clave[f"marca:{clave}"]
                       for clave in claves}
        self.interfaz.actualizar_resaltados_ultimo_movimiento()
        self.comprobar_resaltados(estado)
        self.assertEqual(self.interfaz.origen_seleccionado, posicion)
        for clave, identificador in conservados.items():
            self.assertEqual(casilla.ids_elementos_por_clave[f"marca:{clave}"], identificador)
            self.assertEqual(self.casillero.canvas.type(identificador), "image")

    def test_repetir_no_acumula_dibujos_ni_referencias(self):
        estado = self.registrar("e2e4")
        self.interfaz.mostrar_estado(estado)
        cantidad = len(self.casillero.canvas.find_all())
        for _ in range(25):
            anteriores = self.ids_resaltados()
            self.interfaz.actualizar_resaltados_ultimo_movimiento()
            self.comprobar_resaltados(estado)
            self.assertEqual(len(self.casillero.canvas.find_all()), cantidad)
            for casilla in self.casillero.casillas.values():
                self.assertTrue(anteriores.isdisjoint(casilla.ids_elementos_por_clave.values()))
                for ids_capa in casilla.variables_id.values():
                    self.assertTrue(anteriores.isdisjoint(ids_capa))

    def test_historial_y_retroceso_marcan_el_estado_mostrado(self):
        primera = self.registrar("e2e4")
        segunda = self.registrar("e7e5")
        self.interfaz.mostrar_estado(segunda)
        modelo_antes = pickle.dumps(self.sesion.partida)
        self.interfaz.retroceder_movimiento()
        self.assertIs(self.interfaz.estado_mostrado, primera)
        self.comprobar_resaltados(primera)
        self.interfaz.retroceder_movimiento()
        self.comprobar_resaltados(self.sesion.partida.estado_inicial)
        self.interfaz.mostrar_estado(primera)
        self.comprobar_resaltados(primera)
        self.assertIs(self.sesion.estado_actual, segunda)
        self.assertEqual(pickle.dumps(self.sesion.partida), modelo_antes)

    def test_volver_a_raiz_retira_marcas_aunque_no_se_redibujen_piezas(self):
        self.interfaz.mostrar_estado(self.registrar("e2e4"))
        self.interfaz.estado_mostrado = self.sesion.partida.estado_inicial
        self.interfaz.actualizar_resaltados_ultimo_movimiento()
        self.comprobar_resaltados(self.sesion.partida.estado_inicial)

    def test_constructor_recupera_el_movimiento_de_una_partida_empezada(self):
        estado = self.registrar("e2e4")
        self.casillero.mostrar_posicion(self.interfaz._obtener_distribucion(estado))
        self.interfaz = InterfazPartida(self.sesion, self.casillero)
        self.comprobar_resaltados(estado)

    def test_dos_vistas_y_sesion_sin_juego_comparten_solo_el_estado(self):
        estado = self.registrar("e2e4")
        self.interfaz.mostrar_estado(estado)
        otra_sesion = SesionDePrueba(self.sesion.partida)
        self.assertFalse(hasattr(otra_sesion, "juego"))
        otro_casillero = Casillero(self.ventana, self.tema,
                                  distribucion=self.interfaz._obtener_distribucion(estado))
        self.addCleanup(otro_casillero.contenedor.destroy)
        otra_interfaz = InterfazPartida(otra_sesion, otro_casillero)
        self.casillero.aplicar_marca((3, 4), "seleccion")
        self.casillero.aplicar_marca((4, 4), "fondo_azul")
        otra_interfaz.actualizar_resaltados_ultimo_movimiento()
        self.comprobar_resaltados(estado)
        self.comprobar_resaltados(estado, otro_casillero)
        self.assertEqual(otro_casillero.canvas.find_withtag("uso:seleccion"), ())
        self.assertEqual(otro_casillero.canvas.find_withtag("uso:estrategia"), ())

    def test_raiz_importada_con_movimiento_previo_conserva_sus_marcas(self):
        estado = self.registrar("e2e4")
        sesion = SesionDePrueba(Partida(estado_inicial=estado))
        self.casillero.mostrar_posicion(self.interfaz._obtener_distribucion(estado))
        self.interfaz = InterfazPartida(sesion, self.casillero)
        self.assertIsNone(sesion.partida.ultima_jugada)
        self.comprobar_resaltados(estado)

    def test_enroque_y_captura_al_paso_marcan_el_origen_y_destino_de_la_jugada(self):
        for movimientos in ("e2e4 a7a6 g1f3 a6a5 f1e2 b7b6 e1g1",
                             "e2e4 a7a6 e4e5 d7d5 e5d6"):
            with self.subTest(movimientos=movimientos):
                sesion = nueva_sesion()
                for movimiento in movimientos.split():
                    enviar(sesion, movimiento)
                self.assertEqual(sesion.partida.contador_jugadas, len(movimientos.split()))
                self.interfaz.mostrar_estado(sesion.estado_actual)
                self.comprobar_resaltados(sesion.estado_actual)

    def test_rechazo_y_promocion_pendiente_no_sustituyen_el_movimiento_confirmado(self):
        for movimiento in "a2a4 b7b5 a4b5 a7a6 b5a6 h7h6 a6a7 h6h5".split():
            self.registrar(movimiento)
        aceptado = self.sesion.estado_actual
        self.interfaz.mostrar_estado(aceptado)
        enviar(self.sesion, "a7a5")
        self.assertIs(self.sesion.estado_actual, aceptado)
        self.interfaz.actualizar_resaltados_ultimo_movimiento()
        self.comprobar_resaltados(aceptado)
        enviar(self.sesion, "a7b8")
        self.assertIsNotNone(self.sesion.jugada_pendiente)
        self.assertIs(self.sesion.estado_actual, aceptado)
        self.interfaz.actualizar_resaltados_ultimo_movimiento()
        self.comprobar_resaltados(aceptado)
        self.sesion.elegir_promocion(PiezaPromocion.REINA)
        self.assertIsNone(self.sesion.jugada_pendiente)
        self.interfaz.mostrar_estado(self.sesion.estado_actual)
        self.comprobar_resaltados(self.sesion.estado_actual)


if __name__ == "__main__":
    unittest.main()
