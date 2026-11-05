"""Consulta y reclamación de tablas por 50 movimientos con una jugada anunciada."""
import pickle
import unittest

from ajedrez.partida import EstadoPartida, EstadoPosicion, Partida
from ajedrez.piezas import Caballo, Color, PeonBlanco, Rey, Torre
from ajedrez.sesion import ModalidadAsignacion, SesionAnalisis
from pruebas.test_analisis_partida import mover, posicion
from pruebas.test_contador_tablas import preparar
from pruebas.test_sesion import SesionDePrueba, nueva_sesion
from pruebas.test_abandono import SesionUnColor


class PruebasMovimientoAnunciado(unittest.TestCase):
    def consultar(self, partida, movimiento, esperado):
        anuncio = None if movimiento is None else (
            posicion(movimiento[:2]), posicion(movimiento[2:]))
        antes = pickle.dumps(partida)
        try:
            resultado = partida.tablas_por_cincuenta_movimientos_disponible(
                movimiento_anunciado=anuncio)
        finally:
            self.assertEqual(pickle.dumps(partida), antes)
        self.assertIs(resultado, esperado)

    def test_limites_con_y_sin_anuncio_en_ambos_turnos(self):
        for turno, movimiento in ((Color.Blanco, 'g1f3'), (Color.Negro, 'g8f6')):
            for contador in (0, 98, 99, 100):
                with self.subTest(turno=turno, contador=contador):
                    partida = Partida(estado_inicial=EstadoPosicion(
                        jugadas_sin_captura_ni_peon=contador), turno_inicial=turno)
                    antes = pickle.dumps(partida)
                    self.assertIs(partida.tablas_por_cincuenta_movimientos_disponible(), contador >= 100)
                    self.assertEqual(pickle.dumps(partida), antes)
                    self.consultar(partida, None, contador >= 100)
                    self.consultar(partida, movimiento, contador + 1 >= 100)

    def test_peon_captura_y_promocion_no_completan_el_limite(self):
        for contador in (99, 100):
            casos = (
                (EstadoPosicion(jugadas_sin_captura_ni_peon=contador), 'e2e4'),
                (preparar({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                           'a2': Torre(Color.Blanco), 'a7': Caballo(Color.Negro)}, contador), 'a2a7'),
                (preparar({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                           'a7': PeonBlanco(), 'b8': Torre(Color.Negro)}, contador), 'a7a8'),
            )
            for raiz, movimiento in casos:
                with self.subTest(contador=contador, movimiento=movimiento):
                    self.consultar(Partida(estado_inicial=raiz), movimiento, False)

    def test_jugadas_inexistentes_o_ilegales_se_rechazan(self):
        for movimiento in ('e4e5', 'g8f6', 'g1g3'):
            with self.subTest(movimiento=movimiento):
                partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=100))
                self.consultar(partida, movimiento, False)
        raiz = preparar({'e1': Rey(Color.Blanco), 'e2': Torre(Color.Blanco),
                         'a8': Rey(Color.Negro), 'e8': Torre(Color.Negro)}, 100)
        self.consultar(Partida(estado_inicial=raiz), 'e2d2', False)

    def test_enroques_incrementan_una_vez_sin_modificar_derechos(self):
        for turno, fila in ((Color.Blanco, '1'), (Color.Negro, '8')):
            for columna, letra, destino in ((7, 'h', 'g'), (0, 'a', 'c')):
                with self.subTest(turno=turno, columna=columna):
                    raiz = preparar({'e1': Rey(Color.Blanco), 'e8': Rey(Color.Negro),
                                     letra + fila: Torre(turno)}, 99, turno, {(turno, columna)})
                    partida = Partida(estado_inicial=raiz, turno_inicial=turno)
                    self.consultar(partida, 'e' + fila + destino + fila, True)

    def test_consultas_repetidas_conservan_historial_y_usan_estado_vigente(self):
        partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=97))
        for movimiento in ('g1f3', 'g8f6'):
            self.assertIsNone(mover(partida, movimiento))
        self.assertEqual(partida.ultima_jugada.estado_posicion.jugadas_sin_captura_ni_peon, 99)
        for _ in range(2):
            self.consultar(partida, 'b1c3', True)
            self.consultar(partida, 'e2e4', False)
            self.consultar(partida, None, False)

    def test_partida_terminada_y_promocion_pendiente_impiden_consultar_como_disponible(self):
        partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=99))
        partida.abandonar(Color.Negro)
        self.consultar(partida, 'g1f3', False)
        raiz = preparar({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                         'a7': PeonBlanco(), 'b8': Torre(Color.Negro)}, 99)
        partida = Partida(estado_inicial=raiz)
        mover(partida, 'a7a8')
        self.assertTrue(partida.promocion_pendiente)
        self.consultar(partida, 'h1g1', False)


