"""Reclamación por repetición: autenticación, emisores y contrato de sesión."""
import pickle
import unittest

from ajedrez.partida import EstadoPartida, EstadoPosicion, Partida
from ajedrez.piezas import Color
from ajedrez.sesion import ModalidadAsignacion, SesionAnalisis
from pruebas import test_abandono as apoyo
from pruebas.test_analisis_partida import mover, posicion
from pruebas.test_recuento_repeticiones import CICLO_BLANCAS, CICLO_NEGRAS
from pruebas.test_sesion import nueva_sesion, SesionDePrueba


def preparar_sesion(turno=Color.Blanco, anunciada=False, modalidad=ModalidadAsignacion.BLANCO_NEGRO,
                    contador=0, ciclos=2):
    sesion = nueva_sesion(modalidad)
    sesion.juego._partida = Partida(
        estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=contador),
        turno_inicial=turno,
    )
    ciclo = CICLO_BLANCAS if turno is Color.Blanco else CICLO_NEGRAS
    movimientos = ciclo * ciclos
    if anunciada:
        movimientos = movimientos[:-1]
    for movimiento in movimientos:
        if mover(sesion.partida, movimiento) is not None:
            raise AssertionError(movimiento)
    anuncio = (posicion(ciclo[-1][:2]), posicion(ciclo[-1][2:])) if anunciada else None
    return sesion, anuncio


class PruebasSesionReclamacionRepeticion(unittest.TestCase):
    def enviar_reclamacion(self, sesion, via, color, anuncio):
        emisor = next(e for e in (sesion.emisor_1, sesion.emisor_2)
                      if sesion.autenticador.autenticar(e.clave) is color)
        if via == "sesion":
            return sesion.reclamar_tablas_por_triple_repeticion(
                color, movimiento_anunciado=anuncio)
        if via == "emisor":
            return emisor.reclamar_tablas_por_triple_repeticion(movimiento_anunciado=anuncio)
        return sesion.juego.reclamar_tablas_por_triple_repeticion(
            emisor.clave, movimiento_anunciado=anuncio)

    def test_aceptacion_por_cada_via_con_colores_pactados_y_aleatorios(self):
        for via in ("juego", "emisor", "sesion"):
            for modalidad in ModalidadAsignacion:
                for turno in Color:
                    for anunciada in (False, True):
                        with self.subTest(via=via, modalidad=modalidad, turno=turno, anunciada=anunciada):
                            sesion, anuncio = preparar_sesion(turno, anunciada, modalidad)
                            color = sesion.partida.jugador
                            sesion.proponer_tablas(color)
                            datos = pickle.dumps(apoyo.datos_de_juego(sesion.partida))
                            self.assertIs(self.enviar_reclamacion(sesion, via, color, anuncio), True)
                            self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
                            self.assertIsNone(sesion.proponente_tablas)
                            self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), datos)

    def test_otro_color_o_clave_invalida_no_cambian_sesion(self):
        for via in ("juego", "emisor", "sesion"):
            for turno in Color:
                with self.subTest(via=via, turno=turno):
                    sesion, anuncio = preparar_sesion(turno, True)
                    contrario = Color.Negro if sesion.partida.jugador is Color.Blanco else Color.Blanco
                    sesion.proponer_tablas(contrario)
                    antes = pickle.dumps(sesion)
                    self.assertIs(self.enviar_reclamacion(sesion, via, contrario, anuncio), False)
                    self.assertIs(sesion.juego.reclamar_tablas_por_triple_repeticion(
                        "clave_no_registrada", movimiento_anunciado=anuncio), False)
                    self.assertEqual(pickle.dumps(sesion), antes)

    def test_rechazo_por_recuento_insuficiente_conserva_propuesta(self):
        for via in ("juego", "emisor", "sesion"):
            for anunciada in (False, True):
                with self.subTest(via=via, anunciada=anunciada):
                    sesion, anuncio = preparar_sesion(anunciada=anunciada, ciclos=1)
                    color = sesion.partida.jugador
                    sesion.proponer_tablas(color)
                    antes = pickle.dumps(sesion)
                    self.assertIs(self.enviar_reclamacion(sesion, via, color, anuncio), False)
                    self.assertEqual(pickle.dumps(sesion), antes)

    def test_consultas_actual_y_anunciada_respetan_color_controlado(self):
        for anunciada in (False, True):
            fuente, anuncio = preparar_sesion(anunciada=anunciada)
            for color in Color:
                with self.subTest(anunciada=anunciada, color=color):
                    sesion = apoyo.SesionUnColor(color)
                    sesion.juego._partida = fuente.partida
                    antes = pickle.dumps(sesion)
                    esperado = color is sesion.partida.jugador
                    self.assertIs(sesion.tablas_por_triple_repeticion_disponible(
                        movimiento_anunciado=anuncio), esperado)
                    self.assertIs(sesion.reclamacion_tablas_disponible(
                        movimiento_anunciado=anuncio), esperado)
                    self.assertEqual(pickle.dumps(sesion), antes)

    def test_contrato_base_consulta_sin_acceder_a_interfaz_juego(self):
        class SesionConReclamaciones(SesionDePrueba):
            @property
            def admite_reclamaciones_tablas(self):
                return True

        fuente, _ = preparar_sesion()
        sesion = SesionConReclamaciones(fuente.partida)
        antes = pickle.dumps(fuente.partida)
        self.assertFalse(hasattr(sesion, "juego"))
        self.assertIs(sesion.tablas_por_triple_repeticion_disponible(), True)
        self.assertIs(sesion.reclamacion_tablas_disponible(), True)
        self.assertEqual(pickle.dumps(fuente.partida), antes)

    def test_analisis_no_admite_reclamaciones_aunque_su_posicion_se_repita(self):
        sesion = SesionAnalisis(EstadoPosicion(), Color.Blanco)
        for movimiento in CICLO_BLANCAS * 2:
            self.assertIsNone(sesion.solicitar_movimiento(
                posicion(movimiento[:2]), posicion(movimiento[2:])))
        antes = pickle.dumps(sesion)
        self.assertEqual(sesion.partida.apariciones_posicion_actual, 3)
        self.assertFalse(sesion.tablas_por_triple_repeticion_disponible())
        self.assertFalse(sesion.reclamacion_tablas_disponible())
        with self.assertRaises(NotImplementedError):
            sesion.reclamar_tablas_por_triple_repeticion(Color.Blanco)
        self.assertEqual(pickle.dumps(sesion), antes)


if __name__ == "__main__":
    unittest.main()
