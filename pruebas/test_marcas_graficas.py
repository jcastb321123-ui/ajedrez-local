"""Registro, superposición y limpieza con un Canvas real en una ventana oculta.

No implementa ni prueba el ejercicio pendiente de los clics de InterfazPartida.
"""

import tkinter as tk
import unittest

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ajedrez.gráficos.graficos_tablero import Casillero
from ajedrez.gráficos.temas_graficos import ESTILOS_MARCAS, EstiloMarca, TemaGrafico
from ajedrez.piezas import Color


def crear_tema(imagen, *, estilos_marcas=None, colores=None):
    return TemaGrafico(
        identificador="prueba", dimension_casilla=60,
        casillas={"clara": imagen, "oscura": imagen},
        piezas={("peon", Color.Blanco, "normal"): imagen},
        proyecciones={("peon", Color.Blanco): imagen},
        marcas={clave: imagen for clave in (*ESTILOS_MARCAS, "personalizada")},
        flechas={}, distintivos={"atencion": imagen}, secuencias={1: imagen},
        iconos={}, fondos={}, controles={}, glifos={}, tipografia={},
        colores={"rojo": "#cc3344"} if colores is None else colores,
        geometria={}, estilos_marcas=estilos_marcas,
    )


class PruebasColoresTema(unittest.TestCase):
    def test_colores_selector_disponibles_por_defecto(self):
        for colores in ({}, {"rojo": "#cc3344"}):
            with self.subTest(colores=colores):
                tema = crear_tema(None, colores=colores)
                self.assertEqual(tema.colores["marfil"], "#FAF7EE")
                self.assertEqual(tema.colores["ambar"], "#D49A28")
                self.assertEqual(tema.colores["flecha_estrategica"], "#2C455B")
                self.assertEqual(tema.colores["flecha_estrategica_seleccionada"], "#527FA7")
                for clave, valor in colores.items():
                    self.assertEqual(tema.colores[clave], valor)

    def test_colores_recibidos_tienen_prioridad(self):
        for cambios in ({}, {"flecha_estrategica": "#405C70"},
                        {"flecha_estrategica_seleccionada": "#7498B8"}):
            with self.subTest(cambios=cambios):
                colores = {"marfil": "#EEEEEE", "ambar": "#AABBCC",
                           "rojo": "#cc3344", **cambios}
                tema = crear_tema(None, colores=colores)
                self.assertEqual(tema.colores, {
                    "flecha_estrategica": "#2C455B",
                    "flecha_estrategica_seleccionada": "#527FA7",
                    **colores,
                })

    def test_colores_no_modifican_entrada_ni_otros_temas(self):
        colores = {"rojo": "#cc3344"}
        tema = crear_tema(None, colores=colores)
        otro = crear_tema(None, colores=colores)
        self.assertEqual(colores, {"rojo": "#cc3344"})
        self.assertIsNot(tema.colores, colores)
        self.assertIsNot(tema.colores, otro.colores)
        tema.colores["ambar"] = "#AABBCC"
        self.assertEqual(otro.colores["ambar"], "#D49A28")
        self.assertEqual(colores, {"rojo": "#cc3344"})


class PruebasEstilosMarcas(unittest.TestCase):
    def test_clasificacion_separa_capa_y_finalidad(self):
        tema = crear_tema(None)
        self.assertEqual(tema.estilos_marcas["seleccion"], EstiloMarca("marca", "seleccion"))
        for clave in ("jaque", "ultima_jugada_origen", "ultima_jugada_destino", "promocion_pendiente"):
            self.assertEqual(tema.estilos_marcas[clave], EstiloMarca("resaltado", "estado"))
        for clave in ("destino_legal", "captura_legal"):
            self.assertEqual(tema.estilos_marcas[clave], EstiloMarca("marca", "estado"))
        for color in ("rojo", "azul", "verde", "ambar"):
            self.assertEqual(tema.estilos_marcas[f"fondo_{color}"], EstiloMarca("resaltado", "estrategia"))
            self.assertEqual(tema.estilos_marcas[f"circulo_{color}"], EstiloMarca("marca", "estrategia"))
        for clave in ("foco", "atencion", "personalizada"):
            self.assertEqual(tema.estilos_marcas[clave], EstiloMarca("marca", "estrategia"))

    def test_personalizacion_no_modifica_otros_temas_ni_geometria(self):
        configuracion = {"seleccion": EstiloMarca("resaltado", "seleccion")}
        tema = crear_tema(None, estilos_marcas=configuracion)
        otro = crear_tema(None)
        configuracion.clear()
        self.assertEqual(tema.estilos_marcas["seleccion"].capa, "resaltado")
        self.assertEqual(otro.estilos_marcas["seleccion"].capa, "marca")
        self.assertIsNot(tema.estilos_marcas, otro.estilos_marcas)
        self.assertEqual(tema.geometria["flecha"], {"width": 4.0, "arrowshape": [12.0, 16.0, 5.0]})


