"""Reclamación de tablas con el contador ya alcanzado en la posición vigente."""
import pickle
import unittest

from ajedrez.partida import EstadoPartida, EstadoPosicion, Jugada, MotivoRechazoMovimiento, Partida
from ajedrez.piezas import Color, PeonBlanco, Rey, Torre
from ajedrez.sesion import ModalidadAsignacion, SesionAnalisis
from pruebas.test_analisis_partida import mover, posicion
from pruebas.test_contador_tablas import preparar
from pruebas.test_sesion import nueva_sesion


class PruebasReclamacionCincuentaMovimientos(unittest.TestCase):
    def comprobar_reclamacion(self, partida, aceptada):
        antes = pickle.dumps(partida)
        datos = {clave: valor for clave, valor in vars(partida).items()
                 if clave != '_estado_partida'}
        contenido = pickle.dumps(datos)
        resultado = partida.reclamar_tablas_por_cincuenta_movimientos()
        self.assertIs(resultado, aceptada)
        if aceptada:
            self.assertIs(partida.estado_partida, EstadoPartida.TABLAS)
            despues = {clave: valor for clave, valor in vars(partida).items()
                       if clave != '_estado_partida'}
            self.assertEqual(pickle.dumps(despues), contenido)
            for clave, valor in datos.items():
                self.assertIs(despues[clave], valor)
        else:
            self.assertEqual(pickle.dumps(partida), antes)

    def test_limite_en_posiciones_iniciales_de_ambos_turnos(self):
        for turno in Color:
            for contador in (0, 99, 100, 101, 149):
                with self.subTest(turno=turno, contador=contador):
                    partida = Partida(
                        estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=contador),
                        turno_inicial=turno)
                    self.comprobar_reclamacion(partida, contador >= 100)

    def test_reclamacion_al_alcanzar_cien_consulta_la_ultima_jugada(self):
        partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=98))
        self.assertIsNone(mover(partida, 'g1f3'))
        self.comprobar_reclamacion(partida, False)
        self.assertIsNone(mover(partida, 'g8f6'))
        self.assertEqual(partida.ultima_jugada.estado_posicion.jugadas_sin_captura_ni_peon, 100)
        self.comprobar_reclamacion(partida, True)

    def test_historial_se_conserva_y_no_se_puede_reclamar_dos_veces(self):
        partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=99))
        for movimiento in ('g1f3', 'g8f6'):
            self.assertIsNone(mover(partida, movimiento))
        self.comprobar_reclamacion(partida, True)
        self.comprobar_reclamacion(partida, False)

    def test_movimiento_de_peon_invalida_el_contador_anterior(self):
        partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=101))
        self.assertIsNone(mover(partida, 'e2e4'))
        self.assertEqual(partida.ultima_jugada.estado_posicion.jugadas_sin_captura_ni_peon, 0)
        self.comprobar_reclamacion(partida, False)

    def test_promocion_pendiente_impide_reclamar_con_el_contador_anterior(self):
        raiz = preparar({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                         'a7': PeonBlanco(), 'b8': Torre(Color.Negro)}, 101)
        partida = Partida(estado_inicial=raiz)
        pendiente = mover(partida, 'a7a8')
        self.assertIsInstance(pendiente, Jugada)
        self.assertTrue(partida.promocion_pendiente)
        self.assertEqual(partida.estado_inicial.jugadas_sin_captura_ni_peon, 101)
        self.comprobar_reclamacion(partida, False)

    def test_resultados_finales_no_se_sobrescriben(self):
        for color in Color:
            with self.subTest(abandona=color):
                partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=101))
                partida.abandonar(color)
                self.comprobar_reclamacion(partida, False)
        partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=149))
        self.assertIsNone(mover(partida, 'g1f3'))
        self.assertIs(partida.estado_partida, EstadoPartida.TABLAS)
        self.comprobar_reclamacion(partida, False)


