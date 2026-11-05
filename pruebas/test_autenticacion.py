import unittest

from ajedrez.autenticacion import AutenticadorJugadores


class PruebasAutenticadorJugadores(unittest.TestCase):
    def setUp(self) -> None:
        self.autenticador = AutenticadorJugadores[object]()
        self.blanco = object()
        self.negro = object()

    def test_clave_desconocida_no_identifica(self) -> None:
        self.assertIsNone(self.autenticador.autenticar("desconocida"))

    def test_registra_y_devuelve_la_misma_identidad(self) -> None:
        self.assertTrue(self.autenticador.registrar("clave-blanca", self.blanco))
        self.assertIs(self.autenticador.autenticar("clave-blanca"), self.blanco)

    def test_distingue_dos_jugadores(self) -> None:
        self.autenticador.registrar("clave-blanca", self.blanco)
        self.autenticador.registrar("clave-negra", self.negro)

        self.assertIs(self.autenticador.autenticar("clave-blanca"), self.blanco)
        self.assertIs(self.autenticador.autenticar("clave-negra"), self.negro)

    def test_clave_duplicada_no_sustituye_al_jugador(self) -> None:
        self.autenticador.registrar("compartida", self.blanco)

        self.assertFalse(self.autenticador.registrar("compartida", self.negro))
        self.assertIs(self.autenticador.autenticar("compartida"), self.blanco)

    def test_repetir_registro_no_crea_una_asociacion_nueva(self) -> None:
        self.autenticador.registrar("clave-blanca", self.blanco)

        self.assertFalse(self.autenticador.registrar("clave-blanca", self.blanco))
        self.assertIs(self.autenticador.autenticar("clave-blanca"), self.blanco)

    def test_clave_vacia_se_rechaza(self) -> None:
        self.assertFalse(self.autenticador.registrar("", self.blanco))
        self.assertIsNone(self.autenticador.autenticar(""))

    def test_claves_de_tipo_incorrecto_se_rechazan_silenciosamente(self) -> None:
        for clave in (None, 123, [], {}):
            with self.subTest(tipo=type(clave).__name__):
                self.assertFalse(self.autenticador.registrar(clave, self.blanco))
                self.assertIsNone(self.autenticador.autenticar(clave))

    def test_none_no_puede_ser_una_identidad(self) -> None:
        self.assertFalse(self.autenticador.registrar("sin-jugador", None))
        self.assertIsNone(self.autenticador.autenticar("sin-jugador"))
        self.assertTrue(self.autenticador.registrar("sin-jugador", self.blanco))

    def test_identidad_cero_no_se_confunde_con_ausencia(self) -> None:
        autenticador = AutenticadorJugadores[int]()

        self.assertTrue(autenticador.registrar("clave-cero", 0))
        self.assertEqual(autenticador.autenticar("clave-cero"), 0)
        self.assertIsNotNone(autenticador.autenticar("clave-cero"))

    def test_no_normaliza_la_clave(self) -> None:
        self.autenticador.registrar(" Clave Á ", self.blanco)

        self.assertIs(self.autenticador.autenticar(" Clave Á "), self.blanco)
        self.assertIsNone(self.autenticador.autenticar("Clave Á"))
        self.assertIsNone(self.autenticador.autenticar(" clave á "))

    def test_los_registros_no_se_comparten_entre_instancias(self) -> None:
        otro = AutenticadorJugadores[object]()
        self.autenticador.registrar("misma-clave", self.blanco)

        self.assertIsNone(otro.autenticar("misma-clave"))
        self.assertTrue(otro.registrar("misma-clave", self.negro))
        self.assertIs(otro.autenticar("misma-clave"), self.negro)
        self.assertIs(self.autenticador.autenticar("misma-clave"), self.blanco)

    def test_un_rechazo_no_altera_otros_registros(self) -> None:
        self.autenticador.registrar("clave-blanca", self.blanco)
        self.autenticador.registrar("clave-negra", self.negro)

        self.assertFalse(self.autenticador.registrar("", self.blanco))
        self.assertIsNone(self.autenticador.autenticar("incorrecta"))
        self.assertIs(self.autenticador.autenticar("clave-blanca"), self.blanco)
        self.assertIs(self.autenticador.autenticar("clave-negra"), self.negro)


if __name__ == "__main__":
    unittest.main()
