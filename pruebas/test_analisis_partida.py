"""Aislamiento del historial, prioridad de navegación y edición libre."""
import pickle
import unittest

from ajedrez.analisis_partida import AnalisisPartida
from ajedrez.editor_posicion import EditorPosicion
from ajedrez.partida import Partida, EstadoPosicion, CapturaAlPaso, Enroque, MotivoRechazoMovimiento
from ajedrez.piezas import Color, Rey, Torre, Reina, PeonBlanco, PeonNegro
from ajedrez.sesion import SesionAnalisis, PiezaPromocion
from ajedrez.tablero import Tablero


def posicion(nombre):
    return int(nombre[1]) - 1, ord(nombre[0]) - ord('a')


def mover(partida, notacion):
    return partida.procesar_solicitud(posicion(notacion[:2]), posicion(notacion[2:]))


def estado_minimo(piezas):
    tablero = Tablero()
    for casilla in tablero.casillas:
        tablero.colocar(None, casilla)
    for casilla, pieza in piezas.items():
        tablero.colocar(pieza, posicion(casilla))
    return EstadoPosicion(tablero=tablero)


class PruebasAnalisis(unittest.TestCase):
    def setUp(self):
        self.partida = Partida()
        for notacion in ('e2e4', 'e7e5', 'g1f3'):
            self.assertIsNone(mover(self.partida, notacion))
        self.estados = tuple(self.partida.iterar_estados())
        self.analisis = AnalisisPartida(self.partida)
        self.original = pickle.dumps(self.partida)

    def tearDown(self):
        self.assertEqual(pickle.dumps(self.partida), self.original)

    def jugar(self, estado, notacion):
        resultado = self.analisis.solicitar_movimiento(estado, posicion(notacion[:2]), posicion(notacion[2:]))
        self.assertIsNone(resultado)
        return self.analisis.sesion_hipotetica.estado_actual

    def test_siguiente_real_tiene_prioridad_y_descarta_variante(self):
        raiz = self.estados[1]
        hipotetico = self.jugar(raiz, 'c7c5')
        self.assertIs(self.analisis.obtener_anterior(hipotetico), raiz)
        self.assertIs(self.analisis.obtener_siguiente(raiz), self.estados[2])
        self.assertIsNone(self.analisis.sesion_hipotetica)
        self.assertFalse(self.analisis.estados_hipoteticos)

    def test_sin_continuacion_real_sigue_la_hipotetica(self):
        raiz = self.estados[-1]
        primero = self.jugar(raiz, 'b8c6')
        segundo = self.jugar(primero, 'f1b5')
        self.assertIs(self.analisis.obtener_siguiente(raiz), primero)
        self.assertIs(self.analisis.obtener_siguiente(primero), segundo)
        self.assertIsNone(self.analisis.obtener_siguiente(segundo))
        self.assertIs(self.analisis.obtener_anterior(segundo), primero)
        self.assertIsNone(self.analisis.obtener_anterior(self.estados[0]))

    def test_sustituir_rama_conserva_prefijo_y_rechazo_conserva_todo(self):
        raiz = self.estados[-1]
        primero = self.jugar(raiz, 'b8c6')
        self.jugar(primero, 'f1b5')
        anterior = self.analisis.estados_hipoteticos
        rechazo = self.analisis.solicitar_movimiento(primero, posicion('a1'), posicion('a8'))
        self.assertIs(rechazo, MotivoRechazoMovimiento.MOVIMIENTO_INVALIDO)
        self.assertEqual(self.analisis.estados_hipoteticos, anterior)
        nuevo = self.jugar(primero, 'f1c4')
        self.assertEqual(self.analisis.estados_hipoteticos, (raiz, primero, nuevo))
        self.assertIs(self.analisis.obtener_anterior(nuevo), primero)
        self.assertIs(self.analisis.obtener_siguiente(primero), nuevo)

    def test_sesion_copia_piezas_y_no_arrastra_historial(self):
        fuente = self.estados[-1]
        sesion = SesionAnalisis(fuente, Color.Negro)
        self.assertIsNone(sesion.estado_actual.estado_anterior)
        self.assertIsNone(sesion.partida.ultima_jugada)
        for casilla, pieza in fuente.tablero.casillas.items():
            if pieza is not None:
                self.assertIsNot(sesion.estado_actual.tablero.pieza_en(casilla), pieza)
        self.assertIsNone(sesion.solicitar_movimiento(posicion('b8'), posicion('c6')))

    def test_fuera_del_tablero_se_rechaza(self):
        sesion = SesionAnalisis(self.estados[-1], Color.Negro)
        self.assertIs(sesion.solicitar_movimiento((-1, 0), (8, 0)), MotivoRechazoMovimiento.MOVIMIENTO_INVALIDO)


