"""Archivos de preferencias y arranque real sin usar la configuración personal."""

from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import tkinter as tk
import unittest
from unittest.mock import patch

from ajedrez.aplicacion import AplicacionAjedrez
from ajedrez.gráficos.opciones_visuales import ModoResaltadoJaque as Modo, OpcionesVisuales
from ajedrez.preferencias_graficas import (
    ErrorPreferencias, PreferenciasGraficas, cargar_preferencias, guardar_preferencias,
    obtener_ruta_preferencias_predeterminada, preferencias_a_datos, preferencias_desde_datos,
)
from ajedrez.persistencia import guardar_partida, partida_a_datos
from ajedrez.repositorio_partidas import RepositorioPartidasSQLite


class PruebasArchivoPreferencias(unittest.TestCase):
    def setUp(self):
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / 'configuracion' / 'preferencias.json'

    def test_archivo_ausente_no_crea_carpeta_y_devuelve_valores_predeterminados(self):
        self.assertEqual(cargar_preferencias(self.ruta), PreferenciasGraficas())
        self.assertFalse(self.ruta.parent.exists())

    def test_guardar_y_cargar_tema_y_todos_los_campos_de_cada_modo(self):
        for modo in Modo:
            with self.subTest(modo=modo):
                originales = PreferenciasGraficas(identificador_tema='taller.veta_fina',
                    opciones_visuales=OpcionesVisuales(modo_resaltado_jaque=modo,
                        intervalo_parpadeo_jaque_ms=450, repeticiones_parpadeo_jaque=5))
                guardar_preferencias(originales, self.ruta)
                self.assertEqual(cargar_preferencias(self.ruta), originales)
                datos = json.loads(self.ruta.read_text(encoding='utf-8'))
                self.assertEqual(set(datos), {'formato', 'version', 'tema', 'opciones_visuales'})
                self.assertEqual(datos['opciones_visuales']['modo_resaltado_jaque'], modo.value)
                self.assertEqual(tuple(self.ruta.parent.iterdir()), (self.ruta,))

    def test_campos_opcionales_omitidos_usan_sus_valores_predeterminados(self):
        datos = {'formato': 'ajedrez-local-preferencias', 'version': 1}
        self.assertEqual(preferencias_desde_datos(datos), PreferenciasGraficas())
        datos['opciones_visuales'] = {'modo_resaltado_jaque': 'rey_y_atacantes'}
        originales = copy.deepcopy(datos)
        resultado = preferencias_desde_datos(datos)
        self.assertIs(resultado.opciones_visuales.modo_resaltado_jaque, Modo.REY_Y_ATACANTES)
        self.assertEqual(resultado.opciones_visuales.intervalo_parpadeo_jaque_ms, 300)
        self.assertEqual(datos, originales)

    def test_archivos_invalidos_se_rechazan_sin_modificarlos(self):
        valido = preferencias_a_datos(PreferenciasGraficas())
        casos = [b'{', b'\xff\xfe', b'[]', b'null', b'{"formato":"ajedrez-local"}']
        for campo, valores in (('version', [True, 0, 2, '1']), ('tema', [None, 3, '']),
                              ('opciones_visuales', [None, []])):
            for valor in valores:
                datos = copy.deepcopy(valido)
                datos[campo] = valor
                casos.append(json.dumps(datos).encode())
        for campo, valores in (
            ('modo_resaltado_jaque', ['otro', 1, None]),
            ('intervalo_parpadeo_jaque_ms', [0, -1, True, 0.5]),
            ('repeticiones_parpadeo_jaque', [0, -1, True, '3']),
        ):
            for valor in valores:
                datos = copy.deepcopy(valido)
                datos['opciones_visuales'][campo] = valor
                casos.append(json.dumps(datos).encode())
        self.ruta.parent.mkdir()
        for contenido in casos:
            with self.subTest(contenido=contenido):
                self.ruta.write_bytes(contenido)
                with self.assertRaises(ErrorPreferencias):
                    cargar_preferencias(self.ruta)
                self.assertEqual(self.ruta.read_bytes(), contenido)

    def test_json_con_bom_se_lee_y_errores_de_acceso_se_propagan(self):
        self.ruta.parent.mkdir()
        self.ruta.write_text(json.dumps(preferencias_a_datos(PreferenciasGraficas())), encoding='utf-8-sig')
        self.assertEqual(cargar_preferencias(self.ruta), PreferenciasGraficas())
        with patch.object(Path, 'read_text', side_effect=PermissionError('Sin acceso')):
            with self.assertRaises(PermissionError):
                cargar_preferencias(self.ruta)

    def test_fallo_al_escribir_o_sustituir_conserva_el_archivo_y_elimina_el_temporal(self):
        anteriores = PreferenciasGraficas()
        nuevas = PreferenciasGraficas(identificador_tema='pizarra.microfibra')
        guardar_preferencias(anteriores, self.ruta)
        contenido = self.ruta.read_bytes()
        for operacion in ('os.fsync', 'os.replace'):
            with self.subTest(operacion=operacion), \
                 patch(f'ajedrez.preferencias_graficas.{operacion}', side_effect=OSError('Fallo de escritura')):
                with self.assertRaises(OSError):
                    guardar_preferencias(nuevas, self.ruta)
            self.assertEqual(self.ruta.read_bytes(), contenido)
            self.assertEqual(tuple(self.ruta.parent.iterdir()), (self.ruta,))
        guardar_preferencias(nuevas, self.ruta)
        self.assertEqual(cargar_preferencias(self.ruta), nuevas)

    def test_fallo_antes_de_crear_carpeta_no_deja_archivo(self):
        with patch.object(Path, 'mkdir', side_effect=PermissionError('Carpeta sin permiso')):
            with self.assertRaises(PermissionError):
                guardar_preferencias(PreferenciasGraficas(), self.ruta)
        self.assertFalse(self.ruta.exists())

    def test_ruta_del_usuario_independiente_del_directorio_de_trabajo(self):
        with patch.dict(os.environ, {'LOCALAPPDATA': self.temporal.name}):
            ruta = obtener_ruta_preferencias_predeterminada()
            self.assertEqual(ruta, Path(self.temporal.name) / 'ajedrez-local' / 'preferencias.json')
            self.assertFalse(ruta.parent.exists())
        with patch.dict(os.environ, {'LOCALAPPDATA': ''}), patch.object(Path, 'home', return_value=Path(self.temporal.name)):
            self.assertEqual(obtener_ruta_preferencias_predeterminada(),
                             Path(self.temporal.name) / '.config' / 'ajedrez-local' / 'preferencias.json')

    def test_lectura_en_otro_proceso_sin_importar_tkinter_ni_modelo(self):
        guardar_preferencias(PreferenciasGraficas(identificador_tema='taller.microfibra'), self.ruta)
        codigo = '''
import sys
from ajedrez.preferencias_graficas import cargar_preferencias
p = cargar_preferencias(sys.argv[1])
assert p.identificador_tema == 'taller.microfibra'
assert 'tkinter' not in sys.modules
assert 'ajedrez.partida' not in sys.modules
'''
        resultado = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', codigo, str(self.ruta)],
                                   cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                   text=True, encoding='utf-8', timeout=30)
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)


