"""Bloqueos permanentes y posiciones parecidas que sí pueden abrirse."""
from copy import copy
import pickle
import unittest

from ajedrez.editor_posicion import EditorPosicion
from ajedrez.partida import EstadoPartida, EstadoPosicion, Jugada, MotivoRechazoMovimiento, Partida
from ajedrez.piezas import Alfil, Caballo, Color, PeonBlanco, PeonNegro, Reina, Rey
from ajedrez.sesion import SesionAnalisis
from pruebas import test_abandono as apoyo_interfaz
from pruebas import test_panel_analisis as apoyo_panel
from pruebas.test_analisis_partida import mover, posicion
from pruebas.test_contador_tablas import preparar
from pruebas.test_sesion import enviar, nueva_sesion


def barrera(fila_alta=4, fase=0):
    piezas = {'a1': Rey(Color.Blanco), 'h8': Rey(Color.Negro)}
    for columna, letra in enumerate('abcdefgh'):
        fila = fila_alta if columna % 2 == fase else fila_alta - 1
        piezas[f'{letra}{fila}'] = PeonBlanco()
        piezas[f'{letra}{fila + 1}'] = PeonNegro()
    return piezas


def antes_del_cierre():
    piezas = barrera()
    piezas['h5'] = piezas.pop('h4')
    return preparar(piezas, 0, Color.Negro)