class PruebasRaicesEspeciales(unittest.TestCase):
    def test_historial_con_negras_primero(self):
        partida = Partida(turno_inicial=Color.Negro)
        estados = [partida.estado_inicial]
        for notacion in ('e7e5', 'e2e4', 'b8c6'):
            self.assertIsNone(mover(partida, notacion))
            estados.append(partida.ultima_jugada.estado_posicion)
        self.assertEqual(list(partida.iterar_estados()), estados)
        for i, estado in enumerate(estados):
            self.assertIs(partida.obtener_turno_en_estado(estado), Color.Negro if i % 2 == 0 else Color.Blanco)
            self.assertIs(partida.obtener_estado_siguiente(estado), estados[i + 1] if i < 3 else None)

    def test_copia_conserva_enroque_y_captura_al_paso(self):
        for secuencia, siguiente, tipo in (
            ('e2e4 a7a6 e4e5 d7d5', 'e5d6', CapturaAlPaso),
            ('e2e4 a7a6 g1f3 a6a5 f1e2 b7b6', 'e1g1', Enroque),
        ):
            with self.subTest(tipo=tipo):
                partida = Partida()
                for notacion in secuencia.split():
                    self.assertIsNone(mover(partida, notacion))
                antes = pickle.dumps(partida)
                sesion = SesionAnalisis(partida.ultima_jugada.estado_posicion, partida.jugador)
                self.assertIsNone(sesion.solicitar_movimiento(posicion(siguiente[:2]), posicion(siguiente[2:])))
                self.assertIsInstance(sesion.partida.ultima_jugada, tipo)
                self.assertEqual(pickle.dumps(partida), antes)

    def test_promocion_no_crea_nodo_hasta_confirmar(self):
        estado = estado_minimo({'e1': Rey(Color.Blanco), 'e8': Rey(Color.Negro), 'a7': PeonBlanco()})
        partida = Partida(estado_inicial=estado, turno_inicial=Color.Blanco)
        antes = pickle.dumps(partida)
        analisis = AnalisisPartida(partida)
        self.assertIsNone(analisis.solicitar_movimiento(estado, posicion('a7'), posicion('a8')))
        self.assertIsNotNone(analisis.jugada_pendiente)
        self.assertFalse(analisis.estados_hipoteticos)
        self.assertIsNone(analisis.obtener_siguiente(estado))
        self.assertIs(analisis.solicitar_movimiento(estado, posicion('e1'), posicion('e2')),
                      MotivoRechazoMovimiento.PROMOCION_PENDIENTE)
        analisis.confirmar_promocion(PiezaPromocion.REINA)
        nuevo = analisis.obtener_siguiente(estado)
        self.assertIsInstance(nuevo.tablero.pieza_en(posicion('a8')), Reina)
        self.assertIsNone(nuevo.tablero.pieza_en(posicion('a7')))
        self.assertEqual(pickle.dumps(partida), antes)