class PruebasCoordenadasLogicas(unittest.TestCase):
    def setUp(self):
        self.casillero = object.__new__(Casillero)
        self.casillero._tamanno_casilla = 60

    def test_coordenadas_interiores(self):
        casos = {
            (0, 0): (7, 0),
            (479, 0): (7, 7),
            (0, 479): (0, 0),
            (479.9, 479.9): (0, 7),
            (60, 60): (6, 1),
        }
        for coordenadas, esperadas in casos.items():
            with self.subTest(coordenadas=coordenadas):
                self.assertEqual(
                    self.casillero.obtener_coordenadas_logicas(coordenadas),
                    esperadas,
                )

    def test_rechaza_limite_y_exterior_en_ambas_componentes(self):
        for componente in (-1, -0.1, 480, 483, 1000):
            for coordenadas in ((componente, 30), (30, componente)):
                with self.subTest(coordenadas=coordenadas):
                    self.assertIsNone(
                        self.casillero.obtener_coordenadas_logicas(coordenadas)
                    )

    def test_limites_se_adaptan_al_tamanno_de_casilla(self):
        for tamanno in (60, 120, 240):
            self.casillero._tamanno_casilla = tamanno
            limite = 8 * tamanno
            with self.subTest(tamanno=tamanno):
                self.assertEqual(
                    self.casillero.obtener_coordenadas_logicas((limite - 1, limite - 1)),
                    (0, 7),
                )
                self.assertIsNone(self.casillero.obtener_coordenadas_logicas((limite, 0)))
                self.assertIsNone(self.casillero.obtener_coordenadas_logicas((0, limite)))