class PruebasPreferenciasEntreEjecuciones(unittest.TestCase):
    def setUp(self):
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / 'preferencias.json'
        self.errores = []
        self.addCleanup(self.assertFalse, self.errores)

    @contextmanager
    def aplicacion(self, *, usar_ruta_predeterminada=False, repositorio=None):
        ventana = tk.Tk()
        ventana.withdraw()
        ventana.report_callback_exception = lambda tipo, error, traza: self.errores.append(error)
        try:
            yield AplicacionAjedrez(ventana=ventana, repositorio=repositorio,
                                   ruta_preferencias=None if usar_ruta_predeterminada else self.ruta)
        finally:
            ventana.destroy()

    def elegir(self, app, tema='taller.veta_fina', modo=Modo.REY_Y_ATACANTES):
        app._boton_preferencias.invoke()
        dialogo = app._dialogo_preferencias
        dialogo._selector_tema.current(dialogo._identificadores_temas.index(tema))
        dialogo._opciones_jaque[modo].invoke()
        dialogo._boton_aplicar.invoke()
        return dialogo

    def test_primer_inicio_sin_archivo_usa_valores_predeterminados_sin_escribir(self):
        with self.aplicacion() as app:
            self.assertEqual(app.tema.identificador, 'club.liso_mate')
            self.assertEqual(app.interfaz_partida.opciones_visuales, OpcionesVisuales())
            self.assertFalse(app._hay_cambios_sin_guardar())
        self.assertFalse(self.ruta.exists())

    def test_aplicar_persiste_y_otro_arranque_recupera_antes_de_crear_la_vista(self):
        for modo in Modo:
            with self.subTest(modo=modo):
                with self.aplicacion() as app:
                    dialogo = self.elegir(app, modo=modo)
                    self.assertFalse(dialogo.winfo_exists())
                    self.assertFalse(app._hay_cambios_sin_guardar())
                with self.aplicacion() as reiniciada:
                    self.assertEqual(reiniciada.tema.identificador, 'taller.veta_fina')
                    vista = reiniciada.interfaz_partida
                    self.assertIs(vista.opciones_visuales.modo_resaltado_jaque, modo)
                    self.assertIs(vista.casillero.tema, reiniciada.tema)
                    self.assertEqual(vista.sesion.partida.contador_jugadas, 0)
                    vista.abrir_panel_analisis()
                    self.assertIs(vista._panel_analisis.opciones_visuales.modo_resaltado_jaque, modo)

    def test_campos_no_expuestos_por_el_dialogo_se_recuperan_y_conservan_al_guardar(self):
        guardar_preferencias(PreferenciasGraficas(opciones_visuales=OpcionesVisuales(
            intervalo_parpadeo_jaque_ms=450, repeticiones_parpadeo_jaque=5)), self.ruta)
        with self.aplicacion() as app:
            self.elegir(app)
        recuperadas = cargar_preferencias(self.ruta).opciones_visuales
        self.assertEqual(recuperadas.intervalo_parpadeo_jaque_ms, 450)
        self.assertEqual(recuperadas.repeticiones_parpadeo_jaque, 5)

    def test_cancelar_no_crea_archivo_ni_altera_las_preferencias_guardadas(self):
        for existente in (False, True):
            with self.subTest(existente=existente):
                if existente:
                    guardar_preferencias(PreferenciasGraficas(identificador_tema='taller.veta_fina'), self.ruta)
                antes = self.ruta.read_bytes() if existente else None
                with self.aplicacion() as app, patch('ajedrez.aplicacion.guardar_preferencias') as guardar:
                    app.solicitar_preferencias()
                    dialogo = app._dialogo_preferencias
                    dialogo._selector_tema.current(5)
                    dialogo._boton_restablecer.invoke()
                    dialogo._boton_cancelar.invoke()
                    guardar.assert_not_called()
                self.assertEqual(self.ruta.read_bytes() if self.ruta.exists() else None, antes)

    def test_restablecer_y_aplicar_se_conserva_en_el_siguiente_inicio(self):
        with self.aplicacion() as app:
            self.elegir(app)
            app.solicitar_preferencias()
            app._dialogo_preferencias._boton_restablecer.invoke()
            app._dialogo_preferencias._boton_aplicar.invoke()
        self.assertEqual(cargar_preferencias(self.ruta), PreferenciasGraficas())
        with self.aplicacion() as app:
            self.assertEqual(app.tema.identificador, 'club.liso_mate')
            self.assertIs(app.interfaz_partida.opciones_visuales.modo_resaltado_jaque, Modo.REY_PERMANENTE)

    def test_archivo_danado_o_version_futura_permite_arrancar_y_no_se_sobrescribe(self):
        futuro = preferencias_a_datos(PreferenciasGraficas())
        futuro['version'] = 99
        for contenido in (b'{', json.dumps(futuro).encode()):
            with self.subTest(contenido=contenido):
                self.ruta.write_bytes(contenido)
                with patch('ajedrez.aplicacion.messagebox.showwarning') as aviso, self.aplicacion() as app:
                    aviso.assert_called_once()
                    self.assertEqual(app.tema.identificador, 'club.liso_mate')
                    self.assertEqual(app.interfaz_partida.opciones_visuales, OpcionesVisuales())
                self.assertEqual(self.ruta.read_bytes(), contenido)

    def test_error_de_lectura_permite_arrancar_sin_escribir(self):
        with patch('ajedrez.aplicacion.cargar_preferencias', side_effect=PermissionError('Sin permiso')), \
             patch('ajedrez.aplicacion.messagebox.showwarning') as aviso, self.aplicacion() as app:
            aviso.assert_called_once()
            self.assertEqual(app.interfaz_partida.opciones_visuales, OpcionesVisuales())
        self.assertFalse(self.ruta.exists())

    def test_tema_no_disponible_conserva_opciones_del_jaque_y_archivo_original(self):
        preferencias = PreferenciasGraficas(identificador_tema='tema.retirado',
            opciones_visuales=OpcionesVisuales(modo_resaltado_jaque=Modo.REY_Y_ATACANTES))
        guardar_preferencias(preferencias, self.ruta)
        antes = self.ruta.read_bytes()
        with patch('ajedrez.aplicacion.messagebox.showwarning') as aviso, self.aplicacion() as app:
            aviso.assert_called_once()
            self.assertEqual(app.tema.identificador, 'club.liso_mate')
            self.assertEqual(app.interfaz_partida.opciones_visuales, preferencias.opciones_visuales)
            app.solicitar_preferencias()
            self.assertEqual(app._dialogo_preferencias._selector_tema.current(), 0)
        self.assertEqual(self.ruta.read_bytes(), antes)

    def test_fallo_de_guardado_conserva_archivo_vista_y_dialogo_y_permite_reintentar(self):
        guardar_preferencias(PreferenciasGraficas(), self.ruta)
        contenido = self.ruta.read_bytes()
        with self.aplicacion() as app:
            tema, opciones = app.tema, app.interfaz_partida.opciones_visuales
            ids = app.interfaz_partida.casillero.canvas.find_all()
            with patch('ajedrez.preferencias_graficas.os.replace', side_effect=PermissionError('Sin permiso')), \
                 patch('ajedrez.aplicacion.messagebox.showerror') as aviso:
                dialogo = self.elegir(app)
                aviso.assert_called_once()
            self.assertTrue(dialogo.winfo_exists())
            self.assertIs(dialogo.grab_current(), dialogo)
            self.assertIs(app.tema, tema)
            self.assertIs(app.interfaz_partida.opciones_visuales, opciones)
            self.assertEqual(app.interfaz_partida.casillero.canvas.find_all(), ids)
            self.assertEqual(self.ruta.read_bytes(), contenido)
            dialogo._boton_aplicar.invoke()
            self.assertFalse(dialogo.winfo_exists())
            self.assertEqual(cargar_preferencias(self.ruta).identificador_tema, 'taller.veta_fina')

    def test_fallo_al_cargar_tema_no_escribe_preferencias(self):
        guardar_preferencias(PreferenciasGraficas(), self.ruta)
        antes = self.ruta.read_bytes()
        with self.aplicacion() as app:
            with patch('ajedrez.aplicacion.cargar_tema', side_effect=FileNotFoundError('Falta un PNG')), \
                 patch('ajedrez.aplicacion.messagebox.showerror'), \
                 patch('ajedrez.aplicacion.guardar_preferencias') as guardar:
                dialogo = self.elegir(app)
                guardar.assert_not_called()
                self.assertTrue(dialogo.winfo_exists())
        self.assertEqual(self.ruta.read_bytes(), antes)

    def test_preferencias_no_modifican_partida_archivos_json_ni_biblioteca(self):
        ruta_db = Path(self.temporal.name) / 'biblioteca.sqlite3'
        ruta_partida = Path(self.temporal.name) / 'partida.json'
        repositorio = RepositorioPartidasSQLite(ruta_db)
        with self.aplicacion(repositorio=repositorio) as app:
            partida = app.interfaz_partida.sesion.partida
            guardar_partida(partida, ruta_partida)
            with patch('ajedrez.aplicacion.simpledialog.askstring', return_value='Original'):
                self.assertTrue(app.solicitar_guardar_en_biblioteca())
            identificador = app._id_partida_biblioteca
            partida.procesar_solicitud((1, 4), (3, 4))
            app.interfaz_partida.mostrar_estado(app.interfaz_partida.sesion.estado_actual)
            antes = partida_a_datos(partida)
            json_original, db_original = ruta_partida.read_bytes(), ruta_db.read_bytes()
            self.assertTrue(app._hay_cambios_sin_guardar())
            self.elegir(app)
            self.assertIs(app.interfaz_partida.sesion.partida, partida)
            self.assertEqual(partida_a_datos(partida), antes)
            self.assertTrue(app._hay_cambios_sin_guardar())
            self.assertEqual(app._id_partida_biblioteca, identificador)
            self.assertEqual(ruta_partida.read_bytes(), json_original)
            self.assertEqual(ruta_db.read_bytes(), db_original)

    def test_aplicacion_usa_ruta_del_usuario_si_no_se_proporciona_otra(self):
        with patch.dict(os.environ, {'LOCALAPPDATA': self.temporal.name}):
            ruta = obtener_ruta_preferencias_predeterminada()
            with self.aplicacion(usar_ruta_predeterminada=True) as app:
                self.assertEqual(app._ruta_preferencias, ruta)
                self.elegir(app)
            self.assertTrue(ruta.is_file())
            self.assertFalse(self.ruta.exists())
            self.assertFalse((ruta.parent / 'biblioteca.sqlite3').exists())
            with self.aplicacion(usar_ruta_predeterminada=True) as app:
                self.assertEqual(app.tema.identificador, 'taller.veta_fina')


if __name__ == '__main__':
    unittest.main()
