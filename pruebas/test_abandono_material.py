"""Abandono con imposibilidad de mate por material, por color y desde la GUI."""
import pickle
import unittest
from unittest.mock import patch

from ajedrez.partida import EstadoPartida, MotivoRechazoMovimiento, Partida
from ajedrez.piezas import Alfil, Caballo, Color, PeonBlanco, PeonNegro, Reina, Rey, Torre
from pruebas import test_abandono as apoyo
from pruebas.test_analisis_partida import estado_minimo, mover, posicion
from pruebas.test_contador_tablas import preparar
from pruebas.test_sesion import enviar, nueva_sesion


def contrario(color):
    return Color.Negro if color is Color.Blanco else Color.Blanco


class PruebasMaterialPorColor(unittest.TestCase):
    def comprobar(self, color, propias, rivales, esperado):
        estado = estado_minimo({
            'a1': Rey(color), 'h8': Rey(contrario(color)), **propias, **rivales})
        antes = pickle.dumps(estado)
        self.assertIs(estado.tablero.tiene_material_insuficiente_para_mate(color), esperado)
        self.assertEqual(pickle.dumps(estado), antes)
        return estado.tablero

    def test_rey_solo_carece_de_material_aunque_el_adversario_pueda_ganar(self):
        for color in Color:
            for clase in (Torre, Reina):
                with self.subTest(color=color, pieza=clase.__name__):
                    tablero = self.comprobar(color, {}, {'d6': clase(contrario(color))}, True)
                    self.assertFalse(tablero.tiene_material_insuficiente_para_mate(contrario(color)))
                    self.assertFalse(tablero.es_posicion_muerta_por_material())

    def test_caballo_solo_contra_rey_o_damas_no_puede_dar_mate(self):
        for color in Color:
            for rivales in ({}, {'d6': Reina(contrario(color))},
                            {'d6': Reina(contrario(color)), 'e7': Reina(contrario(color))}):
                with self.subTest(color=color, rivales=tuple(rivales)):
                    self.comprobar(color, {'b1': Caballo(color)}, rivales, True)

    def test_un_caballo_puede_aprovechar_otras_piezas_rivales(self):
        for color in Color:
            rival = contrario(color)
            peon = PeonNegro() if rival is Color.Negro else PeonBlanco()
            for pieza in (Alfil(rival), Caballo(rival), Torre(rival), peon):
                with self.subTest(color=color, pieza=type(pieza).__name__):
                    self.comprobar(color, {'b1': Caballo(color)}, {'d6': pieza}, False)

    def test_alfiles_mismo_color_de_casilla_contra_torres_y_damas(self):
        for color in Color:
            for propias in ({'c1': Alfil(color)},
                            {'c1': Alfil(color), 'e3': Alfil(color)}):
                with self.subTest(color=color, propias=tuple(propias)):
                    self.comprobar(color, propias,
                                   {'d6': Torre(contrario(color)), 'e7': Reina(contrario(color)),
                                    'a3': Alfil(contrario(color))}, True)

    def test_alfiles_otros_colores_peones_y_caballos_pueden_permitir_mate(self):
        for color in Color:
            rival = contrario(color)
            peon = PeonNegro() if rival is Color.Negro else PeonBlanco()
            for pieza in (Alfil(rival), Caballo(rival), peon):
                with self.subTest(color=color, pieza=type(pieza).__name__):
                    self.comprobar(color, {'c1': Alfil(color)}, {'a2': pieza}, False)

    def test_material_propio_con_mate_posible_no_produce_tablas(self):
        for color in Color:
            peon = PeonBlanco() if color is Color.Blanco else PeonNegro()
            casos = (
                {'c2': peon}, {'c1': Torre(color)}, {'c1': Reina(color)},
                {'b1': Caballo(color), 'g1': Caballo(color)},
                {'c1': Alfil(color), 'f1': Alfil(color)},
                {'c1': Alfil(color), 'b1': Caballo(color)},
            )
            for propias in casos:
                with self.subTest(color=color, propias=tuple(propias)):
                    self.comprobar(color, propias, {}, False)