class PruebasReclamacionMovimientoAnunciado(unittest.TestCase):
    def reclamar(self, partida, movimiento, esperado):
        anuncio = (posicion(movimiento[:2]), posicion(movimiento[2:]))
        antes = pickle.dumps(partida)
        datos = {clave: valor for clave, valor in vars(partida).items()
                 if clave != '_estado_partida'}
        contenido = pickle.dumps(datos)

        resultado = partida.reclamar_tablas_por_cincuenta_movimientos(
            movimiento_anunciado=anuncio)

        self.assertIs(resultado, esperado)
        if esperado:
            self.assertIs(partida.estado_partida, EstadoPartida.TABLAS)
            despues = {clave: valor for clave, valor in vars(partida).items()
                       if clave != '_estado_partida'}
            self.assertEqual(pickle.dumps(despues), contenido)
            for clave, valor in datos.items():
                self.assertIs(despues[clave], valor)
        else:
            self.assertEqual(pickle.dumps(partida), antes)

    def test_limite_con_anuncio_en_ambos_turnos(self):
        for turno, movimiento in ((Color.Blanco, 'g1f3'), (Color.Negro, 'g8f6')):
            for contador in (98, 99):
                with self.subTest(turno=turno, contador=contador):
                    partida = Partida(
                        estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=contador),
                        turno_inicial=turno)
                    self.reclamar(partida, movimiento, contador == 99)

    def test_anuncios_ilegales_o_que_reinician_el_contador_no_declaran_tablas(self):
        for movimiento in ('e2e4', 'e4e5', 'g8f6', 'g1g3'):
            with self.subTest(movimiento=movimiento):
                partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=99))
                self.reclamar(partida, movimiento, False)
        raiz = preparar({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                         'a2': Torre(Color.Blanco), 'a7': Caballo(Color.Negro)}, 99)
        self.reclamar(Partida(estado_inicial=raiz), 'a2a7', False)

    def test_reclamacion_con_historial_no_ejecuta_el_movimiento_ni_lo_registra(self):
        partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=97))
        for movimiento in ('g1f3', 'g8f6'):
            self.assertIsNone(mover(partida, movimiento))
        self.reclamar(partida, 'b1c3', True)
        self.assertEqual(partida.ultima_jugada.estado_posicion.jugadas_sin_captura_ni_peon, 99)
        self.assertIsInstance(partida.tablero.casillas[posicion('b1')], Caballo)
        self.assertIsNone(partida.tablero.casillas[posicion('c3')])
        self.reclamar(partida, 'b1c3', False)

    def test_anunciar_enroque_conserva_posiciones_y_derechos(self):
        for turno, fila in ((Color.Blanco, '1'), (Color.Negro, '8')):
            with self.subTest(turno=turno):
                raiz = preparar({'e1': Rey(Color.Blanco), 'e8': Rey(Color.Negro),
                                 'h' + fila: Torre(turno)}, 99, turno, {(turno, 7)})
                partida = Partida(estado_inicial=raiz, turno_inicial=turno)
                self.reclamar(partida, 'e' + fila + 'g' + fila, True)


