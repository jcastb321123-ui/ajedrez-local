"""Claves de distribución; las casillas conservan el orden fijado por Tablero."""
import pickle
import unittest

from ajedrez.piezas import Caballo, Color, Torre
from ajedrez.tablero import Tablero


class PruebasClaveDistribucion(unittest.TestCase):
    def test_tableros_independientes_equivalentes_tienen_la_misma_clave(self):
        primero, segundo = Tablero(), Tablero()
        self.assertIsNot(primero.pieza_en((0, 0)), segundo.pieza_en((0, 0)))
        clave = primero.obtener_clave_distribucion()
        self.assertEqual(clave, segundo.obtener_clave_distribucion())
        self.assertIsInstance(clave, tuple)
        self.assertEqual(len(clave), 32)
        self.assertEqual(clave[0], ((0, 0), Torre, Color.Blanco))
        self.assertEqual({clave: 'inicial'}[segundo.obtener_clave_distribucion()], 'inicial')

    def test_mover_y_volver_cambia_y_recupera_la_clave(self):
        tablero = Tablero()
        inicial = tablero.obtener_clave_distribucion()
        tablero.trasladar_pieza((0, 1), (2, 2))
        self.assertNotEqual(tablero.obtener_clave_distribucion(), inicial)
        self.assertIn(((0, 1), Caballo, Color.Blanco), inicial)
        tablero.trasladar_pieza((2, 2), (0, 1))
        self.assertEqual(tablero.obtener_clave_distribucion(), inicial)

    def test_tipo_y_color_distinguen_distribuciones(self):
        for pieza in (Torre(Color.Blanco), Caballo(Color.Negro)):
            with self.subTest(tipo=type(pieza), color=pieza.color):
                tablero = Tablero()
                inicial = tablero.obtener_clave_distribucion()
                tablero.colocar(pieza, (0, 1))
                self.assertNotEqual(tablero.obtener_clave_distribucion(), inicial)

    def test_consulta_no_muta_el_tablero_y_omite_casillas_vacias(self):
        tablero = Tablero()
        for posicion in tablero.casillas:
            tablero.colocar(None, posicion)
        self.assertEqual(tablero.obtener_clave_distribucion(), ())
        tablero.colocar(Caballo(Color.Negro), (5, 2))
        antes = pickle.dumps(tablero)
        self.assertEqual(tablero.obtener_clave_distribucion(),
                         (((5, 2), Caballo, Color.Negro),))
        self.assertEqual(pickle.dumps(tablero), antes)



if __name__ == '__main__':
    unittest.main(verbosity=2)