class PruebasEditor(unittest.TestCase):
    def setUp(self):
        self.estado = EstadoPosicion()
        self.antes = pickle.dumps(self.estado)
        self.editor = EditorPosicion(self.estado, Color.Blanco)

    def tearDown(self):
        self.assertEqual(pickle.dumps(self.estado), self.antes)

    def test_colocar_quitar_mover_y_deshacer(self):
        self.editor.quitar(posicion('a2'))
        self.editor.colocar(posicion('a3'), 'dama', Color.Negro)
        self.editor.mover(posicion('a3'), posicion('a4'))
        self.assertIsInstance(self.editor.tablero.pieza_en(posicion('a4')), Reina)
        for _ in range(3):
            self.editor.deshacer()
        self.assertEqual(pickle.dumps(self.editor.tablero), pickle.dumps(self.estado.tablero))

    def test_turno_negro_sin_movimiento_ficticio(self):
        nuevo = self.editor.construir_estado(turno=Color.Negro, enroques=self.editor.derechos_enroque())
        self.assertIsNone(nuevo.origen)
        self.assertIsNone(nuevo.pieza)
        sesion = SesionAnalisis(nuevo, Color.Negro)
        self.assertIsNone(sesion.solicitar_movimiento(posicion('e7'), posicion('e5')))

    def test_rechaza_reyes_ausentes_duplicados_adyacentes_y_peones_extremos(self):
        casos = (
            {'e1': Rey(Color.Blanco)},
            {'e1': Rey(Color.Blanco), 'a1': Rey(Color.Blanco), 'e8': Rey(Color.Negro)},
            {'e1': Rey(Color.Blanco), 'e2': Rey(Color.Negro)},
            {'e1': Rey(Color.Blanco), 'e8': Rey(Color.Negro), 'a8': PeonBlanco()},
        )
        for piezas in casos:
            with self.subTest(piezas=piezas), self.assertRaises(ValueError):
                EditorPosicion(estado_minimo(piezas), Color.Blanco).construir_estado(turno=Color.Blanco, enroques=set())

    def test_rechaza_jaque_al_bando_sin_turno(self):
        estado = estado_minimo({'e1': Rey(Color.Blanco), 'a8': Rey(Color.Negro), 'a1': Torre(Color.Blanco)})
        editor = EditorPosicion(estado, Color.Blanco)
        with self.assertRaises(ValueError):
            editor.construir_estado(turno=Color.Blanco, enroques=set())
        editor.construir_estado(turno=Color.Negro, enroques=set())

    def test_derechos_enroque_solo_los_explicitados(self):
        derechos = {(Color.Blanco, 7)}
        estado = self.editor.construir_estado(turno=Color.Blanco, enroques=derechos)
        self.assertEqual(EditorPosicion(estado, Color.Blanco).derechos_enroque(), derechos)
        self.editor.quitar(posicion('h1'))
        with self.assertRaises(ValueError):
            self.editor.construir_estado(turno=Color.Blanco, enroques=derechos)

    def test_captura_al_paso_en_primera_jugada_del_borrador(self):
        estado = estado_minimo({'e1': Rey(Color.Blanco), 'e8': Rey(Color.Negro),
                                'e5': PeonBlanco(), 'd5': PeonNegro()})
        editor = EditorPosicion(estado, Color.Blanco)
        nuevo = editor.construir_estado(turno=Color.Blanco, enroques=set(), peon_al_paso=posicion('d5'))
        sesion = SesionAnalisis(nuevo, Color.Blanco)
        self.assertIsNone(sesion.solicitar_movimiento(posicion('e5'), posicion('d6')))
        self.assertIsInstance(sesion.partida.ultima_jugada, CapturaAlPaso)
        self.assertIsNone(sesion.estado_actual.tablero.pieza_en(posicion('d5')))
        with self.assertRaises(ValueError):
            editor.construir_estado(turno=Color.Negro, enroques=set(), peon_al_paso=posicion('d5'))

    def test_editar_invalida_al_paso_y_deshacer_lo_recupera(self):
        partida = Partida()
        mover(partida, 'e2e4')
        editor = EditorPosicion(partida.ultima_jugada.estado_posicion, Color.Negro)
        editor.quitar(posicion('a2'))
        self.assertIsNone(editor.tablero.posicion_de_captura_al_paso)
        editor.deshacer()
        self.assertEqual(editor.tablero.posicion_de_captura_al_paso, posicion('e4'))


if __name__ == '__main__':
    unittest.main()