class PruebasTransmisionMovimientoAnunciado(unittest.TestCase):
    def preparar_sesion(self, contador, turno=Color.Blanco,
                        modalidad=ModalidadAsignacion.BLANCO_NEGRO):
        sesion = nueva_sesion(modalidad)
        sesion.juego._partida = Partida(
            estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=contador),
            turno_inicial=turno)
        return sesion

    def reclamar(self, sesion, jugador, movimiento, via):
        emisor = next(emisor for emisor in (sesion.emisor_1, sesion.emisor_2)
                      if sesion.autenticador.autenticar(emisor.clave) is jugador)
        anuncio = (posicion(movimiento[:2]), posicion(movimiento[2:]))
        if via == 'sesion':
            return sesion.reclamar_tablas_por_cincuenta_movimientos(
                jugador, movimiento_anunciado=anuncio)
        if via == 'emisor':
            return emisor.reclamar_tablas_por_cincuenta_movimientos(
                movimiento_anunciado=anuncio)
        return sesion.juego.reclamar_tablas_por_cincuenta_movimientos(
            emisor.clave, movimiento_anunciado=anuncio)

    def test_anuncio_aceptado_llega_al_modelo_y_limpia_propuesta_sin_mover(self):
        for via in ('juego', 'emisor', 'sesion'):
            for modalidad in ModalidadAsignacion:
                for turno, movimiento in ((Color.Blanco, 'g1f3'), (Color.Negro, 'g8f6')):
                    with self.subTest(via=via, modalidad=modalidad, turno=turno):
                        sesion = self.preparar_sesion(99, turno, modalidad)
                        sesion.proponer_tablas(turno)
                        partida = sesion.partida
                        datos = {clave: valor for clave, valor in vars(partida).items()
                                 if clave != '_estado_partida'}
                        contenido = pickle.dumps(datos)
                        resultado = self.reclamar(sesion, turno, movimiento, via)
                        self.assertIs(resultado, True)
                        self.assertIs(partida.estado_partida, EstadoPartida.TABLAS)
                        self.assertIsNone(sesion.proponente_tablas)
                        despues = {clave: valor for clave, valor in vars(partida).items()
                                   if clave != '_estado_partida'}
                        self.assertEqual(pickle.dumps(despues), contenido)
                        for clave, valor in datos.items():
                            self.assertIs(despues[clave], valor)

    def test_color_sin_turno_no_puede_reclamar_con_anuncio_valido(self):
        for via in ('juego', 'emisor', 'sesion'):
            for turno, movimiento in ((Color.Blanco, 'g1f3'), (Color.Negro, 'g8f6')):
                with self.subTest(via=via, turno=turno):
                    sesion = self.preparar_sesion(99, turno)
                    contrario = Color.Negro if turno is Color.Blanco else Color.Blanco
                    sesion.proponer_tablas(contrario)
                    antes = pickle.dumps(sesion)
                    self.assertIs(self.reclamar(sesion, contrario, movimiento, via), False)
                    self.assertEqual(pickle.dumps(sesion), antes)

    def test_rechazos_llegan_al_emisor_y_conservan_sesion_y_propuesta(self):
        for via in ('juego', 'emisor', 'sesion'):
            for contador, movimiento in ((98, 'g1f3'), (99, 'e2e4'), (99, 'g1g3')):
                with self.subTest(via=via, contador=contador, movimiento=movimiento):
                    sesion = self.preparar_sesion(contador)
                    sesion.proponer_tablas(Color.Blanco)
                    antes = pickle.dumps(sesion)
                    self.assertIs(self.reclamar(sesion, Color.Blanco, movimiento, via), False)
                    self.assertEqual(pickle.dumps(sesion), antes)


class PruebasConsultaAnunciadaSesion(unittest.TestCase):
    def test_consulta_local_con_y_sin_anuncio_no_modifica_la_sesion(self):
        for turno, movimiento in ((Color.Blanco, 'g1f3'), (Color.Negro, 'g8f6')):
            for contador in (98, 99, 100):
                with self.subTest(turno=turno, contador=contador):
                    sesion = nueva_sesion()
                    sesion.juego._partida = Partida(
                        estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=contador),
                        turno_inicial=turno)
                    antes = pickle.dumps(sesion)
                    self.assertIs(sesion.tablas_por_cincuenta_movimientos_disponible(),
                                  contador >= 100)
                    anuncio = (posicion(movimiento[:2]), posicion(movimiento[2:]))
                    self.assertIs(sesion.tablas_por_cincuenta_movimientos_disponible(
                        movimiento_anunciado=anuncio), contador >= 99)
                    self.assertEqual(pickle.dumps(sesion), antes)

    def test_consulta_heredada_acepta_el_mismo_argumento_por_nombre(self):
        class SesionConReclamaciones(SesionDePrueba):
            @property
            def admite_reclamaciones_tablas(self):
                return True

        partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=99))
        sesion = SesionConReclamaciones(partida)
        antes = pickle.dumps(partida)
        self.assertIs(sesion.tablas_por_cincuenta_movimientos_disponible(
            movimiento_anunciado=(posicion('g1'), posicion('f3'))), True)
        self.assertEqual(pickle.dumps(partida), antes)

    def test_analisis_y_color_sin_turno_no_ofrecen_reclamacion_anunciada(self):
        raiz = EstadoPosicion(jugadas_sin_captura_ni_peon=99)
        local = SesionUnColor(Color.Negro)
        local.juego._partida = Partida(estado_inicial=raiz)
        analisis = SesionAnalisis(raiz, Color.Blanco)
        for sesion in (local, analisis):
            with self.subTest(sesion=type(sesion).__name__):
                antes = pickle.dumps(sesion)
                self.assertIs(sesion.tablas_por_cincuenta_movimientos_disponible(
                    movimiento_anunciado=(posicion('g1'), posicion('f3'))), False)
                self.assertEqual(pickle.dumps(sesion), antes)


if __name__ == '__main__':
    unittest.main(verbosity=2)