class PruebasResultadoAbandonoMaterial(unittest.TestCase):
    def comprobar_abandono(self, partida, color, esperado):
        referencias = apoyo.datos_de_juego(partida)
        antes = pickle.dumps(referencias)
        self.assertIsNone(partida.abandonar(color))
        self.assertIs(partida.estado_partida, esperado)
        self.assertEqual(pickle.dumps(apoyo.datos_de_juego(partida)), antes)
        for anterior, actual in zip(referencias[:4], apoyo.datos_de_juego(partida)[:4]):
            self.assertIs(actual, anterior)

    def test_el_resultado_depende_del_adversario_y_no_del_turno(self):
        for fuerte in Color:
            for turno in Color:
                for abandona in Color:
                    with self.subTest(fuerte=fuerte, turno=turno, abandona=abandona):
                        estado = preparar({'a1': Rey(fuerte), 'h8': Rey(contrario(fuerte)),
                                           'c1': Torre(fuerte)}, 0, turno)
                        partida = Partida(estado_inicial=estado, turno_inicial=turno)
                        self.assertIs(partida.estado_partida, EstadoPartida.EN_CURSO)
                        victoria = (EstadoPartida.VICTORIA_BLANCA if fuerte is Color.Blanco
                                    else EstadoPartida.VICTORIA_NEGRA)
                        esperado = EstadoPartida.TABLAS if abandona is fuerte else victoria
                        self.comprobar_abandono(partida, abandona, esperado)

    def test_alfil_frente_a_torre_y_caballo_frente_a_dama(self):
        for debil in Color:
            for menor, mayor in ((Alfil, Torre), (Alfil, Reina), (Caballo, Reina)):
                with self.subTest(debil=debil, menor=menor.__name__, mayor=mayor.__name__):
                    estado = preparar({'a1': Rey(debil), 'h8': Rey(contrario(debil)),
                                       'c1': menor(debil), 'd6': mayor(contrario(debil))}, 0, debil)
                    partida = Partida(estado_inicial=estado, turno_inicial=debil)
                    self.assertIs(partida.estado_partida, EstadoPartida.EN_CURSO)
                    self.comprobar_abandono(partida, contrario(debil), EstadoPartida.TABLAS)

    def test_se_evalua_el_tablero_vigente_tras_una_captura(self):
        estado = preparar({'b2': Rey(Color.Blanco), 'c1': Torre(Color.Blanco),
                           'h8': Rey(Color.Negro), 'b3': Torre(Color.Negro)}, 0)
        partida = Partida(estado_inicial=estado)
        self.assertIsNone(mover(partida, 'b2b3'))
        self.assertFalse(estado.tablero.tiene_material_insuficiente_para_mate(Color.Negro))
        self.assertIs(partida.estado_partida, EstadoPartida.EN_CURSO)
        self.comprobar_abandono(partida, Color.Blanco, EstadoPartida.TABLAS)

    def test_mates_reales_evitan_confundir_no_forzar_mate_con_mate_imposible(self):
        casos = (
            ({'c7': Rey(Color.Blanco), 'a8': Rey(Color.Negro),
              'c6': Caballo(Color.Blanco), 'c4': Caballo(Color.Blanco)}, 'c4b6'),
            ({'c8': Rey(Color.Blanco), 'a8': Rey(Color.Negro),
              'c4': Caballo(Color.Blanco), 'a7': Torre(Color.Negro)}, 'c4b6'),
            ({'c7': Rey(Color.Blanco), 'a8': Rey(Color.Negro),
              'c8': Alfil(Color.Blanco), 'a7': Alfil(Color.Negro)}, 'c8b7'),
        )
        for piezas, movimiento in casos:
            with self.subTest(movimiento=movimiento, piezas=tuple(piezas)):
                estado = preparar(piezas, 0)
                partida = Partida(estado_inicial=estado)
                self.comprobar_abandono(partida, Color.Negro, EstadoPartida.VICTORIA_BLANCA)
                continuacion = Partida(estado_inicial=estado)
                self.assertIsNone(mover(continuacion, movimiento))
                self.assertIs(continuacion.estado_partida, EstadoPartida.VICTORIA_BLANCA)

    def test_sesion_transmite_el_resultado_y_rechaza_seguir_la_partida_original(self):
        for fuerte in Color:
            with self.subTest(fuerte=fuerte):
                sesion = nueva_sesion()
                estado = preparar({'a1': Rey(fuerte), 'h8': Rey(contrario(fuerte)),
                                   'c1': Torre(fuerte)}, 0, fuerte)
                sesion.juego._partida = Partida(estado_inicial=estado, turno_inicial=fuerte)
                antes = pickle.dumps(apoyo.datos_de_juego(sesion.partida))
                self.assertIsNone(sesion.solicitar_abandono(fuerte))
                self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
                self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), antes)
                self.assertIs(enviar(sesion, 'c1c2'), MotivoRechazoMovimiento.PARTIDA_FINALIZADA)