class PruebasReclamacionCincuentaInterfazJuego(unittest.TestCase):
    def preparar_juego(self, contador=100, turno=Color.Blanco):
        sesion = nueva_sesion()
        juego = sesion.juego
        juego._partida = Partida(
            estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=contador),
            turno_inicial=turno)
        claves = {color: clave for clave, color in juego.autenticador.jugadores_por_clave.items()}
        return juego, claves

    def test_solo_quien_tiene_turno_reclama_y_la_aceptacion_limpia_la_propuesta(self):
        for turno in Color:
            with self.subTest(turno=turno):
                juego, claves = self.preparar_juego(turno=turno)
                contrario = Color.Negro if turno is Color.Blanco else Color.Blanco
                juego.proponer_tablas(claves[contrario])
                antes = pickle.dumps(juego)
                self.assertIs(juego.reclamar_tablas_por_cincuenta_movimientos(claves[contrario]), False)
                self.assertEqual(pickle.dumps(juego), antes)
                self.assertIs(juego.reclamar_tablas_por_cincuenta_movimientos(claves[turno]), True)
                self.assertIs(juego.partida.estado_partida, EstadoPartida.TABLAS)
                self.assertIsNone(juego.proponente_tablas)
                final = pickle.dumps(juego)
                origen, destino = ('g1', 'f3') if turno is Color.Blanco else ('g8', 'f6')
                self.assertIs(
                    juego.solicitar_movimiento(claves[turno], posicion(origen), posicion(destino)),
                    MotivoRechazoMovimiento.PARTIDA_FINALIZADA)
                self.assertEqual(pickle.dumps(juego), final)

    def test_contador_insuficiente_conserva_la_propuesta(self):
        for turno in Color:
            with self.subTest(turno=turno):
                juego, claves = self.preparar_juego(contador=99, turno=turno)
                juego.proponer_tablas(claves[turno])
                antes = pickle.dumps(juego)
                self.assertIs(juego.reclamar_tablas_por_cincuenta_movimientos(claves[turno]), False)
                self.assertEqual(pickle.dumps(juego), antes)

    def test_rechazo_tras_abandono_conserva_resultado_y_no_reabre_propuesta(self):
        for color in Color:
            with self.subTest(abandona=color):
                juego, claves = self.preparar_juego(contador=101)
                juego.proponer_tablas(claves[Color.Negro])
                juego.solicitar_abandono(claves[color])
                self.assertIsNone(juego.proponente_tablas)
                antes = pickle.dumps(juego)
                self.assertIs(juego.reclamar_tablas_por_cincuenta_movimientos(claves[Color.Blanco]), False)
                self.assertEqual(pickle.dumps(juego), antes)

    def test_reclamacion_durante_promocion_conserva_eleccion_y_oferta_ya_retirada(self):
        juego, claves = self.preparar_juego()
        raiz = preparar({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                         'a7': PeonBlanco(), 'b8': Torre(Color.Negro)}, 101)
        juego._partida = Partida(estado_inicial=raiz)
        juego.proponer_tablas(claves[Color.Negro])
        self.assertIsNone(juego.solicitar_movimiento(
            claves[Color.Blanco], posicion('a7'), posicion('a8')))
        self.assertIsNotNone(juego.jugada_pendiente)
        self.assertIsNone(juego.proponente_tablas)
        antes = pickle.dumps(juego)
        self.assertIs(juego.reclamar_tablas_por_cincuenta_movimientos(claves[Color.Blanco]), False)
        self.assertEqual(pickle.dumps(juego), antes)


class PruebasReclamacionCincuentaSesion(unittest.TestCase):
    def preparar_sesion(self, contador=100, turno=Color.Blanco,
                       modalidad=ModalidadAsignacion.BLANCO_NEGRO):
        sesion = nueva_sesion(modalidad)
        sesion.juego._partida = Partida(
            estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=contador),
            turno_inicial=turno)
        return sesion

    def test_emisor_devuelve_tanto_aceptacion_como_rechazo(self):
        for contador, esperado in ((99, False), (100, True)):
            with self.subTest(contador=contador):
                sesion = self.preparar_sesion(contador)
                emisor = next(emisor for emisor in (sesion.emisor_1, sesion.emisor_2)
                              if sesion.autenticador.autenticar(emisor.clave) is Color.Blanco)
                resultado = emisor.reclamar_tablas_por_cincuenta_movimientos()
                estado_esperado = EstadoPartida.TABLAS if esperado else EstadoPartida.EN_CURSO
                self.assertIs(sesion.partida.estado_partida, estado_esperado)
                self.assertIs(resultado, esperado)

    def test_sesion_respeta_el_color_solicitante_y_devuelve_el_resultado(self):
        for modalidad in ModalidadAsignacion:
            for turno in Color:
                with self.subTest(modalidad=modalidad, turno=turno):
                    sesion = self.preparar_sesion(turno=turno, modalidad=modalidad)
                    self.assertIs(sesion.admite_reclamaciones_tablas, True)
                    contrario = Color.Negro if turno is Color.Blanco else Color.Blanco
                    sesion.proponer_tablas(contrario)
                    antes = pickle.dumps(sesion)
                    self.assertIs(sesion.reclamar_tablas_por_cincuenta_movimientos(contrario), False)
                    self.assertEqual(pickle.dumps(sesion), antes)
                    self.assertIs(sesion.reclamar_tablas_por_cincuenta_movimientos(turno), True)
                    self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
                    self.assertIsNone(sesion.proponente_tablas)

    def test_analisis_hereda_la_accion_no_admitida_y_permite_movimientos(self):
        sesion = SesionAnalisis(EstadoPosicion(jugadas_sin_captura_ni_peon=100), Color.Blanco)
        self.assertIs(sesion.admite_reclamaciones_tablas, False)
        antes = pickle.dumps(sesion)
        with self.assertRaises(NotImplementedError):
            sesion.reclamar_tablas_por_cincuenta_movimientos(Color.Blanco)
        self.assertEqual(pickle.dumps(sesion), antes)
        self.assertIsNone(sesion.solicitar_movimiento(posicion('g1'), posicion('f3')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
