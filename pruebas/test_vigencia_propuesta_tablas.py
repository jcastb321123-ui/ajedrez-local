"""Caducidad de ofertas al jugar, promocionar y finalizar la partida."""
import pickle
import unittest
from unittest.mock import patch

from ajedrez.partida import Partida, EstadoPartida, EstadoPosicion, MotivoRechazoMovimiento
from ajedrez.piezas import Color, Rey, Reina, Torre, Alfil, PeonBlanco, PeonNegro
from ajedrez.sesion import PiezaPromocion
from pruebas import test_abandono as apoyo
from pruebas.test_contador_tablas import preparar
from pruebas.test_sesion import enviar, nueva_sesion, posicion
from pruebas.test_tablas import completar_primer_turno


def contrario(color):
    return Color.Negro if color is Color.Blanco else Color.Blanco


def clave(sesion, color):
    return next(clave for clave, jugador in sesion.juego.autenticador.jugadores_por_clave.items()
                if jugador is color)


class PruebasVigenciaPropuesta(unittest.TestCase):
    def test_solo_el_movimiento_del_adversario_retira_la_oferta_en_ambos_turnos(self):
        for turno, movimiento in ((Color.Blanco, 'g1f3'), (Color.Negro, 'g8f6')):
            for proponente in Color:
                with self.subTest(turno=turno, proponente=proponente):
                    sesion = completar_primer_turno(nueva_sesion())
                    if turno is Color.Negro:
                        self.assertIsNone(enviar(sesion, 'b1c3'))
                    sesion.proponer_tablas(proponente)
                    self.assertIsNone(enviar(sesion, movimiento))
                    esperado = proponente if proponente is turno else None
                    self.assertIs(sesion.proponente_tablas, esperado)
                    self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)

    def test_el_proponente_no_retira_su_oferta_al_mover_y_el_rival_puede_aceptar(self):
        sesion = completar_primer_turno(nueva_sesion())
        sesion.proponer_tablas(Color.Blanco)
        self.assertIsNone(enviar(sesion, 'g1f3'))
        self.assertIs(sesion.proponente_tablas, Color.Blanco)
        sesion.responder_propuesta_tablas(Color.Negro, True)
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertIsNone(sesion.proponente_tablas)

    def test_rechazos_de_validacion_y_autorizacion_conservan_toda_la_sesion(self):
        sesion = completar_primer_turno(nueva_sesion())
        sesion.proponer_tablas(Color.Negro)
        casos = ((clave(sesion, Color.Blanco), 'g1g3', MotivoRechazoMovimiento.MOVIMIENTO_INVALIDO),
                 (clave(sesion, Color.Negro), 'g8f6', MotivoRechazoMovimiento.NO_AUTORIZADO),
                 ('clave_desconocida', 'g1f3', MotivoRechazoMovimiento.NO_AUTORIZADO))
        for identidad, movimiento, esperado in casos:
            with self.subTest(movimiento=movimiento, esperado=esperado):
                antes = pickle.dumps(sesion)
                resultado = sesion.juego.solicitar_movimiento(
                    identidad, posicion(movimiento[:2]), posicion(movimiento[2:]))
                self.assertIs(resultado, esperado)
                self.assertEqual(pickle.dumps(sesion), antes)

        sesion.juego._partida = Partida(estado_inicial=preparar(
            {'e1': Rey(Color.Blanco), 'e2': Torre(Color.Blanco),
             'a8': Rey(Color.Negro), 'e8': Torre(Color.Negro)}, 0))
        antes = pickle.dumps(sesion)
        self.assertIs(enviar(sesion, 'e2f2'), MotivoRechazoMovimiento.REY_EN_JAQUE)
        self.assertEqual(pickle.dumps(sesion), antes)

    def test_la_promocion_del_rival_retira_la_oferta_al_aceptar_el_avance(self):
        for turno, origen, destino, peon in (
            (Color.Blanco, 'a7', 'a8', PeonBlanco()),
            (Color.Negro, 'a2', 'a1', PeonNegro()),
        ):
            with self.subTest(turno=turno):
                sesion = nueva_sesion()
                sesion.juego._partida = Partida(estado_inicial=preparar(
                    {'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro), origen: peon}, 0, turno),
                    turno_inicial=turno)
                sesion.proponer_tablas(contrario(turno))
                self.assertIsNone(enviar(sesion, origen + destino))
                self.assertIsNotNone(sesion.jugada_pendiente)
                self.assertEqual(sesion.partida.contador_jugadas, 0)
                self.assertIsNone(sesion.proponente_tablas)
                sesion.elegir_promocion(PiezaPromocion.REINA)
                self.assertEqual(sesion.partida.contador_jugadas, 1)
                self.assertIsNone(sesion.proponente_tablas)

    def test_promocion_del_proponente_conserva_oferta_hasta_que_termine_la_partida(self):
        for turno, piezas, movimiento in (
            (Color.Blanco, {'h6': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                            'f7': PeonBlanco()}, 'f7f8'),
            (Color.Negro, {'h3': Rey(Color.Negro), 'h1': Rey(Color.Blanco),
                           'f2': PeonNegro()}, 'f2f1'),
        ):
            for opcion in PiezaPromocion:
                with self.subTest(turno=turno, opcion=opcion):
                    sesion = nueva_sesion()
                    sesion.juego._partida = Partida(
                        estado_inicial=preparar(piezas, 0, turno), turno_inicial=turno)
                    sesion.proponer_tablas(turno)
                    self.assertIsNone(enviar(sesion, movimiento))
                    self.assertIs(sesion.proponente_tablas, turno)
                    antes = pickle.dumps(sesion)
                    self.assertIs(enviar(sesion, 'h1g1'), MotivoRechazoMovimiento.PROMOCION_PENDIENTE)
                    sesion.juego.aplicar_promocion(clave(sesion, contrario(turno)), opcion)
                    self.assertEqual(pickle.dumps(sesion), antes)
                    sesion.elegir_promocion(opcion)
                    self.assertIsNot(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)
                    self.assertIsNone(sesion.proponente_tablas)

    def test_promocion_del_proponente_que_no_finaliza_conserva_la_oferta(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(estado_inicial=preparar(
            {'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
             'a7': PeonBlanco(), 'c8': Torre(Color.Negro)}, 0))
        sesion.proponer_tablas(Color.Blanco)
        self.assertIsNone(enviar(sesion, 'a7a8'))
        sesion.elegir_promocion(PiezaPromocion.REINA)
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)
        self.assertIs(sesion.proponente_tablas, Color.Blanco)

    def test_mate_ahogado_y_material_insuficiente_retiran_incluso_la_oferta_propia(self):
        casos = (
            ({'f6': Rey(Color.Blanco), 'g6': Reina(Color.Blanco), 'h8': Rey(Color.Negro)},
             'g6g7', EstadoPartida.VICTORIA_BLANCA),
            ({'f6': Rey(Color.Blanco), 'f7': Reina(Color.Blanco), 'h8': Rey(Color.Negro)},
             'f7g6', EstadoPartida.TABLAS),
            ({'a1': Rey(Color.Blanco), 'c1': Alfil(Color.Blanco),
              'h8': Rey(Color.Negro), 'd2': Torre(Color.Negro)}, 'c1d2', EstadoPartida.TABLAS),
        )
        for piezas, movimiento, resultado in casos:
            with self.subTest(movimiento=movimiento):
                sesion = nueva_sesion()
                sesion.juego._partida = Partida(estado_inicial=preparar(piezas, 0))
                sesion.proponer_tablas(Color.Blanco)
                self.assertIsNone(enviar(sesion, movimiento))
                self.assertIs(sesion.partida.estado_partida, resultado)
                self.assertIsNone(sesion.proponente_tablas)

    def test_finalizaciones_automaticas_por_contador_y_repeticion_retiran_la_oferta(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=149))
        sesion.proponer_tablas(Color.Blanco)
        self.assertIsNone(enviar(sesion, 'g1f3'))
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertIsNone(sesion.proponente_tablas)

        sesion = nueva_sesion()
        movimientos = ('g1f3', 'g8f6', 'f3g1', 'f6g8') * 4
        for movimiento in movimientos[:-1]:
            self.assertIsNone(enviar(sesion, movimiento))
        sesion.proponer_tablas(Color.Negro)
        self.assertIsNone(enviar(sesion, movimientos[-1]))
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertIsNone(sesion.proponente_tablas)

    def test_abandono_retira_la_propuesta_independientemente_del_proponente(self):
        for proponente in Color:
            for abandona in Color:
                with self.subTest(proponente=proponente, abandona=abandona):
                    sesion = completar_primer_turno(nueva_sesion())
                    sesion.proponer_tablas(proponente)
                    sesion.solicitar_abandono(abandona)
                    self.assertIsNone(sesion.proponente_tablas)
                    self.assertIsNot(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)

    def test_respuesta_a_oferta_caducada_no_finaliza_y_admite_una_propuesta_nueva(self):
        sesion = completar_primer_turno(nueva_sesion())
        sesion.proponer_tablas(Color.Negro)
        self.assertIsNone(enviar(sesion, 'g1f3'))
        self.assertIsNone(sesion.proponente_tablas)
        antes = pickle.dumps(sesion)
        for color in Color:
            for aceptar in (False, True):
                sesion.responder_propuesta_tablas(color, aceptar)
                self.assertEqual(pickle.dumps(sesion), antes)
        sesion.proponer_tablas(Color.Blanco)
        sesion.responder_propuesta_tablas(Color.Negro, True)
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)