class PruebasBloqueoPermanente(unittest.TestCase):
    def comprobar(self, estado, esperado):
        tablero = estado.tablero
        antes = pickle.dumps(estado)
        diccionario = tablero.casillas
        objetos = tuple(tablero.casillas.items())
        self.assertIs(tablero.es_posicion_muerta_por_bloqueo(), esperado)
        self.assertIs(tablero.casillas, diccionario)
        for casilla, pieza in objetos:
            self.assertIs(tablero.casillas[casilla], pieza)
        self.assertEqual(pickle.dumps(estado), antes)

    def test_barreras_a_distintas_alturas_y_fases_con_reyes_moviles(self):
        for fila in range(3, 7):
            for fase in (0, 1):
                with self.subTest(fila=fila, fase=fase):
                    estado = preparar(barrera(fila, fase), 0)
                    self.assertFalse(estado.tablero.es_posicion_muerta_por_material())
                    self.comprobar(estado, True)
                    for casilla in ('a1', 'h8'):
                        rey = estado.tablero.pieza_en(posicion(casilla))
                        self.assertTrue(estado.tablero.calcular_rango_candidato(rey, posicion(casilla)))

    def test_hueco_defendido_sigue_cerrado_y_abertura_accesible_no(self):
        for huecos, esperado in ((('a4', 'a5'), True),
                                 (('g4', 'g5', 'h3', 'h4'), False)):
            with self.subTest(huecos=huecos):
                piezas = barrera()
                for casilla in huecos:
                    del piezas[casilla]
                self.comprobar(preparar(piezas, 0), esperado)

    def test_alfil_encerrado_y_caballo_que_puede_salir(self):
        piezas = barrera(3)
        piezas['c1'] = Alfil(Color.Blanco)
        self.comprobar(preparar(piezas, 0), True)
        piezas['c1'] = Caballo(Color.Blanco)
        self.comprobar(preparar(piezas, 0), False)

    def test_captura_de_peon_impide_declarar_bloqueo(self):
        piezas = {'a1': Rey(Color.Blanco), 'h8': Rey(Color.Negro)}
        for letra in 'abcdefgh':
            piezas[f'{letra}4'] = PeonBlanco()
            piezas[f'{letra}5'] = PeonNegro()
        estado = preparar(piezas, 0)
        self.comprobar(estado, False)
        partida = Partida(estado_inicial=estado)
        self.assertIsNone(mover(partida, 'a4b5'))
        self.assertEqual(sum(p is not None for p in partida.tablero.casillas.values()), 17)

    def test_avance_disponible_y_rey_que_solo_obstruye_temporalmente(self):
        self.comprobar(antes_del_cierre(), False)
        estado = preparar({'a1': Rey(Color.Blanco), 'd5': Rey(Color.Negro),
                           'd4': PeonBlanco()}, 0, Color.Negro)
        self.comprobar(estado, False)
        partida = Partida(estado_inicial=estado, turno_inicial=Color.Negro)
        self.assertIsNone(mover(partida, 'd5e6'))
        self.assertIsNone(mover(partida, 'd4d5'))

    def test_captura_al_paso_abre_barrera_que_sin_ese_derecho_es_permanente(self):
        sin_al_paso = preparar(barrera(5, 1), 0)
        self.comprobar(sin_al_paso, True)
        estado = EditorPosicion(sin_al_paso, Color.Blanco).construir_estado(
            turno=Color.Blanco, enroques=set(), peon_al_paso=posicion('a5'))
        self.comprobar(estado, False)
        partida = Partida(estado_inicial=estado)
        self.assertIsNone(mover(partida, 'b5a6'))
        self.assertIsNone(partida.tablero.pieza_en(posicion('a5')))
        self.assertIs(partida.estado_partida, EstadoPartida.EN_CURSO)

    def test_marca_al_paso_sin_capturador_no_descarta_el_bloqueo(self):
        estado = EditorPosicion(preparar(barrera(), 0), Color.Blanco).construir_estado(
            turno=Color.Blanco, enroques=set(), peon_al_paso=posicion('a5'))
        self.comprobar(estado, True)

    def test_un_rey_lejano_puede_llegar_a_capturar_y_permitir_promocion(self):
        estado = preparar({'a1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                           'd4': PeonBlanco(), 'd5': PeonNegro()}, 0)
        self.comprobar(estado, False)
        partida = Partida(estado_inicial=estado)
        for movimiento in ('a1b2', 'h8h7', 'b2b3', 'h7h8', 'b3b4', 'h8h7',
                            'b4c5', 'h7h8', 'c5d5', 'h8h7', 'd5c5', 'h7h8',
                            'd4d5', 'h8h7', 'd5d6', 'h7h8', 'd6d7', 'h8h7'):
            self.assertIsNone(mover(partida, movimiento), movimiento)
        promocion = mover(partida, 'd7d8')
        self.assertIsInstance(promocion, Jugada)
        partida.promocionar(posicion('d8'), Reina(Color.Blanco), promocion)
        self.assertIsInstance(partida.tablero.pieza_en(posicion('d8')), Reina)

    def test_no_confunde_la_oposicion_del_rey_rival_con_una_barrera(self):
        estado = preparar({'a1': Rey(Color.Blanco), 'e6': Rey(Color.Negro),
                           'd4': PeonBlanco(), 'd5': PeonNegro()}, 0)
        self.comprobar(estado, False)

    def test_no_declara_bloqueo_si_ya_hay_jaque(self):
        piezas = barrera()
        piezas['a3'] = piezas.pop('a1')
        estado = preparar(piezas, 0)
        self.assertTrue(estado.tablero.el_rey_queda_en_jaque(Color.Blanco))
        self.comprobar(estado, False)

    def test_material_y_bloqueo_conservan_sus_significados(self):
        estado = preparar({'a1': Rey(Color.Blanco), 'h8': Rey(Color.Negro)}, 0)
        self.comprobar(estado, False)
        self.assertTrue(estado.tablero.es_posicion_muerta_por_material())
        self.assertTrue(estado.tablero.es_posicion_muerta())
        self.assertFalse(EstadoPosicion().tablero.es_posicion_muerta())

    def test_recorrido_exhaustivo_de_movimientos_legales_en_una_barrera(self):
        # Comprueba todos los estados alcanzables de este ejemplo usando Jugada,
        # sin recurrir al detector: sólo cambian las casillas de los dos reyes.
        inicial = preparar(barrera(3), 0)
        reyes = {Color.Blanco: inicial.tablero.pieza_en(posicion('a1')),
                 Color.Negro: inicial.tablero.pieza_en(posicion('h8'))}
        fijo = copy(inicial.tablero)
        fijo._casillas = inicial.tablero.casillas.copy()
        fijo.colocar(None, posicion('a1'))
        fijo.colocar(None, posicion('h8'))
        comienzo = (posicion('a1'), posicion('h8'), Color.Blanco)
        pendientes, visitados = [comienzo], {comienzo}
        while pendientes:
            blanco, negro, turno = pendientes.pop()
            tablero = copy(fijo)
            tablero._casillas = fijo.casillas.copy()
            tablero.colocar(reyes[Color.Blanco], blanco)
            tablero.colocar(reyes[Color.Negro], negro)
            estado = EstadoPosicion(tablero=tablero)
            self.assertFalse(tablero.el_rey_queda_en_jaque(Color.Blanco))
            self.assertFalse(tablero.el_rey_queda_en_jaque(Color.Negro))
            for origen, pieza in tablero.casillas.items():
                if pieza is None or pieza.color is not turno:
                    continue
                for destino in tablero.calcular_rango_candidato(pieza, origen):
                    jugada = Jugada(1, origen, destino, None, estado_inicial=estado)
                    if not jugada.estado_posicion.movimiento_valido:
                        continue
                    self.assertIsInstance(pieza, Rey)
                    self.assertIsNone(tablero.pieza_en(destino))
                    siguiente = ((destino, negro, Color.Negro) if turno is Color.Blanco
                                 else (blanco, destino, Color.Blanco))
                    if siguiente not in visitados:
                        visitados.add(siguiente)
                        pendientes.append(siguiente)
        self.assertGreater(len(visitados), 100)


class PruebasResultadoPorBloqueo(unittest.TestCase):
    def test_posicion_inicial_finalizada_en_ambos_turnos_sin_mutar_raiz(self):
        for turno in Color:
            with self.subTest(turno=turno):
                estado = preparar(barrera(), 0, turno)
                antes = pickle.dumps(estado)
                partida = Partida(estado_inicial=estado, turno_inicial=turno)
                self.assertIs(partida.estado_partida, EstadoPartida.TABLAS)
                self.assertIsNone(partida.ultima_jugada)
                self.assertEqual(partida.contador_jugadas, 0)
                self.assertEqual(pickle.dumps(estado), antes)
                resultado = pickle.dumps(partida)
                partida.actualizar_estado()
                self.assertEqual(pickle.dumps(partida), resultado)

    def test_jugada_que_cierra_barrera_finaliza_sin_esperar_repeticion_o_contador(self):
        estado = antes_del_cierre()
        antes = pickle.dumps(estado)
        partida = Partida(estado_inicial=estado, turno_inicial=Color.Negro)
        self.assertIs(partida.estado_partida, EstadoPartida.EN_CURSO)
        self.assertIsNone(mover(partida, 'h5h4'))
        self.assertIs(partida.estado_partida, EstadoPartida.TABLAS)
        self.assertEqual(partida.contador_jugadas, 1)
        self.assertEqual(partida.ultima_jugada.estado_posicion.jugadas_sin_captura_ni_peon, 0)
        self.assertEqual(partida.apariciones_posicion_actual, 1)
        self.assertEqual(pickle.dumps(estado), antes)

    def test_abandono_en_el_bloqueo_no_introduce_una_victoria(self):
        for color in Color:
            with self.subTest(color=color):
                partida = Partida(estado_inicial=preparar(barrera(), 0))
                antes = pickle.dumps(partida)
                partida.abandonar(color)
                self.assertIs(partida.estado_partida, EstadoPartida.TABLAS)
                self.assertEqual(pickle.dumps(partida), antes)

    def test_juego_local_se_detiene_y_analisis_puede_seguir_sin_alterarlo(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(estado_inicial=antes_del_cierre(), turno_inicial=Color.Negro)
        self.assertIsNone(enviar(sesion, 'h5h4'))
        original = pickle.dumps(sesion.partida)
        self.assertIs(enviar(sesion, 'a1b1'), MotivoRechazoMovimiento.PARTIDA_FINALIZADA)
        analisis = SesionAnalisis(sesion.estado_actual, Color.Blanco)
        self.assertIsNone(analisis.solicitar_movimiento(posicion('a1'), posicion('b1')))
        self.assertIs(analisis.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertEqual(analisis.partida.contador_jugadas, 1)
        self.assertEqual(pickle.dumps(sesion.partida), original)


class PruebasInterfazBloqueo(unittest.TestCase):
    setUp = apoyo_interfaz.PruebasBotonesAbandono.setUp
    tearDown = apoyo_interfaz.PruebasBotonesAbandono.tearDown
    crear = apoyo_interfaz.PruebasBotonesAbandono.crear
    clic = apoyo_interfaz.PruebasBotonesAbandono.clic

    def test_cierre_actualiza_resultado_controles_y_permite_revision(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(estado_inicial=antes_del_cierre(), turno_inicial=Color.Negro)
        vista = self.crear(sesion)
        self.clic(vista, 'h5')
        self.clic(vista, 'h4')
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertEqual(vista.indicador_estado_partida.cget('text'), 'Tablas')
        self.assertIsNone(vista.origen_seleccionado)
        for boton in (*vista.botones_abandono.values(), *vista.botones_propuesta_tablas.values(),
                       vista.boton_reclamacion_tablas):
            self.assertEqual(boton.cget('state'), 'disabled')
        original = pickle.dumps(sesion.partida)
        self.clic(vista, 'a1')
        self.clic(vista, 'b1')
        self.assertIsNot(vista.estado_mostrado, sesion.estado_actual)
        self.assertEqual(pickle.dumps(sesion.partida), original)


class PruebasEditorBloqueo(unittest.TestCase):
    setUp = apoyo_panel.PruebasPanelAnalisis.setUp
    tearDown = apoyo_panel.PruebasPanelAnalisis.tearDown
    panel = apoyo_panel.PruebasPanelAnalisis.panel

    def test_editor_reconoce_barrera_sin_modificar_partida_principal(self):
        original = pickle.dumps(self.sesion.partida)
        panel = self.panel()
        panel.iniciar_edicion()
        panel.editor.vaciar()
        for casilla, pieza in barrera().items():
            panel.editor.colocar(posicion(casilla), 'rey' if isinstance(pieza, Rey) else 'peon',
                                  pieza.color)
        panel.turno_edicion.set('Blanco')
        for variable in panel.enroques_edicion.values():
            variable.set(False)
        panel.aplicar_edicion()
        self.assertIsNone(panel.editor, panel.mensaje.get())
        self.assertIs(panel.sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertEqual(len(panel.casillero.canvas.find_withtag('pieza')), 18)
        self.assertEqual(pickle.dumps(self.sesion.partida), original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
