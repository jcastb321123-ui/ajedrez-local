"""Triple repetición reclamable y cinco apariciones automáticas."""
import pickle
import unittest

from ajedrez.editor_posicion import EditorPosicion
from ajedrez.partida import EstadoPartida, MotivoRechazoMovimiento, Partida
from ajedrez.piezas import Caballo, Color, PeonBlanco, PeonNegro, Rey
from ajedrez.sesion import SesionAnalisis
from pruebas.test_analisis_partida import estado_minimo, mover, posicion
from pruebas.test_contador_tablas import preparar
from pruebas.test_recuento_repeticiones import CICLO_BLANCAS, CICLO_NEGRAS
from pruebas.test_sesion import enviar, nueva_sesion


def anuncio(movimiento):
    if movimiento is None:
        return None
    return posicion(movimiento[:2]), posicion(movimiento[2:])


class PruebasTablasRepeticion(unittest.TestCase):
    def jugar(self, partida, movimientos):
        for movimiento in movimientos:
            self.assertIsNone(mover(partida, movimiento))

    def consultar(self, partida, esperado, movimiento=None):
        antes = pickle.dumps(partida)
        self.assertIs(partida.tablas_por_triple_repeticion_disponible(
            movimiento_anunciado=anuncio(movimiento)), esperado)
        self.assertEqual(pickle.dumps(partida), antes)

    def reclamar(self, partida, esperado, movimiento=None):
        antes = pickle.dumps(partida)
        datos = {clave: valor for clave, valor in vars(partida).items()
                 if clave != "_estado_partida"}
        contenido = pickle.dumps(datos)
        self.assertIs(partida.reclamar_tablas_por_triple_repeticion(
            movimiento_anunciado=anuncio(movimiento)), esperado)
        if esperado:
            self.assertIs(partida.estado_partida, EstadoPartida.TABLAS)
            despues = {clave: valor for clave, valor in vars(partida).items()
                       if clave != "_estado_partida"}
            self.assertEqual(pickle.dumps(despues), contenido)
            for clave, valor in datos.items():
                self.assertIs(despues[clave], valor)
        else:
            self.assertEqual(pickle.dumps(partida), antes)

    def test_tercera_y_cuarta_reclamables_quinta_automatica_en_ambos_turnos(self):
        for turno, ciclo in ((Color.Blanco, CICLO_BLANCAS),
                             (Color.Negro, CICLO_NEGRAS)):
            with self.subTest(turno=turno):
                partida = Partida(turno_inicial=turno)
                self.consultar(partida, False)
                for vueltas in range(1, 5):
                    self.jugar(partida, ciclo)
                    self.assertEqual(partida.apariciones_posicion_actual, vueltas + 1)
                    self.assertIs(partida.estado_partida,
                                  EstadoPartida.TABLAS if vueltas == 4 else EstadoPartida.EN_CURSO)
                    self.consultar(partida, vueltas in (2, 3))

    def test_reclamacion_actual_cambia_solo_el_resultado(self):
        for turno, ciclo in ((Color.Blanco, CICLO_BLANCAS),
                             (Color.Negro, CICLO_NEGRAS)):
            with self.subTest(turno=turno):
                partida = Partida(turno_inicial=turno)
                self.jugar(partida, ciclo)
                self.reclamar(partida, False)
                self.jugar(partida, ciclo)
                self.reclamar(partida, True)
                self.reclamar(partida, False)

    def test_anuncio_completa_tercera_sin_ejecutar_ni_registrar(self):
        for turno, ciclo in ((Color.Blanco, CICLO_BLANCAS),
                             (Color.Negro, CICLO_NEGRAS)):
            with self.subTest(turno=turno):
                partida = Partida(turno_inicial=turno)
                self.jugar(partida, ciclo[:3])
                self.consultar(partida, False, ciclo[-1])
                self.reclamar(partida, False, ciclo[-1])
                self.jugar(partida, ciclo[3:] + ciclo[:3])
                self.consultar(partida, False)
                self.consultar(partida, True, ciclo[-1])
                self.reclamar(partida, True, ciclo[-1])
                self.assertEqual(partida.contador_jugadas, 7)

    def test_anuncio_evalua_destino_aunque_actual_ya_sea_reclamable(self):
        partida = Partida()
        self.jugar(partida, CICLO_BLANCAS * 2)
        self.consultar(partida, True)
        self.consultar(partida, False, "e2e4")
        self.reclamar(partida, False, "e2e4")
        self.consultar(partida, True)

    def test_anuncios_invalidos_y_partida_finalizada_no_alteran_nada(self):
        partida = Partida()
        self.jugar(partida, CICLO_BLANCAS * 2)
        for movimiento in ("e4e5", "g8f6", "g1g3"):
            with self.subTest(movimiento=movimiento):
                self.consultar(partida, False, movimiento)
                self.reclamar(partida, False, movimiento)
        partida.abandonar(Color.Blanco)
        self.consultar(partida, False)
        self.consultar(partida, False, "g1f3")
        self.reclamar(partida, False)

    def test_promocion_pendiente_no_admite_reclamacion(self):
        raiz = preparar(
            {"h1": Rey(Color.Blanco), "h8": Rey(Color.Negro), "a7": PeonBlanco()}, 0
        )
        partida = Partida(estado_inicial=raiz)
        self.assertIsNotNone(mover(partida, "a7a8"))
        self.assertTrue(partida.promocion_pendiente)
        self.consultar(partida, False)
        self.consultar(partida, False, "h1g1")
        self.reclamar(partida, False)

    def test_ciclos_distintos_tambien_cuentan_como_repeticion(self):
        partida = Partida()
        self.jugar(partida, CICLO_BLANCAS + ("b1c3", "b8c6", "c3b1", "c6b8"))
        self.consultar(partida, True)
        self.assertEqual(partida.apariciones_posicion_actual, 3)

    def test_posibilidad_al_paso_caducada_distingue_la_raiz(self):
        for vecino, esperado in ((True, False), (False, True)):
            with self.subTest(vecino=vecino):
                piezas = {"e1": Rey(Color.Blanco), "e8": Rey(Color.Negro),
                          "g1": Caballo(Color.Blanco), "g8": Caballo(Color.Negro),
                          "d5": PeonNegro()}
                if vecino:
                    piezas["e5"] = PeonBlanco()
                raiz = EditorPosicion(estado_minimo(piezas), Color.Blanco).construir_estado(
                    turno=Color.Blanco, enroques=set(), peon_al_paso=posicion("d5")
                )
                partida = Partida(estado_inicial=raiz)
                self.jugar(partida, CICLO_BLANCAS * 2)
                self.consultar(partida, esperado)
                self.assertEqual(partida.apariciones_posicion_actual, 2 if vecino else 3)

    def test_sesion_local_se_detiene_en_quinta_aparicion(self):
        sesion = nueva_sesion()
        for movimiento in CICLO_BLANCAS * 4:
            self.assertIsNone(enviar(sesion, movimiento))
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        antes = pickle.dumps(sesion.partida)
        self.assertIs(enviar(sesion, "b1c3"), MotivoRechazoMovimiento.PARTIDA_FINALIZADA)
        self.assertEqual(pickle.dumps(sesion.partida), antes)

    def test_analisis_aislado_puede_continuar_tras_resultado(self):
        original = Partida()
        self.jugar(original, CICLO_BLANCAS * 4)
        antes = pickle.dumps(original)
        sesion = SesionAnalisis(original.ultima_jugada.estado_posicion, original.jugador)
        self.assertEqual(sesion.partida.apariciones_posicion_actual, 1)
        for movimiento in CICLO_BLANCAS * 4:
            self.assertIsNone(sesion.solicitar_movimiento(*anuncio(movimiento)))
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertIsNone(sesion.solicitar_movimiento(*anuncio("b1c3")))
        self.assertEqual(sesion.partida.contador_jugadas, 17)
        self.assertEqual(pickle.dumps(original), antes)


if __name__ == "__main__":
    unittest.main()