class PruebasInterfazAbandonoMaterial(unittest.TestCase):
    setUp = apoyo.PruebasBotonesAbandono.setUp
    tearDown = apoyo.PruebasBotonesAbandono.tearDown
    crear = apoyo.PruebasBotonesAbandono.crear
    clic = apoyo.PruebasBotonesAbandono.clic

    def test_confirmacion_actualiza_tablas_y_cancelacion_conserva_la_seleccion(self):
        for fuerte in Color:
            for unico in (False, True):
                for confirmar in (False, True):
                    with self.subTest(fuerte=fuerte, unico=unico, confirmar=confirmar):
                        sesion = apoyo.SesionUnColor(fuerte) if unico else nueva_sesion()
                        estado = preparar({'a1': Rey(fuerte), 'h8': Rey(contrario(fuerte)),
                                           'c1': Torre(fuerte)}, 0, fuerte)
                        sesion.juego._partida = Partida(estado_inicial=estado, turno_inicial=fuerte)
                        vista = self.crear(sesion)
                        self.clic(vista, 'c1')
                        antes = pickle.dumps(sesion.partida)
                        mostrado = vista.estado_mostrado
                        with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno',
                                          return_value=confirmar) as dialogo:
                            vista.botones_abandono[fuerte].invoke()
                        dialogo.assert_called_once()
                        self.assertIs(dialogo.call_args.kwargs['parent'], vista.contenedor)
                        self.assertIs(vista.estado_mostrado, mostrado)
                        if confirmar:
                            self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
                            self.assertEqual(vista.indicador_estado_partida.cget('text'), 'Tablas')
                            self.assertIsNone(vista.origen_seleccionado)
                            self.assertTrue(all(b.cget('state') == 'disabled'
                                                for b in vista.botones_abandono.values()))
                        else:
                            self.assertEqual(pickle.dumps(sesion.partida), antes)
                            self.assertEqual(vista.origen_seleccionado, posicion('c1'))
                        vista.contenedor.destroy()

    def test_tras_las_tablas_por_abandono_se_puede_analizar_sin_alterar_el_original(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(estado_inicial=preparar(
            {'a1': Rey(Color.Blanco), 'c1': Torre(Color.Blanco), 'h8': Rey(Color.Negro)}, 0))
        vista = self.crear(sesion)
        with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno', return_value=True):
            vista.botones_abandono[Color.Blanco].invoke()
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        original = pickle.dumps(sesion.partida)
        self.clic(vista, 'c1')
        self.clic(vista, 'c2')
        self.assertIsNot(vista.sesion_movimientos.partida, sesion.partida)
        hipotetico = vista.estado_mostrado
        self.assertIsNot(hipotetico, sesion.estado_actual)
        vista.retroceder_movimiento()
        self.assertIs(vista.estado_mostrado, sesion.estado_actual)
        vista.avanzar_movimiento()
        self.assertIs(vista.estado_mostrado, hipotetico)
        self.assertEqual(pickle.dumps(sesion.partida), original)


if __name__ == '__main__':
    unittest.main()