class PruebasInterfazVigenciaPropuesta(unittest.TestCase):
    setUp = apoyo.PruebasBotonesAbandono.setUp
    tearDown = apoyo.PruebasBotonesAbandono.tearDown
    crear = apoyo.PruebasBotonesAbandono.crear
    clic = apoyo.PruebasBotonesAbandono.clic

    def test_seleccion_y_rechazo_conservan_oferta_movimiento_valido_rehabilita_botones(self):
        sesion = completar_primer_turno(nueva_sesion())
        sesion.proponer_tablas(Color.Negro)
        vista = self.crear(sesion)
        with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno') as dialogo:
            self.clic(vista, 'g1')
            self.assertIs(sesion.proponente_tablas, Color.Negro)
            self.clic(vista, 'g3')
            self.assertIs(sesion.proponente_tablas, Color.Negro)
            self.assertEqual(vista.origen_seleccionado, posicion('g1'))
            self.assertTrue(all(b.cget('state') == 'disabled' for b in vista.botones_propuesta_tablas.values()))
            self.clic(vista, 'f3')
            self.assertIsNone(sesion.proponente_tablas)
            self.assertIsNone(vista.origen_seleccionado)
            self.assertTrue(all(b.cget('state') == 'normal' for b in vista.botones_propuesta_tablas.values()))
            vista._consultar_respuesta_tablas()
        dialogo.assert_not_called()

    def test_sesion_de_un_color_actualiza_disponibilidad_tras_movimiento_del_rival(self):
        sesion = completar_primer_turno(apoyo.SesionUnColor(Color.Negro))
        vista = self.crear(sesion)
        with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno') as dialogo:
            vista.botones_propuesta_tablas[Color.Negro].invoke()
        dialogo.assert_not_called()
        self.assertEqual(vista.botones_propuesta_tablas[Color.Negro].cget('state'), 'disabled')
        self.assertIsNone(enviar(sesion, 'g1f3'))
        vista.mostrar_estado(sesion.estado_actual)
        self.assertIsNone(sesion.proponente_tablas)
        self.assertEqual(vista.botones_propuesta_tablas[Color.Negro].cget('state'), 'normal')

    def test_caducidad_durante_promocion_mantiene_botones_bloqueados_hasta_confirmar(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(estado_inicial=preparar(
            {'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
             'a7': PeonBlanco(), 'c8': Torre(Color.Negro)}, 0, Color.Negro),
            turno_inicial=Color.Negro)
        self.assertIsNone(enviar(sesion, 'h8g8'))
        sesion.proponer_tablas(Color.Negro)
        vista = self.crear(sesion)
        self.clic(vista, 'a7')
        self.clic(vista, 'a8')
        self.assertIsNone(sesion.proponente_tablas)
        self.assertIsNotNone(sesion.jugada_pendiente)
        self.assertTrue(all(b.cget('state') == 'disabled' for b in vista.botones_propuesta_tablas.values()))
        selector = next(w for w in vista.casillero.contenedor.winfo_children()
                        if isinstance(w, apoyo.tk.Frame) and w.winfo_manager() == 'place')
        opciones = [w for w in selector.winfo_children() if isinstance(w, apoyo.tk.Button)]
        opciones[3].invoke()
        self.assertIsNone(sesion.jugada_pendiente)
        self.assertIsNone(sesion.proponente_tablas)
        self.assertTrue(all(b.cget('state') == 'normal' for b in vista.botones_propuesta_tablas.values()))


if __name__ == '__main__':
    unittest.main()