class PruebasMarcasCanvas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ventana = tk.Tk()
        except tk.TclError as error:
            raise unittest.SkipTest(f"Tk no disponible: {error}") from error
        cls.ventana.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.ventana.destroy()

    def setUp(self):
        self.imagen = tk.PhotoImage(master=self.ventana, width=60, height=60)
        self.tema = crear_tema(self.imagen)
        self.posicion = (1, 4)
        self.casillero = Casillero(self.ventana, self.tema,
                                  distribucion={self.posicion: ("peon", Color.Blanco, "normal")})
        self.canvas = self.casillero.canvas
        self.casilla = self.casillero.casillas[self.posicion]
        self.fondos = {c.id_imagen for c in self.casillero.casillas.values()}
        self.pieza = self.casilla.id_pieza

    def tearDown(self):
        self.casillero.contenedor.destroy()

    def aplicar(self, clave):
        self.casillero.aplicar_marca(self.posicion, clave)
        return self.casilla.ids_elementos_por_clave[f"marca:{clave}"]

    def comprobar_reemplazo_anotacion(self, aplicar, obtener_id):
        aplicar()
        id_anterior = obtener_id()
        self.assertEqual(self.casillero.anotaciones_estrategicas, [id_anterior])
        self.casillero.aplicar_flecha((1, 2), (3, 2), "flecha_estrategica")
        id_flecha = self.casillero.anotaciones_estrategicas[-1]
        aplicar()
        id_nuevo = obtener_id()
        self.assertNotEqual(id_nuevo, id_anterior)
        self.assertIsNone(self.canvas.type(id_anterior))
        self.assertEqual(self.canvas.type(id_nuevo), "image")
        self.assertEqual(self.canvas.type(id_flecha), "line")
        self.assertEqual(self.casillero.anotaciones_estrategicas, [id_flecha, id_nuevo])
        self.assertTrue(all(type(identificador) is int
                            for identificador in self.casillero.anotaciones_estrategicas))
        self.comprobar_registros()

    def test_reemplazo_marca_actualiza_registro_sin_tocar_otras_anotaciones(self):
        self.comprobar_reemplazo_anotacion(
            lambda: self.casillero.aplicar_marca(self.posicion, "fondo_azul"),
            lambda: self.casilla.ids_elementos_por_clave["marca:fondo_azul"],
        )

    def test_reemplazo_proyeccion_actualiza_registro_sin_tocar_otras_anotaciones(self):
        self.comprobar_reemplazo_anotacion(
            lambda: self.casillero.aplicar_proyeccion(self.posicion, ("peon", Color.Blanco)),
            lambda: self.casilla.id_proyeccion,
        )

    def test_reemplazo_distintivo_actualiza_registro_sin_tocar_otras_anotaciones(self):
        self.comprobar_reemplazo_anotacion(
            lambda: self.casillero.aplicar_distintivo(self.posicion, "atencion"),
            lambda: self.casilla.id_distintivo,
        )

    def test_reemplazo_secuencia_actualiza_registro_sin_tocar_otras_anotaciones(self):
        self.comprobar_reemplazo_anotacion(
            lambda: self.casillero.aplicar_marcador_de_secuencia(self.posicion, 1),
            lambda: self.casilla.id_marcador_de_secuencia,
        )

    def comprobar_reemplazo_marca_no_estrategica(self, clave):
        # Cada clave conserva su uso durante toda la secuencia.
        self.casillero.aplicar_flecha((1, 2), (3, 2), "flecha_estrategica")
        id_flecha = self.casillero.anotaciones_estrategicas[-1]
        id_anterior = self.aplicar(clave)
        id_nuevo = self.aplicar(clave)
        self.assertNotEqual(id_anterior, id_nuevo)
        self.assertIsNone(self.canvas.type(id_anterior))
        self.assertEqual(self.canvas.type(id_nuevo), "image")
        self.assertEqual(self.casillero.anotaciones_estrategicas, [id_flecha])
        self.comprobar_registros()

    def test_reemplazo_marca_estado_no_altera_registro_estrategico(self):
        self.comprobar_reemplazo_marca_no_estrategica("jaque")

    def test_reemplazo_marca_seleccion_no_altera_registro_estrategico(self):
        self.comprobar_reemplazo_marca_no_estrategica("seleccion")

    def test_aplicar_elemento_devuelve_nuevo_y_anterior_con_y_sin_clave(self):
        for capa, clave in (("proyeccion", None), ("marca", "auxiliar:prueba")):
            with self.subTest(capa=capa, clave=clave):
                primero, anterior = self.casilla.aplicar_elemento(
                    self.imagen, capa, clave_elemento=clave,
                )
                self.assertIsInstance(primero, int)
                self.assertIsNone(anterior)
                segundo, sustituido = self.casilla.aplicar_elemento(
                    self.imagen, capa, clave_elemento=clave,
                )
                self.assertEqual(sustituido, primero)
                self.assertNotEqual(segundo, primero)
                self.assertIsNone(self.canvas.type(primero))
                self.assertEqual(self.canvas.type(segundo), "image")
        self.comprobar_registros()

    def test_obtener_casilla_localiza_imagenes_con_y_sin_clave(self):
        self.assertIs(self.casillero.obtener_casilla(self.pieza), self.casilla)
        for posicion in ((0, 0), (3, 6), (7, 7)):
            casilla = self.casillero.casillas[posicion]
            with self.subTest(posicion=posicion):
                self.assertIs(self.casillero.obtener_casilla(casilla.id_imagen), casilla)
                self.casillero.aplicar_marca(posicion, "fondo_azul")
                id_marca = casilla.ids_elementos_por_clave["marca:fondo_azul"]
                self.assertIs(self.casillero.obtener_casilla(id_marca), casilla)
                for capa in ("pieza", "resaltado", "marca", "proyeccion", "distintivo", "secuencia"):
                    id_imagen, _ = casilla.aplicar_elemento(self.imagen, capa)
                    self.assertIs(self.casillero.obtener_casilla(id_imagen), casilla)
        self.comprobar_registros()

    def test_obtener_casilla_devuelve_none_para_ids_sin_imagen_registrada(self):
        id_borrado = self.aplicar("fondo_azul")
        self.casillero.borrar_marca(self.posicion, "fondo_azul")
        self.casillero.aplicar_flecha((1, 2), (3, 2), "flecha_estrategica")
        id_flecha = self.casillero.anotaciones_estrategicas[-1]
        id_texto = self.canvas.create_text(30, 30, text="prueba")
        for id_elemento in (id_borrado, id_flecha, id_texto, 999999):
            with self.subTest(id_elemento=id_elemento):
                self.assertIsNone(self.casillero.obtener_casilla(id_elemento))

    def agregar_otros_elementos(self):
        self.casillero.aplicar_proyeccion(self.posicion, ("peon", Color.Blanco))
        self.casillero.aplicar_distintivo(self.posicion, "atencion")
        self.casillero.aplicar_marcador_de_secuencia(self.posicion, 1)
        self.casillero.aplicar_flecha((1, 2), (3, 3), "rojo")
        return next(iter(self.casillero.casillas[(1, 2)].ids_flechas))

    def comprobar_registros(self):
        existentes = set(self.canvas.find_all())
        for casilla in self.casillero.casillas.values():
            self.assertIs(casilla.capas[2], casilla.variables_id["resaltado"])
            self.assertIs(casilla.capas[5], casilla.variables_id["marca"])
            for clave_elemento, id_elemento in casilla.ids_elementos_por_clave.items():
                self.assertIn(id_elemento, existentes)
                etiquetas_dibujo = self.canvas.gettags(id_elemento)
                if clave_elemento.startswith("marca:"):
                    self.assertIn(clave_elemento, etiquetas_dibujo)
                self.assertEqual(
                    sum(elementos.count(id_elemento) for elementos in casilla.variables_id.values()),
                    1,
                )
                for etiqueta_capa, ids_capa in casilla.variables_id.items():
                    if id_elemento in ids_capa:
                        self.assertIn(etiqueta_capa, etiquetas_dibujo)
            for elementos in casilla.capas.values():
                for id in elementos:
                    if id is not None:
                        self.assertIn(id, existentes)

    def crear_flecha_para_prueba_de_resaltado(self, *, caballo=False):
        # Aisla el resaltado del getter del registro cronológico, aún en desarrollo.
        origen = (1, 4)
        destino = (3, 5) if caballo else (3, 4)
        recorrido = (270, 390, 270, 270, 330, 270) if caballo else (270, 390, 270, 270)
        flecha = self.canvas.create_line(
            *recorrido, arrow="last", tags="flecha",
            fill=self.tema.colores["flecha_estrategica"],
            width=self.tema.geometria["flecha"]["width"],
            arrowshape=self.tema.geometria["flecha"]["arrowshape"],
        )
        self.casillero._aplicar_flecha_a_casillas(origen, destino, flecha)
        self.casillero._anotaciones_estrategicas.append(flecha)
        self.casillero._ordenar_capas()
        return flecha

    def test_alternar_resaltado_flecha_conserva_dibujo_geometria_y_registros(self):
        for caballo in (False, True):
            with self.subTest(caballo=caballo):
                flecha = self.crear_flecha_para_prueba_de_resaltado(caballo=caballo)
                dibujos = self.canvas.find_all()
                coordenadas = self.canvas.coords(flecha)
                geometria = {opcion: self.canvas.itemcget(flecha, opcion)
                             for opcion in ("width", "arrowshape", "arrow")}
                referencias = {posicion: set(casilla.ids_flechas)
                               for posicion, casilla in self.casillero.casillas.items()}
                orden_anotaciones = list(self.casillero._anotaciones_estrategicas)
                for seleccionada in (True, False, True, False):
                    self.casillero.alternar_resaltado_flecha(flecha)
                    clave = "flecha_estrategica_seleccionada" if seleccionada else "flecha_estrategica"
                    self.assertEqual(self.canvas.itemcget(flecha, "fill"), self.tema.colores[clave])
                    self.assertEqual("flecha_seleccionada" in self.canvas.gettags(flecha), seleccionada)
                    self.assertEqual(self.canvas.find_all(), dibujos)
                    self.assertEqual(self.canvas.coords(flecha), coordenadas)
                    for opcion, valor in geometria.items():
                        self.assertEqual(self.canvas.itemcget(flecha, opcion), valor)
                    self.assertEqual(self.casillero._anotaciones_estrategicas, orden_anotaciones)
                    self.assertEqual(
                        {posicion: set(casilla.ids_flechas)
                         for posicion, casilla in self.casillero.casillas.items()}, referencias)
                    self.comprobar_registros()

    def test_alternar_resaltado_flecha_respeta_colores_personalizados(self):
        for normal, seleccionado in (("#405C70", "#7498B8"), ("#405C70", "#405C70")):
            with self.subTest(normal=normal, seleccionado=seleccionado):
                self.tema.colores["flecha_estrategica"] = normal
                self.tema.colores["flecha_estrategica_seleccionada"] = seleccionado
                flecha = self.crear_flecha_para_prueba_de_resaltado()
                self.casillero.alternar_resaltado_flecha(flecha)
                self.assertEqual(self.canvas.itemcget(flecha, "fill"), seleccionado)
                self.assertIn("flecha_seleccionada", self.canvas.gettags(flecha))
                self.casillero.alternar_resaltado_flecha(flecha)
                self.assertEqual(self.canvas.itemcget(flecha, "fill"), normal)
                self.assertNotIn("flecha_seleccionada", self.canvas.gettags(flecha))

    def test_alternar_resaltado_flecha_solo_afecta_al_id_indicado(self):
        primera = self.crear_flecha_para_prueba_de_resaltado()
        segunda = self.crear_flecha_para_prueba_de_resaltado(caballo=True)
        self.casillero.alternar_resaltado_flecha(primera)
        self.assertEqual(self.canvas.itemcget(segunda, "fill"), self.tema.colores["flecha_estrategica"])
        self.assertNotIn("flecha_seleccionada", self.canvas.gettags(segunda))
        self.casillero.alternar_resaltado_flecha(segunda)
        self.casillero.alternar_resaltado_flecha(primera)
        self.assertEqual(self.canvas.find_withtag("flecha_seleccionada"), (segunda,))

    def test_alternar_resaltado_flecha_ignora_ids_ajenos_o_borrados(self):
        flecha = self.crear_flecha_para_prueba_de_resaltado()
        self.casillero.borrar_flecha(flecha)
        linea_sin_etiqueta = self.canvas.create_line(0, 0, 30, 30, fill="#123456")
        dibujos = self.canvas.find_all()
        for id_elemento in (flecha, 999999, self.pieza, self.casilla.id_imagen, linea_sin_etiqueta):
            with self.subTest(id_elemento=id_elemento):
                self.casillero.alternar_resaltado_flecha(id_elemento)
                self.assertEqual(self.canvas.find_all(), dibujos)
                self.assertFalse(self.canvas.find_withtag("flecha_seleccionada"))
        self.assertEqual(self.canvas.itemcget(linea_sin_etiqueta, "fill"), "#123456")

    def test_borrar_flecha_actualiza_registro_y_conserva_la_otra(self):
        self.casillero.aplicar_flecha((1, 2), (3, 2), "flecha_estrategica")
        primera = self.casillero.anotaciones_estrategicas[-1]
        self.casillero.aplicar_flecha((1, 2), (4, 2), "flecha_estrategica")
        segunda = self.casillero.anotaciones_estrategicas[-1]
        self.casillero.borrar_flecha(primera)
        self.assertIsNone(self.canvas.type(primera))
        self.assertEqual(self.canvas.type(segunda), "line")
        self.assertEqual(self.casillero.anotaciones_estrategicas, [segunda])
        self.assertFalse(any(primera in casilla.ids_flechas
                             for casilla in self.casillero.casillas.values()))
        self.comprobar_registros()

    def test_borrar_todas_flechas_retira_registro_y_conserva_proyeccion(self):
        self.casillero.aplicar_proyeccion(self.posicion, ("peon", Color.Blanco))
        proyeccion = self.casilla.id_proyeccion
        for destino in ((3, 2), (4, 2)):
            self.casillero.aplicar_flecha((1, 2), destino, "flecha_estrategica")
        flechas = tuple(self.canvas.find_withtag("flecha"))
        self.casillero._borrar_todas_las_flechas()
        for flecha in flechas:
            self.assertIsNone(self.canvas.type(flecha))
        self.assertTrue(all(not casilla.ids_flechas
                            for casilla in self.casillero.casillas.values()))
        self.assertEqual(self.canvas.type(proyeccion), "image")
        self.assertEqual(self.casillero.anotaciones_estrategicas, [proyeccion])
        self.comprobar_registros()

    def test_limpieza_temporal_vacia_registro_sin_borrar_seleccion(self):
        seleccion = self.aplicar("seleccion")
        self.casillero.aplicar_proyeccion(self.posicion, ("peon", Color.Blanco))
        self.casillero.aplicar_flecha((1, 2), (3, 2), "flecha_estrategica")
        self.casillero.limpiar_anotaciones_temporales()
        self.assertEqual(self.canvas.type(seleccion), "image")
        self.assertFalse(self.canvas.find_withtag("flecha"))
        self.assertEqual(self.casillero.anotaciones_estrategicas, [])
        self.comprobar_registros()

    def test_seleccion_unica_sin_borrar_las_anotaciones(self):
        fondo = self.aplicar("fondo_verde")
        anterior = self.aplicar("seleccion")
        destino = (6, 4)
        self.casillero.aplicar_seleccion(destino)
        self.assertNotIn("marca:seleccion", self.casilla.ids_elementos_por_clave)
        self.assertIn("marca:seleccion", self.casillero.casillas[destino].ids_elementos_por_clave)
        self.assertEqual(self.canvas.type(anterior), None)
        self.assertEqual(self.canvas.type(fondo), "image")
        self.casillero.borrar_seleccion()
        self.casillero.borrar_seleccion()
        self.assertEqual(set(self.canvas.find_all()), self.fondos | {self.pieza, fondo})
        self.comprobar_registros()

    def test_marcas_de_la_misma_capa_coexisten_y_solo_se_reemplaza_su_clave(self):
        ids = {clave: self.aplicar(clave) for clave in ESTILOS_MARCAS}
        self.assertEqual(len(self.casilla.ids_elementos_por_clave), len(ESTILOS_MARCAS))
        self.assertTrue(self.casilla.resaltada())
        reemplazo = self.aplicar("fondo_rojo")
        self.assertNotEqual(ids["fondo_rojo"], reemplazo)
        self.assertIsNone(self.canvas.type(ids.pop("fondo_rojo")))
        for clave, id in ids.items():
            self.assertEqual(self.casilla.ids_elementos_por_clave[f"marca:{clave}"], id)
        self.comprobar_registros()

    def test_borrado_por_clave_y_por_id_mantiene_registros_sin_tocar_otras_marcas(self):
        seleccion = self.aplicar("seleccion")
        self.aplicar("fondo_rojo")
        circulo = self.aplicar("circulo_rojo")
        self.casillero.borrar_marca(self.posicion, "fondo_rojo")
        self.casillero.borrar_marca(self.posicion, "fondo_rojo")
        self.casillero.borrar_elemento(self.posicion, circulo)
        self.assertEqual(self.casilla.ids_elementos_por_clave, {"marca:seleccion": seleccion})
        self.assertFalse(self.casilla.resaltada())
        self.assertEqual(self.casillero.anotaciones_estrategicas, [])
        self.comprobar_registros()

    def test_limpieza_estrategica_conserva_seleccion_indicadores_y_piezas(self):
        conservados = {self.aplicar(clave) for clave in
                      ("seleccion", "jaque", "ultima_jugada_destino", "destino_legal")}
        for clave in ("fondo_verde", "circulo_rojo", "atencion"):
            self.aplicar(clave)
        flecha = self.agregar_otros_elementos()
        self.casillero.limpiar_anotaciones_temporales()
        self.casillero.limpiar_anotaciones_temporales()
        self.assertEqual(set(self.canvas.find_all()), self.fondos | {self.pieza} | conservados)
        self.assertIsNone(self.canvas.type(flecha))
        self.assertIsNone(self.casilla.id_proyeccion)
        self.assertIsNone(self.casilla.id_distintivo)
        self.assertIsNone(self.casilla.id_marcador_de_secuencia)
        self.assertTrue(all(not c.ids_flechas for c in self.casillero.casillas.values()))
        self.assertEqual(self.casillero.anotaciones_estrategicas, [])
        self.comprobar_registros()

    def test_limpieza_de_indicadores_no_toca_seleccion_ni_estrategia(self):
        conservados = {self.aplicar(clave) for clave in ("seleccion", "fondo_azul", "circulo_ambar")}
        for clave in ("jaque", "ultima_jugada_origen", "promocion_pendiente", "captura_legal"):
            self.aplicar(clave)
        self.casillero.limpiar_marcas(uso="estado")
        self.assertEqual(set(self.canvas.find_all()), self.fondos | {self.pieza} | conservados)
        self.comprobar_registros()

    def test_limpiar_todas_las_marcas_no_borra_otros_elementos(self):
        for clave in ("seleccion", "fondo_azul", "jaque"):
            self.aplicar(clave)
        self.agregar_otros_elementos()
        otros = set(self.canvas.find_all()) - set(self.casilla.ids_elementos_por_clave.values())
        anotaciones_conservadas = [
            identificador for identificador in self.casillero.anotaciones_estrategicas
            if identificador in otros
        ]
        self.casillero.limpiar_marcas()
        self.assertEqual(set(self.canvas.find_all()), otros)
        self.assertEqual(self.casilla.ids_elementos_por_clave, {})
        self.assertEqual(self.casillero.anotaciones_estrategicas, anotaciones_conservadas)
        self.comprobar_registros()

    def test_limpieza_total_deja_solo_las_64_casillas_y_vacia_los_registros(self):
        for clave in ESTILOS_MARCAS:
            self.aplicar(clave)
        self.agregar_otros_elementos()
        self.casillero.limpiar_casillero()
        self.casillero.limpiar_casillero()
        self.assertEqual(set(self.canvas.find_all()), self.fondos)
        self.assertEqual(self.casillero.anotaciones_estrategicas, [])
        for casilla in self.casillero.casillas.values():
            self.assertEqual(casilla.ids_elementos_por_clave, {})
            self.assertEqual(casilla.ids_flechas, set())
            for clave, elementos in casilla.variables_id.items():
                if clave != "imagen":
                    self.assertEqual(elementos, [None])
        self.comprobar_registros()

    def test_mostrar_posicion_retira_toda_seleccion_y_anotacion(self):
        for clave in ("seleccion", "fondo_rojo", "jaque"):
            self.aplicar(clave)
        destino = (3, 4)
        self.casillero.mostrar_posicion({destino: ("peon", Color.Blanco, "normal")})
        nueva_pieza = self.casillero.casillas[destino].id_pieza
        self.assertEqual(set(self.canvas.find_all()), self.fondos | {nueva_pieza})
        self.assertIsNone(self.casilla.id_pieza)
        self.assertIsNone(self.canvas.type(self.pieza))
        self.assertEqual(self.casillero.anotaciones_estrategicas, [])
        self.assertTrue(all(not c.ids_elementos_por_clave for c in self.casillero.casillas.values()))
        self.comprobar_registros()

    def test_las_finalidades_no_alteran_el_orden_de_capas(self):
        seleccion = self.aplicar("seleccion")
        flecha = self.agregar_otros_elementos()
        fondo = self.aplicar("fondo_rojo")
        jaque = self.aplicar("jaque")
        orden = list(self.canvas.find_all())
        posicion = orden.index
        self.assertLess(max(map(posicion, self.fondos)), posicion(fondo))
        self.assertLess(posicion(fondo), posicion(self.pieza))
        self.assertLess(posicion(jaque), posicion(self.pieza))
        self.assertLess(posicion(self.pieza), posicion(self.casilla.id_proyeccion))
        self.assertLess(posicion(self.casilla.id_proyeccion), posicion(seleccion))
        self.assertLess(posicion(seleccion), posicion(flecha))
        self.assertLess(posicion(flecha), posicion(self.casilla.id_distintivo))
        self.assertLess(posicion(self.casilla.id_distintivo), posicion(self.casilla.id_marcador_de_secuencia))

    def test_cambio_de_capa_del_tema_no_cambia_la_finalidad_de_limpieza(self):
        anterior = self.aplicar("seleccion")
        self.tema.estilos_marcas["seleccion"] = EstiloMarca("resaltado", "seleccion")
        nuevo = self.aplicar("seleccion")
        self.assertIsNone(self.canvas.type(anterior))
        self.assertNotIn(nuevo, self.casilla.capas[5])
        self.assertIn(nuevo, self.casilla.capas[2])
        self.assertTrue(self.casilla.resaltada())
        self.casillero.limpiar_anotaciones_temporales()
        self.assertEqual(self.casilla.ids_elementos_por_clave["marca:seleccion"], nuevo)
        self.casillero.borrar_seleccion()
        self.assertFalse(self.casilla.resaltada())
        self.comprobar_registros()

    def test_elementos_genericos_anteriores_siguen_funcionando(self):
        seleccion = self.aplicar("seleccion")
        for capa in ("marca", "resaltado"):
            self.casilla.aplicar_elemento(self.imagen, capa)
            anterior = self.casilla.variables_id[capa][0]
            self.casilla.aplicar_elemento(self.imagen, capa)
            self.assertIsNone(self.canvas.type(anterior))
        self.assertIsNotNone(self.casilla.id_marca)
        self.assertIsNotNone(self.casilla.id_resaltado)
        self.casillero.limpiar_anotaciones_temporales()
        self.assertIsNone(self.casilla.id_marca)
        self.assertIsNone(self.casilla.id_resaltado)
        self.assertEqual(self.casilla.ids_elementos_por_clave, {"marca:seleccion": seleccion})
        self.comprobar_registros()

    def test_aplicacion_sin_clave_conserva_getters_listas_y_anclaje(self):
        listas_originales = dict(self.casilla.variables_id)
        capas_originales = dict(self.casilla.capas)
        seleccion = self.aplicar("seleccion")
        propiedades_por_capa = {
            "pieza": "id_pieza",
            "proyeccion": "id_proyeccion",
            "distintivo": "id_distintivo",
            "secuencia": "id_marcador_de_secuencia",
            "marca": "id_marca",
            "resaltado": "id_resaltado",
        }
        for etiqueta_capa, nombre_propiedad in propiedades_por_capa.items():
            with self.subTest(capa=etiqueta_capa):
                self.casilla.aplicar_elemento(self.imagen, etiqueta_capa)
                id_anterior = getattr(self.casilla, nombre_propiedad)
                resultado = self.casilla.aplicar_elemento(self.imagen, etiqueta_capa)
                id_nuevo = getattr(self.casilla, nombre_propiedad)
                self.assertEqual(resultado, (id_nuevo, id_anterior))
                self.assertNotEqual(id_anterior, id_nuevo)
                self.assertIsNone(self.canvas.type(id_anterior))
                self.assertEqual(self.canvas.gettags(id_nuevo), (etiqueta_capa,))
                self.assertEqual(self.canvas.coords(id_nuevo), self.canvas.coords(self.casilla.id_imagen))
                self.assertEqual(self.canvas.itemcget(id_nuevo, "anchor"), "nw")
                self.assertEqual(self.casilla.variables_id[etiqueta_capa][0], id_nuevo)
        for categoria, lista_original in listas_originales.items():
            self.assertIs(self.casilla.variables_id[categoria], lista_original)
        for nivel, lista_original in capas_originales.items():
            self.assertIs(self.casilla.capas[nivel], lista_original)
        self.assertEqual(self.casilla.ids_elementos_por_clave, {"marca:seleccion": seleccion})
        self.comprobar_registros()

    def test_elementos_con_clave_coexisten_sin_conocer_estilos_de_marcas(self):
        self.casilla.aplicar_elemento(self.imagen, "marca")
        id_sin_clave = self.casilla.id_marca
        ids_iniciales = {}
        for clave_elemento in ("auxiliar:primero", "auxiliar:segundo"):
            self.casilla.aplicar_elemento(
                self.imagen, etiqueta_capa="marca",
                clave_elemento=clave_elemento,
                etiquetas_adicionales=("grupo:auxiliares",),
            )
            ids_iniciales[clave_elemento] = self.casilla.ids_elementos_por_clave[clave_elemento]
        for id_elemento in ids_iniciales.values():
            self.assertEqual(self.canvas.gettags(id_elemento), ("marca", "grupo:auxiliares"))
            self.assertEqual(self.canvas.coords(id_elemento), self.canvas.coords(self.casilla.id_imagen))
        self.casilla.aplicar_elemento(
            self.imagen, "marca", clave_elemento="auxiliar:primero",
            etiquetas_adicionales=("grupo:renovados",),
        )
        id_reemplazo = self.casilla.ids_elementos_por_clave["auxiliar:primero"]
        self.assertIsNone(self.canvas.type(ids_iniciales["auxiliar:primero"]))
        self.assertEqual(self.canvas.gettags(id_reemplazo), ("marca", "grupo:renovados"))
        self.assertEqual(self.casilla.id_marca, id_sin_clave)
        self.assertEqual(self.casilla.ids_elementos_por_clave["auxiliar:segundo"],
                         ids_iniciales["auxiliar:segundo"])
        self.assertEqual(len(self.casilla.variables_id["marca"]), 3)
        self.casilla.borrar_elemento(id_reemplazo)
        self.assertNotIn("auxiliar:primero", self.casilla.ids_elementos_por_clave)
        self.assertEqual(len(self.casilla.variables_id["marca"]), 2)
        self.comprobar_registros()

    def test_limpieza_de_marcas_no_borra_otras_claves_de_la_misma_capa(self):
        self.casilla.aplicar_elemento(
            self.imagen, "marca", clave_elemento="auxiliar:seleccion",
            etiquetas_adicionales=("uso:seleccion",),
        )
        id_auxiliar = self.casilla.ids_elementos_por_clave["auxiliar:seleccion"]
        id_seleccion = self.aplicar("seleccion")
        self.casillero.borrar_marca(self.posicion, "seleccion")
        self.assertIsNone(self.canvas.type(id_seleccion))
        self.assertEqual(self.canvas.type(id_auxiliar), "image")
        for uso in ("seleccion", "estrategia", "estado", None):
            self.aplicar("seleccion")
            self.aplicar("fondo_verde")
            self.aplicar("jaque")
            self.casillero.limpiar_marcas(uso=uso)
            self.assertEqual(self.canvas.type(id_auxiliar), "image")
            self.comprobar_registros()
        self.assertEqual(self.casilla.ids_elementos_por_clave, {"auxiliar:seleccion": id_auxiliar})

    def test_reemplazo_por_clave_actualiza_capa_y_etiquetas_sin_dejar_ids_antiguos(self):
        id_anterior = self.aplicar("fondo_rojo")
        id_conservado = self.aplicar("fondo_verde")
        self.tema.estilos_marcas["fondo_rojo"] = EstiloMarca("marca", "estrategia")
        id_nuevo = self.aplicar("fondo_rojo")
        self.assertIsNone(self.canvas.type(id_anterior))
        self.assertNotIn(id_anterior, self.casilla.capas[2])
        self.assertNotIn(id_nuevo, self.casilla.capas[2])
        self.assertIn(id_nuevo, self.casilla.capas[5])
        self.assertIn(id_conservado, self.casilla.capas[2])
        self.assertEqual(self.canvas.gettags(id_nuevo), ("marca", "marca:fondo_rojo", "uso:estrategia"))
        self.casillero.limpiar_marcas(uso="estrategia")
        self.assertIsNone(self.canvas.type(id_conservado))
        self.assertIsNone(self.canvas.type(id_nuevo))
        self.comprobar_registros()

    def test_limpieza_temporal_retira_elementos_con_y_sin_clave_en_cada_categoria(self):
        id_seleccion = self.aplicar("seleccion")
        id_jaque = self.aplicar("jaque")
        for etiqueta_capa in ("proyeccion", "distintivo", "secuencia"):
            self.casilla.aplicar_elemento(self.imagen, etiqueta_capa)
            self.casilla.aplicar_elemento(
                self.imagen, etiqueta_capa, clave_elemento=f"{etiqueta_capa}:alternativa",
            )
        self.casillero.limpiar_anotaciones_temporales()
        self.assertEqual(set(self.canvas.find_all()), self.fondos | {self.pieza, id_seleccion, id_jaque})
        self.assertEqual(self.casilla.ids_elementos_por_clave,
                         {"marca:seleccion": id_seleccion, "marca:jaque": id_jaque})
        for etiqueta_capa in ("proyeccion", "distintivo", "secuencia"):
            self.assertEqual(self.casilla.variables_id[etiqueta_capa], [None])
        self.comprobar_registros()

    def test_limpieza_total_tambien_elimina_elementos_con_claves_no_asociadas_a_marcas(self):
        self.casillero.aplicar_proyeccion(self.posicion, ("peon", Color.Blanco))
        self.casilla.aplicar_elemento(
            self.imagen, "proyeccion", clave_elemento="proyeccion:alternativa",
        )
        self.aplicar("seleccion")
        self.casillero.limpiar_casillero()
        self.assertEqual(set(self.canvas.find_all()), self.fondos)
        self.assertEqual(self.casilla.ids_elementos_por_clave, {})
        self.assertEqual(self.casilla.variables_id["proyeccion"], [None])
        self.comprobar_registros()

    def test_ciclos_de_seleccion_y_anotacion_no_acumulan_dibujos(self):
        for _ in range(30):
            self.casillero.aplicar_seleccion(self.posicion)
            self.aplicar("fondo_verde")
            self.aplicar("circulo_rojo")
            self.casillero.limpiar_anotaciones_temporales()
            self.casillero.borrar_seleccion()
        self.assertEqual(set(self.canvas.find_all()), self.fondos | {self.pieza})
        self.assertEqual(self.casilla.ids_elementos_por_clave, {})
        self.assertEqual(self.casilla.capas[2], [None])
        self.assertEqual(self.casilla.capas[5], [None])
        self.comprobar_registros()


if __name__ == "__main__":
    unittest.main()
