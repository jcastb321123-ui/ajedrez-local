"""Reconstrucción de partidas y escritura segura de archivos externos."""

import copy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ajedrez.partida import CapturaAlPaso, Enroque, EstadoPartida, EstadoPosicion, Jugada, Partida
from ajedrez.persistencia import (
    ErrorArchivoPartida, cargar_partida, guardar_partida, partida_a_datos, partida_desde_datos,
)
from ajedrez.piezas import Alfil, Caballo, Color, PeonBlanco, PeonNegro, Reina, Rey, Torre
from ajedrez.sesion import AsignacionColores, ModalidadAsignacion, SesionLocal
from ajedrez.tablero import Tablero
from pruebas.test_partida_estado_inicial import firma_tablero, posicion, registro


def jugar(partida, movimientos):
    for movimiento in movimientos.split():
        respuesta = partida.procesar_solicitud(posicion(movimiento[:2]), posicion(movimiento[2:]))
        if respuesta is not None:
            raise AssertionError((movimiento, respuesta))


def partida_con_piezas(piezas, turno=Color.Blanco, contador=0):
    tablero = Tablero()
    for casilla in tablero.casillas:
        tablero.colocar(None, casilla)
    for casilla, pieza in piezas.items():
        tablero.colocar(pieza, posicion(casilla))
    return Partida(estado_inicial=EstadoPosicion(
        tablero=tablero, jugadas_sin_captura_ni_peon=contador,
    ), turno_inicial=turno)


