"""Guardado, actualización, carga y listado sin perder datos ni conexiones."""

from contextlib import closing
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ajedrez.partida import Partida
from ajedrez.persistencia import ErrorArchivoPartida, partida_a_datos, partida_desde_datos
from ajedrez.piezas import Color, PeonBlanco, Rey, Torre
from ajedrez.repositorio_partidas import (
    RepositorioPartidasSQLite, ResumenPartida, obtener_ruta_biblioteca_predeterminada,
)
from pruebas.test_persistencia import jugar, partida_con_piezas
from pruebas.test_sesion import SesionDePrueba


class PruebasInicializacionRepositorio(unittest.TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.carpeta = Path(carpeta.name)

    def test_crea_archivo_y_tabla_con_ruta_string_o_path(self):
        for tipo_ruta in (str, Path):
            with self.subTest(tipo=tipo_ruta):
                ruta = self.carpeta / f'biblioteca José {tipo_ruta.__name__}.sqlite3'
                RepositorioPartidasSQLite(tipo_ruta(ruta))
                self.assertTrue(ruta.is_file())
                # Otra conexión debe ver el esquema ya confirmado.
                with closing(sqlite3.connect(ruta)) as conexion:
                    columnas = conexion.execute('PRAGMA table_info(partidas)').fetchall()
                    self.assertEqual(
                        [(columna[1], columna[2], columna[3], columna[5]) for columna in columnas],
                        [('id_partida', 'INTEGER', 0, 1),
                         ('titulo', 'TEXT', 1, 0),
                         ('contenido_json', 'TEXT', 1, 0),
                         ('fecha_creacion', 'TEXT', 1, 0),
                         ('fecha_actualizacion', 'TEXT', 1, 0)],
                    )
                    self.assertEqual(conexion.execute('SELECT COUNT(*) FROM partidas').fetchone(), (0,))

    def test_reabrir_conserva_la_partida_y_su_identificador(self):
        ruta = self.carpeta / 'biblioteca.sqlite3'
        RepositorioPartidasSQLite(ruta)
        datos = partida_a_datos(Partida())
        registro = (41, "Partida de José: 'ensayo'", json.dumps(datos, ensure_ascii=False),
                    '2026-11-10T10:00:00+00:00', '2026-11-10T11:00:00+00:00')
        with closing(sqlite3.connect(ruta, autocommit=False)) as conexion:
            with conexion:
                conexion.execute(
                    'INSERT INTO partidas '
                    '(id_partida, titulo, contenido_json, fecha_creacion, fecha_actualizacion) '
                    'VALUES (?, ?, ?, ?, ?)', registro,
                )

        RepositorioPartidasSQLite(ruta)

        with closing(sqlite3.connect(ruta, autocommit=False)) as conexion:
            recuperado = conexion.execute(
                'SELECT id_partida, titulo, contenido_json, fecha_creacion, fecha_actualizacion '
                'FROM partidas WHERE id_partida = ?', (41,),
            ).fetchone()
            self.assertEqual(recuperado, registro)
            self.assertEqual(json.loads(recuperado[2]), datos)
            with conexion:
                siguiente = conexion.execute(
                    'INSERT INTO partidas (titulo, contenido_json, fecha_creacion, fecha_actualizacion) '
                    'VALUES (?, ?, ?, ?)', registro[1:],
                ).lastrowid
            self.assertEqual(siguiente, 42)

    def test_cierra_la_conexion_al_terminar(self):
        conectar = sqlite3.connect
        conexiones = []

        def registrar_conexion(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar_conexion):
            repositorio = RepositorioPartidasSQLite(self.carpeta / 'biblioteca.sqlite3')

        self.assertTrue(conexiones)
        # El repositorio sigue vivo; el cierre no puede depender de recolectarlo.
        self.assertIsInstance(repositorio, RepositorioPartidasSQLite)
        for conexion in conexiones:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexion.execute('SELECT 1')

    def test_cierra_la_conexion_y_conserva_el_archivo_si_sqlite_falla(self):
        ruta = self.carpeta / 'archivo_invalido.sqlite3'
        contenido = b'Este archivo no es una base de datos SQLite.\n' * 8
        ruta.write_bytes(contenido)
        conectar = sqlite3.connect
        conexiones = []

        def registrar_conexion(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar_conexion):
            with self.assertRaises(sqlite3.DatabaseError):
                RepositorioPartidasSQLite(ruta)
        self.assertEqual(ruta.read_bytes(), contenido)
        self.assertTrue(conexiones)
        for conexion in conexiones:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexion.execute('SELECT 1')


class PruebasGuardadoRepositorio(unittest.TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta = Path(carpeta.name) / 'biblioteca.sqlite3'
        self.repositorio = RepositorioPartidasSQLite(self.ruta)

    def leer_registros(self):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            conexion.row_factory = sqlite3.Row
            return [dict(fila) for fila in conexion.execute('SELECT * FROM partidas ORDER BY id_partida')]

    def test_guarda_modelo_completo_titulo_fechas_e_identificador(self):
        partida = Partida()
        jugar(partida, 'e2e4 d7d5 e4d5')
        partida.abandonar(Color.Negro)
        datos_originales = partida_a_datos(partida)
        titulo = "Análisis de José'); DROP TABLE partidas; -- ♞"
        antes = datetime.now(UTC)
        identificador = self.repositorio.guardar_partida(partida, titulo)
        despues = datetime.now(UTC)

        registros = self.leer_registros()
        self.assertEqual(len(registros), 1)
        registro = registros[0]
        self.assertIsInstance(identificador, int)
        self.assertEqual(registro['id_partida'], identificador)
        self.assertEqual(registro['titulo'], titulo)
        self.assertEqual(json.loads(registro['contenido_json']), datos_originales)
        self.assertEqual(partida_a_datos(partida), datos_originales)
        recuperada = partida_desde_datos(json.loads(registro['contenido_json']))
        self.assertEqual(partida_a_datos(recuperada), datos_originales)
        self.assertEqual(recuperada.jugador, partida.jugador)
        self.assertEqual(recuperada.estado_partida, partida.estado_partida)
        self.assertEqual(registro['fecha_creacion'], registro['fecha_actualizacion'])
        fecha = datetime.fromisoformat(registro['fecha_creacion'])
        self.assertEqual(fecha.utcoffset(), timedelta(0))
        self.assertLessEqual(antes, fecha)
        self.assertLessEqual(fecha, despues)

    def test_cada_guardado_es_independiente_y_sobrevive_a_la_reapertura(self):
        partida = Partida()
        datos_iniciales = partida_a_datos(partida)
        primero = self.repositorio.guardar_partida(partida, 'Entrenamiento')
        registro_inicial = self.leer_registros()[0]
        jugar(partida, 'e2e4')
        segundo = self.repositorio.guardar_partida(partida, 'Entrenamiento')
        otro_repositorio = RepositorioPartidasSQLite(self.ruta)
        tercero = otro_repositorio.guardar_partida(Partida(), 'Otra partida')
        self.assertEqual(len({primero, segundo, tercero}), 3)
        registros = self.leer_registros()
        self.assertEqual([r['id_partida'] for r in registros], [primero, segundo, tercero])
        self.assertEqual(registros[0], registro_inicial)
        self.assertEqual(json.loads(registros[0]['contenido_json']), datos_iniciales)
        self.assertEqual(json.loads(registros[1]['contenido_json']), partida_a_datos(partida))

    def test_guarda_modelo_de_sesion_alternativa_sin_dependencias_locales(self):
        partida = Partida(turno_inicial=Color.Negro)
        jugar(partida, 'e7e5')
        sesion = SesionDePrueba(partida)
        identificador = self.repositorio.guardar_partida(sesion.partida, 'Sesión alternativa')
        registro = self.leer_registros()[0]
        self.assertEqual(registro['id_partida'], identificador)
        recuperada = partida_desde_datos(json.loads(registro['contenido_json']))
        self.assertEqual(recuperada.primer_jugador, Color.Negro)
        self.assertEqual(partida_a_datos(recuperada), partida_a_datos(sesion.partida))
        otra_sesion = SesionDePrueba(recuperada)
        self.assertIs(otra_sesion.estado_actual, recuperada.ultima_jugada.estado_posicion)

    def test_promocion_pendiente_no_inserta_ni_altera_registros(self):
        self.repositorio.guardar_partida(Partida(), 'Guardada anteriormente')
        antes = self.leer_registros()
        pendiente = partida_con_piezas({
            'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro), 'a7': PeonBlanco(),
        })
        pendiente.procesar_solicitud((6, 0), (7, 0))
        self.assertTrue(pendiente.promocion_pendiente)
        with self.assertRaises(ErrorArchivoPartida):
            self.repositorio.guardar_partida(pendiente, 'Promoción por resolver')
        self.assertEqual(self.leer_registros(), antes)
        self.assertTrue(pendiente.promocion_pendiente)

    def test_cierra_la_conexion_tras_confirmar_el_guardado(self):
        conectar = sqlite3.connect
        conexiones = []

        def registrar_conexion(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar_conexion):
            identificador = self.repositorio.guardar_partida(Partida(), 'Prueba de cierre')
        self.assertEqual(self.leer_registros()[0]['id_partida'], identificador)
        self.assertTrue(conexiones)
        for conexion in conexiones:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexion.execute('SELECT 1')

    def test_error_sql_revierte_insercion_y_cierra_la_conexion(self):
        self.repositorio.guardar_partida(Partida(), 'Registro que debe conservarse')
        anteriores = self.leer_registros()
        with closing(sqlite3.connect(self.ruta, autocommit=False)) as conexion:
            with conexion:
                # FAIL permite detectar una fila parcial si el llamador no revierte.
                conexion.execute("""
                    CREATE TRIGGER rechazar_guardado AFTER INSERT ON partidas
                    BEGIN
                        SELECT RAISE(FAIL, 'Fallo de escritura simulado');
                    END
                """)
        conectar = sqlite3.connect
        conexiones = []

        def registrar_conexion(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar_conexion):
            with self.assertRaises(sqlite3.IntegrityError):
                self.repositorio.guardar_partida(Partida(), 'No debe quedar guardada')
        self.assertEqual(self.leer_registros(), anteriores)
        self.assertTrue(conexiones)
        for conexion in conexiones:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexion.execute('SELECT 1')


class PruebasCargaRepositorio(unittest.TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta = Path(carpeta.name) / 'biblioteca.sqlite3'
        self.repositorio = RepositorioPartidasSQLite(self.ruta)

    def leer_registros(self):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            return conexion.execute('SELECT * FROM partidas ORDER BY id_partida').fetchall()

    def sustituir_contenido(self, identificador, contenido):
        with closing(sqlite3.connect(self.ruta, autocommit=False)) as conexion:
            with conexion:
                conexion.execute(
                    'UPDATE partidas SET contenido_json = ? WHERE id_partida = ?',
                    (contenido, identificador),
                )

    def test_recupera_por_identificador_partidas_nuevas_y_finalizadas_tras_reabrir(self):
        finalizada = Partida()
        jugar(finalizada, 'e2e4 d7d5 e4d5')
        finalizada.abandonar(Color.Negro)
        esperados = {}
        for partida in (Partida(), finalizada):
            identificador = self.repositorio.guardar_partida(partida, 'Mismo título')
            esperados[identificador] = partida_a_datos(partida)
        registros = self.leer_registros()
        reabierto = RepositorioPartidasSQLite(self.ruta)
        for identificador, datos in esperados.items():
            with self.subTest(identificador=identificador):
                recuperada = reabierto.cargar_partida(identificador)
                self.assertIsInstance(recuperada, Partida)
                self.assertEqual(partida_a_datos(recuperada), datos)
        self.assertEqual(self.leer_registros(), registros)

    def test_reconstruye_enlaces_y_permite_continuar_sin_cambiar_otras_cargas(self):
        original = Partida()
        jugar(original, 'e2e4 d7d5 e4d5')
        datos = partida_a_datos(original)
        identificador = self.repositorio.guardar_partida(original, 'Continuación')
        registros = self.leer_registros()
        recuperada = self.repositorio.cargar_partida(identificador)
        otra = self.repositorio.cargar_partida(identificador)
        self.assertIsNot(recuperada, otra)
        estados = list(recuperada.iterar_estados())
        self.assertEqual(len(estados), 4)
        self.assertIs(estados[0], recuperada.estado_inicial)
        for previo, siguiente in zip(estados, estados[1:]):
            self.assertIs(siguiente.estado_anterior, previo)
        jugadas = [jugada for turno in recuperada.registro_turnos
                   for jugada in (turno.jugada_blanco, turno.jugada_negro)
                   if jugada is not None]
        for indice, jugada in enumerate(jugadas):
            self.assertIs(jugada.anterior, jugadas[indice - 1] if indice else None)
            self.assertIs(jugada.siguiente, jugadas[indice + 1] if indice + 1 < len(jugadas) else None)
        self.assertIs(recuperada.ultima_jugada, jugadas[-1])
        self.assertIs(recuperada.ultima_jugada.estado_posicion, estados[-1])
        jugar(recuperada, 'g8f6')
        self.assertEqual(recuperada.contador_jugadas, 4)
        self.assertEqual(partida_a_datos(original), datos)
        self.assertEqual(partida_a_datos(otra), datos)
        self.assertEqual(partida_a_datos(self.repositorio.cargar_partida(identificador)), datos)
        self.assertEqual(self.leer_registros(), registros)

    def test_posicion_personalizada_y_turno_se_pueden_usar_en_sesion_alternativa(self):
        original = partida_con_piezas({
            'e1': Rey(Color.Blanco), 'a1': Torre(Color.Blanco),
            'e8': Rey(Color.Negro), 'h8': Torre(Color.Negro),
        }, turno=Color.Negro, contador=99)
        identificador = self.repositorio.guardar_partida(original, 'Problema con negras')
        recuperada = self.repositorio.cargar_partida(identificador)
        sesion = SesionDePrueba(recuperada)
        self.assertIs(sesion.partida, recuperada)
        self.assertIs(sesion.estado_actual, recuperada.estado_inicial)
        self.assertIs(recuperada.jugador, Color.Negro)
        self.assertEqual(partida_a_datos(recuperada), partida_a_datos(original))
        self.assertEqual(recuperada.tablero.obtener_derechos_enroque(),
                         original.tablero.obtener_derechos_enroque())
        jugar(recuperada, 'h8h7')
        self.assertIs(sesion.estado_actual, recuperada.ultima_jugada.estado_posicion)
        self.assertTrue(recuperada.tablas_por_cincuenta_movimientos_disponible())
        self.assertEqual(original.contador_jugadas, 0)

    def test_conserva_repeticiones_para_reclamar_tras_la_carga(self):
        original = Partida()
        jugar(original, 'g1f3 g8f6 f3g1 f6g8 ' * 2)
        identificador = self.repositorio.guardar_partida(original, 'Tres posiciones iguales')
        recuperada = self.repositorio.cargar_partida(identificador)
        self.assertEqual(recuperada.apariciones_posicion_actual, 3)
        self.assertTrue(recuperada.reclamar_tablas_por_triple_repeticion())
        self.assertEqual(partida_a_datos(self.repositorio.cargar_partida(identificador)),
                         partida_a_datos(original))

    def test_identificador_inexistente_lanza_keyerror_sin_modificar_registros(self):
        with self.assertRaises(KeyError) as error:
            self.repositorio.cargar_partida(1)
        self.assertEqual(error.exception.args, (1,))
        identificador = self.repositorio.guardar_partida(Partida(), 'Debe conservarse')
        registros = self.leer_registros()
        with self.assertRaises(KeyError) as error:
            self.repositorio.cargar_partida(identificador + 1)
        self.assertEqual(error.exception.args, (identificador + 1,))
        self.assertEqual(self.leer_registros(), registros)

    def test_rechaza_json_version_e_historial_invalidos_sin_modificar_registros(self):
        datos = partida_a_datos(Partida())
        ilegal = dict(datos, jugadas=[{
            'origen': [1, 4], 'destino': [5, 4], 'promocion': None,
        }])
        identificador = self.repositorio.guardar_partida(Partida(), 'Contenido dañado')
        for contenido in ('{', 'null', json.dumps(dict(datos, version=999)), json.dumps(ilegal)):
            with self.subTest(contenido=contenido):
                self.sustituir_contenido(identificador, contenido)
                registros = self.leer_registros()
                with self.assertRaises(ErrorArchivoPartida):
                    self.repositorio.cargar_partida(identificador)
                self.assertEqual(self.leer_registros(), registros)

    def test_cierra_conexiones_tanto_en_exito_como_en_errores_de_carga(self):
        valido = self.repositorio.guardar_partida(Partida(), 'Válida')
        json_roto = self.repositorio.guardar_partida(Partida(), 'JSON roto')
        datos_rotos = self.repositorio.guardar_partida(Partida(), 'Datos rotos')
        self.sustituir_contenido(json_roto, '{')
        self.sustituir_contenido(datos_rotos, '{}')
        conectar = sqlite3.connect
        conexiones = []

        def registrar_conexion(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        for identificador, error in ((valido, None), (datos_rotos + 1, KeyError),
                                     (json_roto, ErrorArchivoPartida),
                                     (datos_rotos, ErrorArchivoPartida)):
            with self.subTest(identificador=identificador):
                conexiones.clear()
                with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar_conexion):
                    if error is None:
                        self.repositorio.cargar_partida(identificador)
                    else:
                        with self.assertRaises(error):
                            self.repositorio.cargar_partida(identificador)
                self.assertTrue(conexiones)
                for conexion in conexiones:
                    with self.assertRaises(sqlite3.ProgrammingError):
                        conexion.execute('SELECT 1')

    def test_propaga_error_sql_y_cierra_conexion(self):
        # La tabla desaparece después de crear el repositorio.
        with closing(sqlite3.connect(self.ruta, autocommit=False)) as conexion:
            with conexion:
                conexion.execute('DROP TABLE partidas')
        conectar = sqlite3.connect
        conexiones = []

        def registrar_conexion(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar_conexion):
            with self.assertRaises(sqlite3.OperationalError):
                self.repositorio.cargar_partida(1)
        self.assertTrue(conexiones)
        for conexion in conexiones:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexion.execute('SELECT 1')


class PruebasListadoRepositorio(unittest.TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta = Path(carpeta.name) / 'biblioteca.sqlite3'
        self.repositorio = RepositorioPartidasSQLite(self.ruta)

    def test_biblioteca_vacia_y_listados_independientes_de_guardados_posteriores(self):
        vacio = self.repositorio.listar_partidas()
        self.assertEqual(vacio, ())
        primero = self.repositorio.guardar_partida(Partida(), 'Primera')
        anterior = self.repositorio.listar_partidas()
        segundo = self.repositorio.guardar_partida(Partida(), 'Segunda')
        actual = self.repositorio.listar_partidas()
        self.assertEqual(vacio, ())
        self.assertEqual([entrada.id_partida for entrada in anterior], [primero])
        self.assertEqual({entrada.id_partida for entrada in actual}, {primero, segundo})

    def test_metadatos_orden_y_empates_se_conservan_tras_reabrir_sin_modificar_datos(self):
        titulo = "Análisis de José: 'ensayo' ♞"
        identificadores = [self.repositorio.guardar_partida(Partida(), titulo) for _ in range(3)]
        creacion = '2026-11-10T10:00:00+00:00'
        antigua = '2026-11-11T10:00:00+00:00'
        reciente = '2026-11-12T10:00:00.123456+00:00'
        # El mayor id tiene la actualización más antigua; los otros dos empatan.
        with closing(sqlite3.connect(self.ruta, autocommit=False)) as conexion:
            with conexion:
                conexion.executemany(
                    'UPDATE partidas SET fecha_creacion = ?, fecha_actualizacion = ? '
                    'WHERE id_partida = ?',
                    [(creacion, fecha, identificador)
                     for identificador, fecha in zip(identificadores, (reciente, reciente, antigua))],
                )
            registros_antes = conexion.execute('SELECT * FROM partidas ORDER BY id_partida').fetchall()
        esperado = (
            ResumenPartida(identificadores[1], titulo, datetime.fromisoformat(creacion),
                          datetime.fromisoformat(reciente)),
            ResumenPartida(identificadores[0], titulo, datetime.fromisoformat(creacion),
                          datetime.fromisoformat(reciente)),
            ResumenPartida(identificadores[2], titulo, datetime.fromisoformat(creacion),
                          datetime.fromisoformat(antigua)),
        )
        reabierto = RepositorioPartidasSQLite(self.ruta)
        resultado = reabierto.listar_partidas()
        self.assertEqual(resultado, esperado)
        for resumen in resultado:
            self.assertEqual(resumen.fecha_creacion.utcoffset(), timedelta(0))
            self.assertEqual(resumen.fecha_actualizacion.utcoffset(), timedelta(0))
        self.assertEqual(partida_a_datos(reabierto.cargar_partida(resultado[0].id_partida)),
                         partida_a_datos(Partida()))
        with closing(sqlite3.connect(self.ruta)) as conexion:
            self.assertEqual(conexion.execute('SELECT * FROM partidas ORDER BY id_partida').fetchall(),
                             registros_antes)

    def test_lista_sin_leer_el_json_ni_reconstruir_el_modelo(self):
        identificador = self.repositorio.guardar_partida(Partida(), 'Historial dañado')
        with closing(sqlite3.connect(self.ruta, autocommit=False)) as conexion:
            with conexion:
                conexion.execute('UPDATE partidas SET contenido_json = ? WHERE id_partida = ?',
                                 ('{', identificador))
        conectar = sqlite3.connect

        def impedir_lectura_historial(accion, tabla, columna, base, origen):
            if accion == sqlite3.SQLITE_READ and tabla == 'partidas' and columna == 'contenido_json':
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        def conectar_sin_acceso_al_historial(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            self.addCleanup(conexion.close)
            conexion.set_authorizer(impedir_lectura_historial)
            return conexion

        # SQLite impide leer el campo, incluso mediante SELECT *.
        with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=conectar_sin_acceso_al_historial):
            resultado = self.repositorio.listar_partidas()
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0].id_partida, identificador)
        self.assertEqual(resultado[0].titulo, 'Historial dañado')
        with self.assertRaises(ErrorArchivoPartida):
            self.repositorio.cargar_partida(identificador)

    def test_resultado_disponible_con_conexion_cerrada_en_biblioteca_vacia_y_con_datos(self):
        conectar = sqlite3.connect
        conexiones = []

        def registrar_conexion(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        for cantidad in (0, 1):
            with self.subTest(cantidad=cantidad):
                if cantidad:
                    self.repositorio.guardar_partida(Partida(), 'Guardada')
                conexiones.clear()
                with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar_conexion):
                    resultado = self.repositorio.listar_partidas()
                self.assertTrue(conexiones)
                for conexion in conexiones:
                    with self.assertRaises(sqlite3.ProgrammingError):
                        conexion.execute('SELECT 1')
                self.assertEqual(len(resultado), cantidad)
                self.assertEqual([entrada.titulo for entrada in resultado], ['Guardada'] if cantidad else [])

    def test_error_sql_se_propaga_y_cierra_la_conexion(self):
        with closing(sqlite3.connect(self.ruta, autocommit=False)) as conexion:
            with conexion:
                conexion.execute('DROP TABLE partidas')
        conectar = sqlite3.connect
        conexiones = []

        def registrar_conexion(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar_conexion):
            with self.assertRaises(sqlite3.OperationalError):
                self.repositorio.listar_partidas()
        self.assertTrue(conexiones)
        for conexion in conexiones:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexion.execute('SELECT 1')


class PruebasActualizacionRepositorio(unittest.TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta = Path(carpeta.name) / 'biblioteca.sqlite3'
        self.repositorio = RepositorioPartidasSQLite(self.ruta)

    def leer_registros(self):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            conexion.row_factory = sqlite3.Row
            return {fila['id_partida']: dict(fila)
                    for fila in conexion.execute('SELECT * FROM partidas ORDER BY id_partida')}

    def test_actualiza_contenido_titulo_y_fecha_conservando_id_creacion_y_otros_registros(self):
        partida = Partida()
        with patch('ajedrez.repositorio_partidas.datetime') as reloj:
            reloj.now.return_value = datetime(2026, 1, 1, tzinfo=UTC)
            identificador = self.repositorio.guardar_partida(partida, 'Título anterior')
        otro = self.repositorio.guardar_partida(Partida(), 'Debe conservarse')
        registros_antes = self.leer_registros()
        jugar(partida, 'e2e4 d7d5 e4d5')
        datos = partida_a_datos(partida)
        titulo = "Análisis de José'); DELETE FROM partidas; -- ♞"
        antes = datetime.now(UTC)
        resultado = self.repositorio.actualizar_partida(identificador, partida, titulo)
        despues = datetime.now(UTC)

        self.assertIsNone(resultado)
        registros = self.leer_registros()
        self.assertEqual(set(registros), set(registros_antes))
        actualizado = registros[identificador]
        self.assertEqual(actualizado['id_partida'], identificador)
        self.assertEqual(actualizado['fecha_creacion'], registros_antes[identificador]['fecha_creacion'])
        self.assertEqual(actualizado['titulo'], titulo)
        self.assertEqual(json.loads(actualizado['contenido_json']), datos)
        fecha = datetime.fromisoformat(actualizado['fecha_actualizacion'])
        self.assertEqual(fecha.utcoffset(), timedelta(0))
        self.assertLessEqual(antes, fecha)
        self.assertLessEqual(fecha, despues)
        self.assertNotEqual(actualizado['fecha_actualizacion'], registros_antes[identificador]['fecha_actualizacion'])
        self.assertEqual(registros[otro], registros_antes[otro])
        reabierto = RepositorioPartidasSQLite(self.ruta)
        self.assertEqual(partida_a_datos(reabierto.cargar_partida(identificador)), datos)
        self.assertEqual(partida_a_datos(partida), datos)

    def test_sin_cambios_renueva_fecha_y_orden_del_listado_y_admite_repetir_actualizacion(self):
        partida = Partida()
        creacion = datetime(2026, 1, 1, tzinfo=UTC)
        posterior = datetime(2026, 1, 2, tzinfo=UTC)
        actualizacion = datetime(2026, 1, 3, tzinfo=UTC)
        with patch('ajedrez.repositorio_partidas.datetime') as reloj:
            reloj.now.side_effect = (creacion, posterior)
            primero = self.repositorio.guardar_partida(partida, 'Primera')
            segundo = self.repositorio.guardar_partida(Partida(), 'Segunda')
        listado_anterior = self.repositorio.listar_partidas()
        self.assertEqual([r.id_partida for r in listado_anterior], [segundo, primero])
        with patch('ajedrez.repositorio_partidas.datetime') as reloj:
            reloj.now.return_value = actualizacion
            self.repositorio.actualizar_partida(primero, partida, 'Primera')
            # Coinciden también las fechas: una fila existente no es un id ausente.
            self.repositorio.actualizar_partida(primero, partida, 'Primera')
        listado_actual = self.repositorio.listar_partidas()
        self.assertEqual([r.id_partida for r in listado_actual], [primero, segundo])
        self.assertEqual(listado_actual[0], ResumenPartida(primero, 'Primera', creacion, actualizacion))
        self.assertEqual(listado_actual[1], listado_anterior[0])
        self.assertEqual(listado_anterior[1].fecha_actualizacion, creacion)
        self.assertEqual(partida_a_datos(self.repositorio.cargar_partida(primero)), partida_a_datos(partida))

    def test_actualiza_partida_de_sesion_alternativa_en_curso_y_finalizada(self):
        partida = Partida(turno_inicial=Color.Negro)
        sesion = SesionDePrueba(partida)
        identificador = self.repositorio.guardar_partida(sesion.partida, 'Sesión alternativa')
        jugar(partida, 'e7e5')
        self.repositorio.actualizar_partida(identificador, sesion.partida, 'En curso')
        recuperada = self.repositorio.cargar_partida(identificador)
        self.assertEqual(partida_a_datos(recuperada), partida_a_datos(partida))
        self.assertIs(recuperada.primer_jugador, Color.Negro)
        self.assertIs(recuperada.jugador, Color.Blanco)
        partida.abandonar(Color.Blanco)
        self.repositorio.actualizar_partida(identificador, sesion.partida, 'Finalizada')
        recuperada = self.repositorio.cargar_partida(identificador)
        self.assertEqual(partida_a_datos(recuperada), partida_a_datos(partida))
        self.assertEqual(recuperada.estado_partida, partida.estado_partida)
        otra_sesion = SesionDePrueba(recuperada)
        self.assertIs(otra_sesion.estado_actual, recuperada.ultima_jugada.estado_posicion)
        self.assertEqual(len(self.repositorio.listar_partidas()), 1)

    def test_identificador_inexistente_lanza_keyerror_y_no_inserta_ni_modifica(self):
        partida = Partida()
        with self.assertRaises(KeyError) as error:
            self.repositorio.actualizar_partida(1, partida, 'No existe')
        self.assertEqual(error.exception.args, (1,))
        self.assertEqual(self.leer_registros(), {})
        identificador = self.repositorio.guardar_partida(partida, 'Debe conservarse')
        registros_antes = self.leer_registros()
        with self.assertRaises(KeyError) as error:
            self.repositorio.actualizar_partida(identificador + 1, partida, 'No existe')
        self.assertEqual(error.exception.args, (identificador + 1,))
        self.assertEqual(self.leer_registros(), registros_antes)

    def test_promocion_pendiente_no_sustituye_registro_ni_modifica_partida(self):
        partida = partida_con_piezas({
            'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro), 'a7': PeonBlanco(),
        })
        identificador = self.repositorio.guardar_partida(partida, 'Antes de promocionar')
        registros_antes = self.leer_registros()
        partida.procesar_solicitud((6, 0), (7, 0))
        self.assertTrue(partida.promocion_pendiente)
        with self.assertRaises(ErrorArchivoPartida):
            self.repositorio.actualizar_partida(identificador, partida, 'Promoción pendiente')
        self.assertEqual(self.leer_registros(), registros_antes)
        self.assertTrue(partida.promocion_pendiente)
        self.assertEqual(partida_a_datos(self.repositorio.cargar_partida(identificador)),
                         json.loads(registros_antes[identificador]['contenido_json']))

    def test_error_sql_revierte_toda_la_actualizacion_y_cierra_conexion(self):
        partida = Partida()
        identificador = self.repositorio.guardar_partida(partida, 'Antes del fallo')
        self.repositorio.guardar_partida(Partida(), 'Otro registro')
        registros_antes = self.leer_registros()
        with closing(sqlite3.connect(self.ruta, autocommit=False)) as conexion:
            with conexion:
                # FAIL deja el UPDATE aplicado si el llamador no revierte la transacción.
                conexion.execute("""
                    CREATE TRIGGER rechazar_actualizacion AFTER UPDATE ON partidas
                    BEGIN
                        SELECT RAISE(FAIL, 'Fallo de escritura simulado');
                    END
                """)
        jugar(partida, 'e2e4')
        conectar = sqlite3.connect
        conexiones = []

        def registrar_conexion(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar_conexion):
            with self.assertRaises(sqlite3.IntegrityError):
                self.repositorio.actualizar_partida(identificador, partida, 'No debe quedar escrito')
        self.assertEqual(self.leer_registros(), registros_antes)
        self.assertTrue(conexiones)
        for conexion in conexiones:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexion.execute('SELECT 1')

    def test_cierra_conexion_tras_actualizar_y_ante_identificador_ausente(self):
        partida = Partida()
        identificador = self.repositorio.guardar_partida(partida, 'Guardada')
        conectar = sqlite3.connect
        conexiones = []

        def registrar_conexion(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        for objetivo in (identificador, identificador + 1):
            with self.subTest(identificador=objetivo):
                conexiones.clear()
                with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar_conexion):
                    if objetivo == identificador:
                        self.repositorio.actualizar_partida(objetivo, partida, 'Actualizada')
                    else:
                        with self.assertRaises(KeyError):
                            self.repositorio.actualizar_partida(objetivo, partida, 'Ausente')
                self.assertTrue(conexiones)
                for conexion in conexiones:
                    with self.assertRaises(sqlite3.ProgrammingError):
                        conexion.execute('SELECT 1')
        self.assertEqual(self.leer_registros()[identificador]['titulo'], 'Actualizada')


class PruebasEliminacionRepositorio(unittest.TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta = Path(carpeta.name) / 'biblioteca.sqlite3'
        self.repositorio = RepositorioPartidasSQLite(self.ruta)

    def registros(self):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            return conexion.execute('SELECT * FROM partidas ORDER BY id_partida').fetchall()

    def test_borrado_persistente_y_selectivo_conserva_los_modelos_ya_cargados(self):
        primero = self.repositorio.guardar_partida(Partida(), 'Mismo título')
        segundo = self.repositorio.guardar_partida(Partida(), 'Mismo título')
        datos = self.registros()
        partida = self.repositorio.cargar_partida(primero)
        self.assertIsNone(self.repositorio.eliminar_partida(primero))
        self.assertEqual(self.registros(), [datos[1]])
        otro = RepositorioPartidasSQLite(self.ruta)
        self.assertEqual([r.id_partida for r in otro.listar_partidas()], [segundo])
        with self.assertRaises(KeyError):
            otro.cargar_partida(primero)
        jugar(partida, 'e2e4')
        self.assertEqual(partida.contador_jugadas, 1)
        otro.eliminar_partida(segundo)
        self.assertEqual(otro.listar_partidas(), ())

    def test_id_ausente_y_borrado_repetido_lanzan_keyerror(self):
        with self.assertRaises(KeyError) as error:
            self.repositorio.eliminar_partida(42)
        self.assertEqual(error.exception.args, (42,))
        identificador = self.repositorio.guardar_partida(Partida(), 'Ensayo')
        self.repositorio.eliminar_partida(identificador)
        with self.assertRaises(KeyError):
            self.repositorio.eliminar_partida(identificador)
        self.assertEqual(self.registros(), [])

    def test_error_sql_revierte_borrado_y_cierra_conexion(self):
        identificador = self.repositorio.guardar_partida(Partida(), 'Debe sobrevivir')
        antes = self.registros()
        with closing(sqlite3.connect(self.ruta, autocommit=False)) as conexion:
            with conexion:
                conexion.execute("""
                    CREATE TRIGGER rechazar_borrado AFTER DELETE ON partidas
                    BEGIN SELECT RAISE(FAIL, 'Fallo de borrado simulado'); END
                """)
        conectar = sqlite3.connect
        conexiones = []

        def registrar(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar):
            with self.assertRaises(sqlite3.IntegrityError):
                self.repositorio.eliminar_partida(identificador)
        self.assertEqual(self.registros(), antes)
        self.assertTrue(conexiones)
        for conexion in conexiones:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexion.execute('SELECT 1')

    def test_cierra_conexion_en_exito_y_ausencia(self):
        identificador = self.repositorio.guardar_partida(Partida(), 'Ensayo')
        conectar = sqlite3.connect
        conexiones = []

        def registrar(*args, **kwargs):
            conexion = conectar(*args, **kwargs)
            conexiones.append(conexion)
            self.addCleanup(conexion.close)
            return conexion

        with patch('ajedrez.repositorio_partidas.sqlite3.connect', side_effect=registrar):
            self.repositorio.eliminar_partida(identificador)
            with self.assertRaises(KeyError):
                self.repositorio.eliminar_partida(identificador)
        self.assertEqual(len(conexiones), 2)
        for conexion in conexiones:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexion.execute('SELECT 1')

    def test_ruta_predeterminada_usa_datos_de_usuario_sin_crear_archivos(self):
        with patch.dict('os.environ', {'LOCALAPPDATA': str(self.ruta.parent)}):
            ruta = obtener_ruta_biblioteca_predeterminada()
            self.assertEqual(ruta, self.ruta.parent / 'ajedrez-local' / 'biblioteca.sqlite3')
            self.assertFalse(ruta.parent.exists())
        with (patch.dict('os.environ', {'LOCALAPPDATA': ''}),
              patch('pathlib.Path.home', return_value=self.ruta.parent)):
            self.assertEqual(obtener_ruta_biblioteca_predeterminada(),
                             self.ruta.parent / '.local' / 'share' / 'ajedrez-local' / 'biblioteca.sqlite3')


if __name__ == '__main__':
    unittest.main()
