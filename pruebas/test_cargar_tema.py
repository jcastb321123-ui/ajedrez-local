"""Carga del catálogo y prueba de integración con PNG y Tkinter reales."""

import gc
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import patch

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ajedrez.gráficos.temas_graficos import (
    CARPETA_RECURSOS_PREDETERMINADA, EstiloMarca, cargar_tema,
)
from ajedrez.gráficos.graficos_tablero import Casillero
from ajedrez.gráficos.interfaz_partida import InterfazPartida
from ajedrez.gráficos.opciones_visuales import OpcionesVisuales, ModoResaltadoJaque
from ajedrez.piezas import Color
from ajedrez.sesion import SesionLocal, AsignacionColores, ModalidadAsignacion


class PruebasContratoCargador(unittest.TestCase):
    def test_opciones_solo_por_nombre_y_con_valores_predeterminados(self):
        for nombre, parametro in inspect.signature(cargar_tema).parameters.items():
            if nombre != 'master':
                self.assertEqual(parametro.kind, inspect.Parameter.KEYWORD_ONLY)
                self.assertIsNot(parametro.default, inspect.Parameter.empty)
        with self.assertRaises(TypeError):
            cargar_tema(object(), 'club.liso_mate')

    def test_catalogo_inexistente_explica_que_carpeta_se_necesita(self):
        with patch.object(Path, 'is_file', return_value=False):
            with patch('ajedrez.gráficos.temas_graficos.tk.PhotoImage') as cargar:
                with self.assertRaisesRegex(FileNotFoundError, 'carpeta_recursos'):
                    cargar_tema(object(), carpeta_recursos=Path(__file__).parent / 'ausente')
                cargar.assert_not_called()


class PruebasCatalogoReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.carpeta = CARPETA_RECURSOS_PREDETERMINADA
        ruta = cls.carpeta / 'catalogo.json'
        if not ruta.is_file():
            raise AssertionError('Falta el catálogo de recursos incluido en ajedrez.')
        cls.catalogo_texto = ruta.read_text(encoding='utf-8')
        cls.catalogo = json.loads(cls.catalogo_texto)

    def test_los_doce_temas_seleccionan_sus_recursos(self):
        master = object()
        self.assertEqual(len(self.catalogo['temas']), 12)
        with patch('ajedrez.gráficos.temas_graficos.tk.PhotoImage',
                   side_effect=lambda **datos: SimpleNamespace(**datos)):
            for identificador, definicion in self.catalogo['temas'].items():
                with self.subTest(tema=identificador):
                    tema = cargar_tema(master, identificador=identificador)
                    self.assertEqual(tema.identificador, identificador)
                    self.assertIs(tema.casillas['clara'].master, master)
                    recursos = self.catalogo['recursos']
                    for color in ('clara', 'oscura'):
                        id_recurso = definicion[f'casilla_{color}']
                        esperada = self.carpeta / recursos[id_recurso]['png']['60']['archivo']
                        self.assertEqual(Path(tema.casillas[color].file), esperada)
                    id_rey = f"{definicion['familia_piezas']}.blanca.rey"
                    esperada = self.carpeta / recursos[id_rey]['png']['60']['archivo']
                    self.assertEqual(Path(tema.piezas['rey', Color.Blanco, 'normal'].file), esperada)
                    id_proyeccion = f"{definicion['proyecciones']}.negra.dama"
                    esperada = self.carpeta / recursos[id_proyeccion]['png']['60']['archivo']
                    self.assertEqual(Path(tema.proyecciones['dama', Color.Negro].file), esperada)
                    self.assertEqual(tema.colores['fondo'],
                                     self.catalogo['paletas'][definicion['paleta']]['fondo'])
                    self.assertEqual(tema.colores['flecha_estrategica'], '#2C455B')
                    self.assertEqual(tema.colores['flecha_estrategica_seleccionada'], '#527FA7')

    def test_tema_inexistente_no_crea_imagenes(self):
        with patch('ajedrez.gráficos.temas_graficos.tk.PhotoImage') as cargar:
            with self.assertRaisesRegex(ValueError, 'Tema desconocido'):
                cargar_tema(object(), identificador='no_existe')
            cargar.assert_not_called()

    def test_tamano_invalido_no_crea_imagenes(self):
        with patch('ajedrez.gráficos.temas_graficos.tk.PhotoImage') as cargar:
            for tamano in (0, -60, 61, True, 60.0, '60'):
                with self.subTest(tamano=tamano):
                    with self.assertRaisesRegex(ValueError, 'Tamaño de casilla'):
                        cargar_tema(object(), dimension_casilla=tamano)
            cargar.assert_not_called()

    def test_carpeta_explicita_utiliza_rutas_absolutas(self):
        with patch('os.getcwd', return_value=str(self.carpeta.parent)):
            with patch('ajedrez.gráficos.temas_graficos.tk.PhotoImage',
                       side_effect=lambda **datos: SimpleNamespace(**datos)):
                tema = cargar_tema(object(), carpeta_recursos=str(self.carpeta))
                self.assertTrue(Path(tema.casillas['clara'].file).is_absolute())
                self.assertEqual(len(tema.piezas), 24)

    def test_error_identifica_imagen_ausente(self):
        is_file_original = Path.is_file
        def is_file(ruta):
            return ruta.name != 'clara.png' and is_file_original(ruta)
        with patch.object(Path, 'is_file', is_file):
            with self.assertRaisesRegex(FileNotFoundError, 'casilla.club.liso_mate.clara'):
                cargar_tema(object())

    def test_recurso_sin_escala_se_identifica(self):
        catalogo = json.loads(self.catalogo_texto)
        del catalogo['recursos']['casilla.club.liso_mate.clara']['png']['60']
        with patch('ajedrez.gráficos.temas_graficos.json.load', return_value=catalogo):
            with self.assertRaisesRegex(ValueError, 'casilla.club.liso_mate.clara.*60 px'):
                cargar_tema(object())

    def test_no_carga_rutas_fuera_del_paquete(self):
        catalogo = json.loads(self.catalogo_texto)
        catalogo['recursos']['casilla.club.liso_mate.clara']['png']['60']['archivo'] = '../fuera.png'
        with patch('ajedrez.gráficos.temas_graficos.json.load', return_value=catalogo):
            with self.assertRaisesRegex(ValueError, 'fuera de carpeta_recursos'):
                cargar_tema(object())

    def test_una_misma_imagen_no_se_carga_dos_veces(self):
        catalogo = json.loads(self.catalogo_texto)
        catalogo['temas']['club.liso_mate']['casilla_oscura'] = 'casilla.club.liso_mate.clara'
        with patch('ajedrez.gráficos.temas_graficos.json.load', return_value=catalogo):
            with patch('ajedrez.gráficos.temas_graficos.tk.PhotoImage',
                       side_effect=lambda **datos: SimpleNamespace(**datos)) as cargar:
                tema = cargar_tema(object())
                self.assertIs(tema.casillas['clara'], tema.casillas['oscura'])
                rutas = [llamada.kwargs['file'] for llamada in cargar.call_args_list]
                self.assertEqual(len(rutas), len(set(rutas)))


class PruebasCargaTkReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (CARPETA_RECURSOS_PREDETERMINADA / 'catalogo.json').is_file():
            raise AssertionError('Falta el catálogo de recursos incluido en ajedrez.')
        try:
            cls.ventana = tk.Tk()
        except tk.TclError as error:
            raise unittest.SkipTest(str(error)) from error
        cls.ventana.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.ventana.destroy()

    def test_predeterminado_contiene_todos_los_grupos_y_claves(self):
        tema = cargar_tema(self.ventana)
        self.assertEqual(tema.identificador, 'club.liso_mate')
        self.assertEqual(tema.dimension_casillas, 60)
        cantidades = {'casillas': 2, 'piezas': 24, 'proyecciones': 12,
                      'marcas': 18, 'flechas': 12, 'distintivos': 2,
                      'secuencias': 10, 'iconos': 6, 'fondos': 1,
                      'controles': 3, 'glifos': 32}
        for nombre, cantidad in cantidades.items():
            self.assertEqual(len(getattr(tema, nombre)), cantidad, nombre)
            for imagen in getattr(tema, nombre).values():
                self.assertIsInstance(imagen, tk.PhotoImage)
                self.assertIs(imagen.tk, self.ventana.tk)
        for clave, grupo in [(('continua', 'rojo'), tema.flechas),
                             (('caballo', 'ambar'), tema.flechas),
                             (('anotar', 'grafito'), tema.iconos),
                             (('a', 'marfil'), tema.glifos),
                             (10, tema.secuencias), ('club', tema.fondos)]:
            self.assertIn(clave, grupo)
        self.assertNotIn('nota', tema.tipografia)
        self.assertIs(tema.marcas['atacante_jaque'], tema.marcas['circulo_ambar'])
        self.assertEqual(tema.estilos_marcas['atacante_jaque'], EstiloMarca('marca', 'estado'))
        self.assertNotEqual(tema.casillas['clara'].get(30, 30), tema.casillas['oscura'].get(30, 30))
        gc.collect()
        self.assertEqual(tema.piezas['rey', Color.Blanco, 'normal'].width(), 60)

    def test_otros_tamanos_cargan_png_nativos_y_geometria_proporcionada(self):
        for tamano in (120, 240):
            with self.subTest(tamano=tamano):
                tema = cargar_tema(self.ventana, identificador='taller.veta_fina',
                                   dimension_casilla=tamano)
                self.assertEqual(tema.casillas['clara'].width(), tamano)
                self.assertEqual(tema.piezas['rey', Color.Negro, 'normal'].height(), tamano)
                self.assertEqual(tema.proyecciones['peon', Color.Blanco].width(), tamano)
                self.assertEqual(tema.marcas['jaque'].height(), tamano)
                self.assertEqual(tema.flechas['continua', 'azul'].width(), tamano * 3)
                self.assertEqual(tema.geometria['flecha']['width'], 4 * tamano / 60)
                self.assertEqual(tema.geometria['flecha']['arrowshape'],
                                 [valor * tamano / 60 for valor in (12, 16, 5)])

    def test_cambios_parciales_conservan_el_resto_y_no_se_comparten(self):
        colores = {'ambar': '#CCA030'}
        tipografia = {'interfaz': {'tamano_px': 20, 'alternativas': ['Arial']}}
        geometria = {'flecha': {'width': 7, 'arrowshape': [14.0, 18.0, 6.0]}}
        estilos = {'seleccion': EstiloMarca('resaltado', 'seleccion')}
        tema = cargar_tema(self.ventana, colores=colores, tipografia=tipografia,
                           geometria=geometria, estilos_marcas=estilos)
        otro = cargar_tema(self.ventana)
        self.assertEqual(tema.colores['ambar'], '#CCA030')
        self.assertEqual(otro.colores['ambar'], '#D49A28')
        self.assertEqual(tema.colores['rojo'], otro.colores['rojo'])
        self.assertEqual(tema.tipografia['interfaz']['familia'], 'Segoe UI')
        self.assertEqual(tema.tipografia['interfaz']['tamano_px'], 20)
        self.assertEqual(tema.tipografia['titulo'], otro.tipografia['titulo'])
        self.assertEqual(tema.geometria['flecha']['width'], 7)
        self.assertEqual(tema.geometria['flecha']['arrowshape'], [14, 18, 6])
        self.assertEqual(tema.geometria['flecha']['ancho_trazo_s'], 0.07)
        self.assertEqual(tema.estilos_marcas['seleccion'], estilos['seleccion'])
        tema.geometria['flecha']['arrowshape'][0] = 99
        tema.tipografia['interfaz']['alternativas'].append('Georgia')
        tema.colores['ambar'] = '#000000'
        self.assertEqual(geometria['flecha']['arrowshape'], [14, 18, 6])
        self.assertEqual(tipografia['interfaz']['alternativas'], ['Arial'])
        self.assertEqual(colores, {'ambar': '#CCA030'})
        self.assertEqual(otro.geometria['flecha']['arrowshape'], [12, 16, 5])
        self.assertIsNot(tema.piezas['rey', Color.Blanco, 'normal'],
                         otro.piezas['rey', Color.Blanco, 'normal'])

    def test_flecha_estrategica_utiliza_color_predeterminado_o_personalizado(self):
        for colores, esperado in (({}, '#2C455B'),
                                  ({'flecha_estrategica': '#405C70'}, '#405C70')):
            with self.subTest(colores=colores):
                tema = cargar_tema(self.ventana, colores=colores)
                self.assertEqual(tema.colores['flecha_estrategica'], esperado)
                self.assertEqual(tema.colores['azul'], '#2563A6')
                casillero = Casillero(self.ventana, tema, distribucion={})
                try:
                    casillero.aplicar_flecha((0, 0), (2, 0), 'flecha_estrategica')
                    flecha, = casillero.canvas.find_withtag('flecha')
                    self.assertEqual(casillero.canvas.itemcget(flecha, 'fill'), esperado)
                finally:
                    casillero.contenedor.destroy()
        self.assertEqual(colores, {'flecha_estrategica': '#405C70'})
        self.assertEqual(cargar_tema(self.ventana).colores['flecha_estrategica'], '#2C455B')

    def test_color_flecha_seleccionada_cambia_solo_el_relleno(self):
        clave = 'flecha_estrategica_seleccionada'
        for colores, esperado in (({}, '#527FA7'), ({clave: '#7498B8'}, '#7498B8')):
            tema = cargar_tema(self.ventana, colores=colores)
            for recorrido in ((30, 450, 30, 330), (30, 450, 30, 330, 90, 330)):
                with self.subTest(colores=colores, recorrido=recorrido):
                    canvas = tk.Canvas(self.ventana)
                    try:
                        flecha = canvas.create_line(
                            *recorrido, arrow='last', tags='flecha',
                            fill=tema.colores['flecha_estrategica'],
                            width=tema.geometria['flecha']['width'],
                            arrowshape=tema.geometria['flecha']['arrowshape'],
                        )
                        coordenadas = canvas.coords(flecha)
                        geometria = {opcion: canvas.itemcget(flecha, opcion)
                                     for opcion in ('width', 'arrowshape')}
                        canvas.itemconfigure(flecha, fill=tema.colores[clave])
                        self.assertEqual(canvas.itemcget(flecha, 'fill'), esperado)
                        self.assertEqual(canvas.coords(flecha), coordenadas)
                        self.assertEqual(canvas.find_withtag('flecha'), (flecha,))
                        for opcion, valor in geometria.items():
                            self.assertEqual(canvas.itemcget(flecha, opcion), valor)
                        canvas.itemconfigure(flecha, fill=tema.colores['flecha_estrategica'])
                        self.assertEqual(canvas.itemcget(flecha, 'fill'), '#2C455B')
                    finally:
                        canvas.destroy()
        self.assertEqual(colores, {clave: '#7498B8'})
        self.assertEqual(cargar_tema(self.ventana).colores[clave], '#527FA7')

    def test_cambiar_solo_grosor_conserva_punta_a_la_escala_elegida(self):
        tema = cargar_tema(self.ventana, dimension_casilla=120,
                           geometria={'flecha': {'width': 11}})
        self.assertEqual(tema.geometria['flecha']['width'], 11)
        self.assertEqual(tema.geometria['flecha']['arrowshape'], [24, 32, 10])

    def test_imagenes_se_asocian_al_master_indicado(self):
        otra_ventana = tk.Tk()
        otra_ventana.withdraw()
        try:
            tema = cargar_tema(otra_ventana)
            self.assertIs(tema.marcas['jaque'].tk, otra_ventana.tk)
            self.assertIsNot(tema.marcas['jaque'].tk, self.ventana.tk)
            del tema
        finally:
            otra_ventana.destroy()

    def test_integracion_casillero_y_jaque_con_imagenes_reales(self):
        tema = cargar_tema(self.ventana)
        sesion = SesionLocal(AsignacionColores(ModalidadAsignacion.BLANCO_NEGRO))
        casillero = Casillero(self.ventana, tema, tamanno_casilla=tema.dimension_casillas)
        try:
            interfaz = InterfazPartida(sesion, casillero)
            self.assertEqual(len(casillero.canvas.find_withtag('pieza')), 32)
            def clic(casilla):
                columna = ord(casilla[0]) - ord('a')
                fila = int(casilla[1]) - 1
                interfaz.gestionar_clic_izquierdo(
                    SimpleNamespace(x=columna * 60 + 30, y=(7 - fila) * 60 + 30))
            for movimiento in ('e2e4', 'f7f6', 'd1h5'):
                clic(movimiento[:2])
                clic(movimiento[2:])
            self.assertIn('marca:jaque', casillero.casillas[7, 4].ids_elementos_por_clave)
            interfaz.aplicar_opciones_visuales(OpcionesVisuales(
                modo_resaltado_jaque=ModoResaltadoJaque.REY_Y_ATACANTES))
            self.assertIn('marca:atacante_jaque', casillero.casillas[4, 7].ids_elementos_por_clave)
            clic('g7')
            clic('g6')
            self.assertFalse(casillero.canvas.find_withtag('marca:jaque'))
            self.assertFalse(casillero.canvas.find_withtag('marca:atacante_jaque'))
            casillero.aplicar_flecha((0, 0), (2, 0), 'rojo')
            flecha, = casillero.canvas.find_withtag('flecha')
            self.assertEqual(float(casillero.canvas.itemcget(flecha, 'width')), 4)
        finally:
            casillero.contenedor.destroy()


if __name__ == '__main__':
    unittest.main()