class PruebasPersistencia(unittest.TestCase):
    def reconstruir(self, partida):
        datos = partida_a_datos(partida)
        recuperada = partida_desde_datos(json.loads(json.dumps(datos)))
        self.assertEqual(partida_a_datos(recuperada), datos)
        self.assertEqual(recuperada.jugador, partida.jugador)
        self.assertEqual(recuperada.estado_partida, partida.estado_partida)
        self.assertEqual(registro(recuperada), registro(partida))
        estados = list(recuperada.iterar_estados())
        for original, nuevo in zip(partida.iterar_estados(), estados, strict=True):
            self.assertIsNot(original, nuevo)
            self.assertEqual(firma_tablero(original.tablero), firma_tablero(nuevo.tablero))
            self.assertEqual(original.jugadas_sin_captura_ni_peon, nuevo.jugadas_sin_captura_ni_peon)
        for anterior, siguiente in zip(estados, estados[1:]):
            self.assertIs(siguiente.estado_anterior, anterior)
        jugadas = [j for t in recuperada.registro_turnos
                   for j in (t.jugada_blanco, t.jugada_negro) if j is not None]
        for indice, jugada in enumerate(jugadas):
            self.assertIs(jugada.anterior, jugadas[indice - 1] if indice else None)
            self.assertIs(jugada.siguiente, jugadas[indice + 1] if indice + 1 < len(jugadas) else None)
        self.assertIs(recuperada.ultima_jugada, jugadas[-1] if jugadas else None)
        return recuperada

    def test_partida_nueva_y_continuacion_independiente(self):
        original = Partida()
        self.reconstruir(original)
        jugar(original, 'e2e4 e7e5 g1f3 b8c6')
        recuperada = self.reconstruir(original)
        jugar(recuperada, 'f1b5')
        self.assertEqual(original.contador_jugadas, 4)
        self.assertEqual(recuperada.contador_jugadas, 5)
        self.assertIsNotNone(original.tablero.pieza_en(posicion('f1')))

    def test_enroques_y_derechos_perdidos(self):
        partida = partida_con_piezas({'e1': Rey(Color.Blanco), 'a1': Torre(Color.Blanco),
                                     'e8': Rey(Color.Negro), 'h8': Torre(Color.Negro)})
        jugar(partida, 'e1c1 e8g8')
        recuperada = self.reconstruir(partida)
        self.assertIsInstance(recuperada.ultima_jugada, Enroque)
        self.assertFalse(recuperada.tablero.obtener_derechos_enroque())
        movida = Torre(Color.Blanco)
        movida.movimiento_realizado()
        partida = partida_con_piezas({'e1': Rey(Color.Blanco), 'a1': movida,
                                     'e8': Rey(Color.Negro)})
        self.assertFalse(self.reconstruir(partida).tablero.obtener_derechos_enroque())

    def test_captura_al_paso_en_primera_jugada_y_raiz_con_negras(self):
        for previa, movimiento in [('e2e4 a7a6 e4e5 d7d5', 'e5d6'),
                                    ('a2a3 e7e5 a3a4 e5e4 d2d4', 'e4d3')]:
            with self.subTest(movimiento=movimiento):
                base = Partida()
                jugar(base, previa)
                partida = Partida(estado_inicial=base.ultima_jugada.estado_posicion)
                recuperada = self.reconstruir(partida)
                jugar(recuperada, movimiento)
                self.assertIsInstance(recuperada.ultima_jugada, CapturaAlPaso)
                self.reconstruir(recuperada)

    def test_las_cuatro_promociones_de_ambos_colores_con_captura(self):
        for color in Color:
            for clase in (Caballo, Alfil, Torre, Reina):
                with self.subTest(color=color, pieza=clase):
                    blancas = color is Color.Blanco
                    piezas = {'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                              'a7' if blancas else 'a2': PeonBlanco() if blancas else PeonNegro(),
                              'b8' if blancas else 'b1': Torre(Color.Negro if blancas else Color.Blanco)}
                    # Evita que la torre dé jaque al rey que va a promocionar.
                    piezas['h7' if blancas else 'h2'] = piezas.pop('h8' if blancas else 'h1')
                    partida = partida_con_piezas(piezas, color)
                    origen, destino = ('a7', 'b8') if blancas else ('a2', 'b1')
                    pendiente = partida.procesar_solicitud(posicion(origen), posicion(destino))
                    self.assertIsInstance(pendiente, Jugada)
                    partida.promocionar(posicion(destino), clase(color), pendiente)
                    recuperada = self.reconstruir(partida)
                    self.assertIsInstance(recuperada.tablero.pieza_en(posicion(destino)), clase)

    def test_conserva_repeticiones_y_permita_reclamar_despues_de_cargar(self):
        partida = Partida()
        jugar(partida, 'g1f3 g8f6 f3g1 f6g8 ' * 2)
        recuperada = self.reconstruir(partida)
        self.assertEqual(recuperada.apariciones_posicion_actual, 3)
        self.assertTrue(recuperada.reclamar_tablas_por_triple_repeticion())
        self.reconstruir(recuperada)

    def test_conserva_contador_de_raiz_y_movimiento_anunciado(self):
        partida = partida_con_piezas({'e1': Rey(Color.Blanco), 'a1': Torre(Color.Blanco),
                                     'e8': Rey(Color.Negro)}, contador=99)
        recuperada = self.reconstruir(partida)
        anuncio = (posicion('a1'), posicion('a2'))
        self.assertTrue(recuperada.tablas_por_cincuenta_movimientos_disponible(movimiento_anunciado=anuncio))
        jugar(recuperada, 'a1a2')
        self.assertTrue(self.reconstruir(recuperada).tablas_por_cincuenta_movimientos_disponible())

    def test_resultados_por_abandono_acuerdo_mate_y_tablas_automaticas(self):
        abandonada = Partida()
        abandonada.abandonar(Color.Negro)
        acuerdo = Partida()
        jugar(acuerdo, 'e2e4 e7e5')
        acuerdo.estado_partida = EstadoPartida.TABLAS
        mate = Partida()
        jugar(mate, 'f2f3 e7e5 g2g4 d8h4')
        repeticion = Partida()
        jugar(repeticion, 'g1f3 g8f6 f3g1 f6g8 ' * 4)
        for partida in (abandonada, acuerdo, mate, repeticion):
            with self.subTest(resultado=partida.estado_partida):
                self.reconstruir(partida)

    def test_sesion_local_recupera_partida_y_regenera_autenticacion(self):
        original = SesionLocal(AsignacionColores(ModalidadAsignacion.BLANCO_NEGRO))
        original.solicitar_movimiento(posicion('e2'), posicion('e4'))
        recuperada = self.reconstruir(original.partida)
        sesion = SesionLocal(AsignacionColores(ModalidadAsignacion.BLANCO_NEGRO), partida=recuperada)
        self.assertIs(sesion.partida, recuperada)
        self.assertNotEqual(sesion.emisor_1.clave, original.emisor_1.clave)
        sesion.solicitar_movimiento(posicion('e7'), posicion('e5'))
        self.assertEqual(sesion.partida.contador_jugadas, 2)
        self.assertIs(sesion.estado_actual, recuperada.ultima_jugada.estado_posicion)

    def test_archivo_se_puede_cargar_en_otra_instancia(self):
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'partida con espacios.json'
            partida = Partida()
            jugar(partida, 'e2e4 d7d5 e4d5')
            guardar_partida(partida, ruta)
            self.assertEqual(partida_a_datos(cargar_partida(ruta)), partida_a_datos(partida))
            self.assertEqual(list(Path(carpeta).iterdir()), [ruta])

    def test_recuperacion_y_continuacion_en_otro_proceso(self):
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'entre ejecuciones.json'
            partida = Partida()
            jugar(partida, 'e2e4')
            guardar_partida(partida, ruta)
            codigo = '''
import sys
from ajedrez.persistencia import cargar_partida, guardar_partida
partida = cargar_partida(sys.argv[1])
assert partida.contador_jugadas == 1
assert partida.procesar_solicitud((6, 4), (4, 4)) is None
guardar_partida(partida, sys.argv[1])
'''
            resultado = subprocess.run(
                [sys.executable, '-B', '-X', 'utf8', '-c', codigo, str(ruta)],
                cwd=Path(__file__).resolve().parents[1], capture_output=True,
                text=True, encoding='utf-8', timeout=30,
            )
            self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
            self.assertEqual(cargar_partida(ruta).contador_jugadas, 2)
            self.assertEqual(partida.contador_jugadas, 1)

    def test_fallo_de_escritura_no_destruye_guardado_anterior(self):
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'partida.json'
            partida = Partida()
            guardar_partida(partida, ruta)
            anterior = ruta.read_bytes()
            jugar(partida, 'e2e4')
            with patch('ajedrez.persistencia.os.replace', side_effect=OSError('Sin permiso')):
                with self.assertRaises(OSError):
                    guardar_partida(partida, ruta)
            self.assertEqual(ruta.read_bytes(), anterior)
            self.assertEqual(list(Path(carpeta).iterdir()), [ruta])

    def test_promocion_pendiente_no_se_guarda(self):
        partida = partida_con_piezas({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                                     'a7': PeonBlanco()})
        partida.procesar_solicitud(posicion('a7'), posicion('a8'))
        with self.assertRaisesRegex(ErrorArchivoPartida, 'promoción'):
            partida_a_datos(partida)

    def test_rechaza_estructura_version_y_metadatos_corruptos(self):
        inicial = partida_a_datos(Partida())
        variantes = [None, [], {}, dict(inicial, version=2), dict(inicial, version=True),
                     dict(inicial, formato='otro'), dict(inicial, resultado='INVALIDO'),
                     dict(inicial, jugadas={})]
        for clave, valor in [('turno', 'otro'), ('jugadas_sin_captura_ni_peon', -1),
                             ('jugadas_sin_captura_ni_peon', True),
                             ('peon_capturable_al_paso', [8, 3])]:
            datos = copy.deepcopy(inicial)
            datos['posicion_inicial'][clave] = valor
            variantes.append(datos)
        for clave, valor in [('casilla', [False, 0]), ('casilla', [0, 9]), ('tipo', []),
                             ('color', 'otro'), ('ha_movido', 'False')]:
            datos = copy.deepcopy(inicial)
            datos['posicion_inicial']['piezas'][0][clave] = valor
            variantes.append(datos)
        duplicada = copy.deepcopy(inicial)
        duplicada['posicion_inicial']['piezas'].append(duplicada['posicion_inicial']['piezas'][0])
        variantes.append(duplicada)
        sin_reyes = copy.deepcopy(inicial)
        sin_reyes['posicion_inicial']['piezas'] = []
        variantes.append(sin_reyes)
        for datos in variantes:
            with self.subTest(datos=datos), self.assertRaises(ErrorArchivoPartida):
                partida_desde_datos(datos)

    def test_rechaza_movimientos_ilegales_y_promociones_incoherentes(self):
        for movimiento in [{'origen': [1, 4], 'destino': [5, 4], 'promocion': None},
                           {'origen': [1, 4], 'destino': [3, 4], 'promocion': 'reina'},
                           {'origen': [1, 4], 'destino': [3, 4], 'promocion': []}]:
            datos = partida_a_datos(Partida())
            datos['jugadas'] = [movimiento]
            with self.subTest(movimiento=movimiento), self.assertRaises(ErrorArchivoPartida):
                partida_desde_datos(datos)

    def test_json_invalido_y_resultado_contradictorio(self):
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'rota.json'
            for contenido in (b'{', b'\xff'):
                ruta.write_bytes(contenido)
                with self.assertRaises(ErrorArchivoPartida):
                    cargar_partida(ruta)
        partida = Partida()
        jugar(partida, 'f2f3 e7e5 g2g4 d8h4')
        datos = partida_a_datos(partida)
        datos['resultado'] = 'EN_CURSO'
        with self.assertRaises(ErrorArchivoPartida):
            partida_desde_datos(datos)


if __name__ == '__main__':
    unittest.main()
