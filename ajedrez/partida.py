from __future__ import annotations
import copy
from .piezas import *
from .tablero import Tablero
from abc import ABC
from collections.abc import Callable
from enum import Enum, auto
from collections.abc import Generator

"""Precondición: Toda Jugada referenciada por Partida es una jugada cuyo estado de posición ha sido validado. El atributo "anterior" de EstadoPosicion sólo puede
referenciar un estado validado; y el atributo "anterior" de jugada sólo puede referenciar a una jugada aceptada."""

class MotivoRechazoMovimiento(Enum):
    MOVIMIENTO_INVALIDO = auto()
    REY_EN_JAQUE = auto()
    NO_AUTORIZADO = auto()
    PROMOCION_PENDIENTE = auto()
    PARTIDA_FINALIZADA = auto()

class EstadoPosicion:
    def __init__(self,
                 *,
                 jugadas_sin_captura_ni_peon: int = 0,
                 tablero: Tablero = Tablero(),
                 origen: tuple[int, int] | None = None,
                 destino: tuple[int, int] | None = None,
                 estado_anterior: EstadoPosicion | None = None):
        self._tablero = copy.deepcopy(tablero)
        if origen:
            self._pieza = self.tablero.casillas[origen]
        else:
            self._pieza = None
        self._origen = origen
        self._destino = destino
        self._estado_anterior = estado_anterior
        self._motivo_rechazo = None
        self._captura_al_paso_disponible = (
            self.tablero.posicion_de_captura_al_paso is not None
        )
        # Se establece al validar la jugada con todos sus efectos aplicados.
        if estado_anterior:
            self._movimiento_valido = False
        else:
            self._movimiento_valido = None
        if self.estado_anterior:
            self._jugadas_sin_captura_ni_peon = self.estado_anterior.jugadas_sin_captura_ni_peon
        else:
            self._jugadas_sin_captura_ni_peon = jugadas_sin_captura_ni_peon

    @property
    def tablero(self) -> Tablero:
        return self._tablero

    @property
    def pieza(self) -> Pieza | None:
        return self._pieza

    @property
    def origen(self) -> tuple[int, int] | None:
        return self._origen

    @property
    def destino(self) -> tuple[int, int] | None:
        return self._destino

    @property
    def estado_anterior(self) -> EstadoPosicion | None:
        return self._estado_anterior

    @property
    def captura_al_paso_disponible(self) -> bool:
        return self._captura_al_paso_disponible

    @property
    def movimiento_valido(self) -> bool | None:
        return self._movimiento_valido

    @movimiento_valido.setter
    def movimiento_valido(self,
                          es_valido: bool | None) -> None:
        self._movimiento_valido = es_valido

    @property
    def motivo_rechazo(self) -> MotivoRechazoMovimiento | None:
        """Diagnóstico de esta propuesta, no del estado aceptado de la partida."""
        return self._motivo_rechazo

    @property
    def jugadas_sin_captura_ni_peon(self) -> int:
        return self._jugadas_sin_captura_ni_peon

    def validar_movimiento(self,
                            condiciones_especificas: Callable[[], bool],
                            aplicar_movimiento: Callable[[], None]) -> None:
        self._motivo_rechazo = None
        rango_candidato = self.tablero.calcular_rango_candidato(self.pieza,
                                                               self.origen)
        
        if self.destino not in rango_candidato or not condiciones_especificas():
            if self._motivo_rechazo is None:
                self._motivo_rechazo = MotivoRechazoMovimiento.MOVIMIENTO_INVALIDO
            return

        aplicar_movimiento()

        if self.tablero.el_rey_queda_en_jaque(self.pieza.color):
            self._motivo_rechazo = MotivoRechazoMovimiento.REY_EN_JAQUE
            return

        if self._es_pieza_con_primer_movimiento():
            self.pieza.movimiento_realizado()

        self.movimiento_valido = True

        self._actualizar_jugadas_sin_captura_ni_peon()

    """*Disponibilidad de captura al paso para la siguiente jugada tras aceptar la actual*"""

    def _actualizar_captura_al_paso(self) -> None:
        self._captura_al_paso_disponible = (
            isinstance(self.pieza, (PeonBlanco, PeonNegro))
            and self._calcular_desplazamiento() == (2, 0)
        )

        self.tablero.posicion_de_captura_al_paso = (
            self.destino
            if self.captura_al_paso_disponible
            else None
        )

    def _calcular_desplazamiento(self) -> tuple[int, int]:
        return (abs(self.destino[0] - self.origen[0]),
                abs(self.destino[1] - self.origen[1]))

    def _es_pieza_con_primer_movimiento(self) -> bool:
        return isinstance(self.pieza, (PeonBlanco, PeonNegro, Torre, Rey))

    def _actualizar_jugadas_sin_captura_ni_peon(self) -> None:
        if (
            not self.movimiento_valido or
            not self.estado_anterior
        ):
            return
        elif (
            isinstance(self.pieza, PeonBlanco | PeonNegro) or
            (
                self.estado_anterior.tablero.casillas[self.destino] is not None
            )
        ):
            self._jugadas_sin_captura_ni_peon = 0
        else:
            self._jugadas_sin_captura_ni_peon += 1

class Jugada(ABC):
    """Precondición: el nivel superior ha seleccionado el tipo de jugada."""

    def __init__(self,
                 numero: int,
                 origen: tuple[int, int],
                 destino: tuple[int, int],
                 anterior: Jugada | None,
                 *, 
                 estado_inicial: EstadoPosicion | None = None):
        if not anterior and not estado_inicial:
            estado_anterior = EstadoPosicion()
            tablero = estado_anterior.tablero
        elif not anterior:
            estado_anterior = estado_inicial
            tablero = estado_inicial.tablero
        else:
            estado_anterior = anterior.estado_posicion
            tablero = estado_anterior.tablero

        self._numero = numero
        self._origen = origen
        self._destino = destino
        self._anterior = anterior
        self._siguiente = None
        self._estado_posicion = EstadoPosicion(tablero = tablero,
                                               origen = self.origen,
                                               destino = self.destino,
                                               estado_anterior = estado_anterior)                                 
        
        self.estado_posicion.validar_movimiento(self._condiciones_especificas,
                                                self._aplicar_movimiento)

    @property
    def numero(self) -> int:
        return self._numero

    @property
    def origen(self) -> tuple[int, int]:
        return self._origen

    @property
    def destino(self) -> tuple[int, int]:
        return self._destino

    @property
    def anterior(self) -> Jugada | None:
        return self._anterior

    @property
    def siguiente(self) -> Jugada | None:
        return self._siguiente

    @siguiente.setter
    def siguiente(self, siguiente: Jugada | None) -> None:
        self._siguiente = siguiente

    @property
    def estado_posicion(self) -> EstadoPosicion:
        return self._estado_posicion

    @property
    def tablero(self) -> Tablero:
        return self.estado_posicion.tablero

    @property
    def pieza(self) -> Pieza:
        return self.estado_posicion.pieza

    def _condiciones_especificas(self) -> bool:
        return True

    def _aplicar_movimiento(self) -> None:
                self.tablero.trasladar_pieza(self.origen, self.destino)
    


class CapturaAlPaso(Jugada):
    def _condiciones_especificas(self) -> bool:
        # El rango candidato comprueba la geometría; el estado, la vigencia.
        return self.estado_posicion.estado_anterior.captura_al_paso_disponible

    def _aplicar_movimiento(self) -> None:
        self.tablero.colocar(None, self.tablero.posicion_de_captura_al_paso)
        super()._aplicar_movimiento()


class Enroque(Jugada):
    def _condiciones_especificas(self) -> bool:
        return self._enroque_disponible()

    def _aplicar_movimiento(self) -> None:
        posicion_torre = self._torre_enroque(self.destino)
        posicion_destino_torre = self._posicion_destino_torre()
        super()._aplicar_movimiento()
        self.tablero.trasladar_pieza(posicion_torre, posicion_destino_torre)
        self.tablero.casillas[posicion_destino_torre].movimiento_realizado()

    def _enroque_disponible(self) -> bool:
        if self.pieza.ha_movido:
            return False

        posicion_torre = self._torre_enroque(self.destino)
        posicion_destino_torre = self._posicion_destino_torre()
        torre = self.tablero.casillas[posicion_torre]

        if (
            torre is None
            or not isinstance(torre, Torre)
            or torre.ha_movido
            or not self.tablero.trayectoria_despejada(posicion_torre,
                                                      posicion_destino_torre)
        ):
            return False

        return self._enroque_no_amenazado()

    def _torre_enroque(self,
                       posicion: tuple[int, int]) -> tuple[int, int]:
        match posicion:
            case (0, 2):
                return (0, 0)
            case (0, 6):
                return (0, 7)
            case (7, 2):
                return (7, 0)
            case (7, 6):
                return (7, 7)

    def _posicion_destino_torre(self) -> tuple[int, int]:
        posicion_origen = self._torre_enroque(self.destino)

        match posicion_origen:
            case (0, 0):
                movimiento = EnroqueLargo()
            case (0, 7):
                movimiento = EnroqueCorto()
            case (7, 0):
                movimiento = EnroqueLargo()
            case (7, 7):
                movimiento = EnroqueCorto()

        vector = movimiento.vector_torre

        return (posicion_origen[0] + vector.desplazamiento[0],
                posicion_origen[1] + vector.desplazamiento[1])

    def _enroque_no_amenazado(self) -> bool:
        casillas_por_comprobar = 3
        aux_set = set()
        posicion = self.origen

        if self._torre_enroque(self.destino) in ((0, 0), (7, 0)):
            vector = Izquierda()
        else:
            vector = Derecha()

        while True:
            for casilla in self.tablero.casillas:
                if self.tablero.casillas[casilla] is None:
                    continue
                aux_set.add(self.tablero.posiciones_amenazadas(
                    self.tablero.casillas[casilla],
                    casilla
                ))

            for conjunto_inmutable in aux_set:
                if posicion in conjunto_inmutable:
                    self.tablero.trasladar_pieza(posicion, self.origen)
                    self.estado_posicion._motivo_rechazo = MotivoRechazoMovimiento.REY_EN_JAQUE
                    return False

            casillas_por_comprobar -= 1
            if casillas_por_comprobar == 0:
                break

            nueva_posicion = (posicion[0] + vector.desplazamiento[0],
                              posicion[1] + vector.desplazamiento[1])
            self.tablero.trasladar_pieza(posicion, nueva_posicion)
            posicion = nueva_posicion

        self.tablero.trasladar_pieza(posicion, self.origen)
        return True


class Turno:
    def __init__(self, 
                 numero_jugada: int):
        self._numero = (numero_jugada // 2) + 1
        self._jugada_blanco = None
        self._jugada_negro = None

    @property
    def numero(self) -> int:
        return self._numero

    @property
    def jugada_blanco(self) -> Jugada | None:
        return self._jugada_blanco

    @jugada_blanco.setter
    def jugada_blanco(self, 
                      jugada: Jugada) -> None:
        self._jugada_blanco = jugada

    @property
    def jugada_negro(self) -> Jugada | None:
        return self._jugada_negro

    @jugada_negro.setter
    def jugada_negro(self, 
                     jugada: Jugada) -> None:
        self._jugada_negro = jugada

class EstadoPartida(Enum):
    EN_CURSO = auto()
    VICTORIA_BLANCA = auto()
    VICTORIA_NEGRA = auto()
    TABLAS = auto()

class Partida:
    def __init__(self,
                 *,
                 estado_inicial: EstadoPosicion | None = None,
                 turno_inicial: Color | None = None):
        self._estado_inicial = estado_inicial
        self._contador_jugadas = 0
        if self._estado_inicial:
            self._tablero = self._estado_inicial.tablero

            if self._estado_inicial.pieza is None:
                self._jugador = Color.Blanco
            elif self._estado_inicial.pieza.color == Color.Blanco:
                self._jugador = Color.Negro
            else:
                self._jugador = Color.Blanco
        else:
            self._estado_inicial = EstadoPosicion()
            self._tablero = self.estado_inicial.tablero
            self._jugador = Color.Blanco
        if turno_inicial is not None:
            if not isinstance(turno_inicial, Color):
                raise ValueError("El turno inicial debe ser un Color.")
            self._jugador = turno_inicial
        self._primer_jugador = self._jugador
        if self._primer_jugador == Color.Blanco:
            self._segundo_jugador = Color.Negro
        else:
            self._segundo_jugador = Color.Blanco
        self._registro_turnos: list[Turno] = []
        self._promocion_pendiente = False
        self._ultima_jugada = None
        self._estado_partida = EstadoPartida.EN_CURSO
        self.actualizar_estado()

    @property
    def estado_inicial(self) -> EstadoPosicion | None:
        return self._estado_inicial

    @property 
    def contador_jugadas(self) -> int:
        return self._contador_jugadas

    @property
    def tablas_por_acuerdo_disponibles(self) -> bool:
        """Permite acordar tablas tras un movimiento confirmado de cada color.

        La alternancia garantiza que dos jugadas registradas incluyen ambos
        colores, también si empiezan las negras. La promoción pendiente aún
        no cuenta como jugada confirmada. Se consulta sólo esta partida.
        """
        return (
            self.contador_jugadas >= 2
            and self.estado_partida is EstadoPartida.EN_CURSO
            and not self.promocion_pendiente
        )

    @property
    def tablero(self) -> Tablero:
        return self._tablero

    @tablero.setter
    def tablero(self,
                tablero: Tablero) -> None:
        self._tablero = tablero

    @property 
    def registro_turnos(self) -> list[Turno]:
        return self._registro_turnos

    def iterar_estados(self) -> Generator[EstadoPosicion, None, None]:
        """Recorre sólo la línea registrada en esta partida, incluida su raíz."""
        yield self.estado_inicial

        for turno in self.registro_turnos:
            for jugada in (turno.jugada_blanco, turno.jugada_negro):
                if jugada is not None:
                    yield jugada.estado_posicion

    def contiene_estado(self, estado: EstadoPosicion) -> bool:
        return any(guardado is estado for guardado in self.iterar_estados())

    def obtener_estado_siguiente(self, estado: EstadoPosicion) -> EstadoPosicion | None:
        """Consulta contextual: no añade enlaces a estados compartidos."""
        anterior = None

        for guardado in self.iterar_estados():
            if anterior is estado:
                return guardado
            
            anterior = guardado

        return None

    def obtener_turno_en_estado(self, estado: EstadoPosicion) -> Color:
        turno = self.primer_jugador

        for guardado in self.iterar_estados():
            if guardado is estado:
                return turno
            
            turno = Color.Negro if turno is Color.Blanco else Color.Blanco

        raise ValueError("El estado no pertenece al historial de esta partida.")

    @property
    def jugador(self) -> Color:
        return self._jugador

    @jugador.setter
    def jugador(self,
                jugador: Color) -> None:
        self._jugador = jugador

    @property
    def primer_jugador(self) -> Color:
        return self._primer_jugador

    @property
    def segundo_jugador(self) -> Color:
        return self._segundo_jugador

    @property
    def promocion_pendiente(self) -> bool:
        return self._promocion_pendiente

    @promocion_pendiente.setter
    def promocion_pendiente(self,
                            pendiente: bool) ->  None:
        self._promocion_pendiente = pendiente

    @property
    def ultima_jugada(self) -> Jugada | None:
        return self._ultima_jugada

    @ultima_jugada.setter
    def ultima_jugada(self,
                      jugada: Jugada) -> None:
        self._ultima_jugada = jugada

    @property
    def apariciones_posicion_actual(self) -> int:
        """Cuenta las apariciones de la posición vigente en esta partida."""
        if self.ultima_jugada is None:
            estado = self.estado_inicial
        else:
            estado = self.ultima_jugada.estado_posicion

        return self._contar_apariciones_posicion(estado, self.jugador)

    @property
    def estado_partida(self) -> EstadoPartida:
        return self._estado_partida

    @estado_partida.setter
    def estado_partida(self,
                       estado: EstadoPartida) -> None:
        self._estado_partida = estado
        
    def es_promocion(self,
                     pieza: Pieza,
                     destino: tuple[int, int]) -> bool:
        return (
            isinstance(pieza, PeonBlanco) and destino[0] == 7
        ) or (
            isinstance(pieza, PeonNegro) and destino[0] == 0
        )

    def es_enroque(self,
                   pieza: Pieza,
                   origen: tuple[int, int],
                   destino: tuple[int, int]) -> bool:
        return (
            isinstance(pieza, Rey)
            and destino[0] == origen[0]
            and abs(destino[1] - origen[1]) == 2
        )

    def es_captura_al_paso(self,
                           pieza: Pieza,
                           origen: tuple[int, int],
                           destino: tuple[int, int]) -> bool:
        """Identifica una solicitud de captura al paso vigente.

        La validación completa incluye el rango candidato y la seguridad del rey propio.
        """
        return (
            isinstance(pieza, (PeonBlanco, PeonNegro))
            and abs(destino[0] - origen[0]) == 1
            and abs(destino[1] - origen[1]) == 1
            and destino in self.tablero.casillas
            and self.tablero.casillas[destino] is None
            and self.tablero.posicion_de_captura_al_paso == (
                origen[0], destino[1]
            )
        )

    def _actualizar_turno(self) -> None:
        if not self.registro_turnos:
            ultimo_turno = Turno(self.contador_jugadas)

            if self.primer_jugador == Color.Blanco:
                ultimo_turno.jugada_blanco = self.ultima_jugada
            else:
                ultimo_turno.jugada_negro = self.ultima_jugada

            self.registro_turnos.append(ultimo_turno)
        elif self.registro_turnos[-1].jugada_negro is not None:
            ultimo_turno = Turno(self.contador_jugadas)

            ultimo_turno.jugada_blanco = self.ultima_jugada
            
            self.registro_turnos.append(ultimo_turno)
        else: 
            self.registro_turnos[-1].jugada_negro = self.ultima_jugada

        if self.contador_jugadas % 2 == 0:
            self.jugador = self.primer_jugador
        else:
            self.jugador = self.segundo_jugador

    def _es_pieza_valida(self,
                         casilla: tuple[int, int]) -> bool:
        pieza = self.tablero.casillas[casilla]

        return pieza is not None and pieza.color == self.jugador

    def procesar_solicitud(self,
                            origen: tuple[int, int],
                            destino: tuple[int, int]) -> Jugada | MotivoRechazoMovimiento | None:
        """None al aceptar; Jugada si falta promocionar; motivo si se rechaza.

        El diagnóstico viaja con el retorno: un rechazo no modifica la partida
        ni añade una propuesta inválida a su historial.
        """
        jugada = self._nueva_jugada(origen,
                                    destino)

        if jugada is None:
            return MotivoRechazoMovimiento.MOVIMIENTO_INVALIDO

        if not jugada.estado_posicion.movimiento_valido:
            return jugada.estado_posicion.motivo_rechazo

        if jugada.estado_posicion.movimiento_valido:
            self.promocion_pendiente = self.es_promocion(jugada.pieza,
                                                          jugada.destino)
            if not self.promocion_pendiente:
                self.tablero = jugada.estado_posicion.tablero

                self._registrar_jugada(jugada)

                self.actualizar_estado()
            else:
                return jugada

    def promocionar(self,
                    posicion: tuple[int, int],
                    pieza: Pieza,
                    jugada: Jugada) -> None:
        jugada.estado_posicion.tablero.colocar(pieza,
                                               posicion)
        self.promocion_pendiente = False

        self.tablero = jugada.estado_posicion.tablero

        self._registrar_jugada(jugada)

        self.actualizar_estado() 

    def reclamar_tablas_por_cincuenta_movimientos(self,
                                                  *,
                                                  movimiento_anunciado: tuple[tuple[int, int],
                                                                              tuple[int, int]] |
                                                                              None = None,) -> bool:
        if self.tablas_por_cincuenta_movimientos_disponible(movimiento_anunciado = movimiento_anunciado):
            self.estado_partida = EstadoPartida.TABLAS

            return True

        return False

    def tablas_por_cincuenta_movimientos_disponible(
        self,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        if (
            self.estado_partida != EstadoPartida.EN_CURSO or
            self.promocion_pendiente
        ):
            return False

        if movimiento_anunciado is None:
            if self.ultima_jugada:
                estado = self.ultima_jugada.estado_posicion
            else:
                estado = self.estado_inicial
        else:
            origen, destino = movimiento_anunciado
            jugada = self._nueva_jugada(origen, destino)

            if jugada is None or not jugada.estado_posicion.movimiento_valido:
                return False

            estado = jugada.estado_posicion

        return estado.jugadas_sin_captura_ni_peon >= 100

    def reclamar_tablas_por_triple_repeticion(
        self,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        """Acepta la reclamación sin ejecutar el movimiento anunciado."""
        if self.tablas_por_triple_repeticion_disponible(
            movimiento_anunciado=movimiento_anunciado
        ):
            self.estado_partida = EstadoPartida.TABLAS
            return True

        return False

    def tablas_por_triple_repeticion_disponible(
        self,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        """Consulta la posición vigente o la que produciría un movimiento legal."""
        if self.estado_partida != EstadoPartida.EN_CURSO or self.promocion_pendiente:
            return False

        if movimiento_anunciado is None:
            return self.apariciones_posicion_actual >= 3

        origen, destino = movimiento_anunciado
        jugada = self._nueva_jugada(origen, destino)
        if jugada is None or not jugada.estado_posicion.movimiento_valido:
            return False

        estado = jugada.estado_posicion
        # La copia debe reflejar los derechos al paso tras el movimiento propuesto.
        estado._actualizar_captura_al_paso()
        turno_siguiente = Color.Negro if self.jugador is Color.Blanco else Color.Blanco

        return self._contar_apariciones_posicion(estado, turno_siguiente) + 1 >= 3

    def _contar_apariciones_posicion(self,
                                    estado: EstadoPosicion,
                                    turno: Color) -> int:
        """Cuenta sólo las apariciones ya registradas, incluida la raíz."""
        clave_buscada = self._obtener_clave_repeticion(estado, turno)
        apariciones = 0
        turno_historial = self.primer_jugador

        for estado_guardado in self.iterar_estados():
            clave_guardada = self._obtener_clave_repeticion(
                estado_guardado, turno_historial
            )
            if clave_guardada == clave_buscada:
                apariciones += 1

            turno_historial = (
                Color.Negro if turno_historial is Color.Blanco else Color.Blanco
            )

        return apariciones

    def _obtener_clave_repeticion(self,
                                 estado: EstadoPosicion,
                                 turno: Color) -> tuple:
        """Reúne los datos que distinguen una posición para la repetición."""
        distribucion = estado.tablero.obtener_clave_distribucion()
        derechos_enroque = estado.tablero.obtener_derechos_enroque()
        peon_capturable = self._obtener_peon_capturable_al_paso(estado, turno)

        return (distribucion, turno, derechos_enroque, peon_capturable)

    def _obtener_peon_capturable_al_paso(self,
                                         estado: EstadoPosicion,
                                         turno: Color) -> tuple[int, int] | None:
        """Devuelve la casilla del peón capturable legalmente, o None.

        Consulta el estado y el turno recibidos sin modificar el historial.
        """
        posicion_peon = estado.tablero.posicion_de_captura_al_paso

        if posicion_peon is None:
            return None

        fila, columna = posicion_peon

        avance = 1 if turno is Color.Blanco else -1

        destino = (fila + avance, columna)

        for columna_vecina in (columna - 1, columna + 1):
            origen = (fila, columna_vecina)

            pieza = estado.tablero.pieza_en(origen)
            
            if not isinstance(pieza, (PeonBlanco, PeonNegro)) or pieza.color is not turno:
                continue

            jugada = CapturaAlPaso(
                0, origen, destino, None, estado_inicial=estado
            )
            if jugada.estado_posicion.movimiento_valido:
                return posicion_peon

        return None

    def _nueva_jugada(self,
                     origen: tuple[int, int],
                     destino: tuple[int, int]) -> Jugada | None:
        pieza = self.tablero.casillas[origen]

        if not self._es_pieza_valida(origen):
            return

        elif self.es_captura_al_paso(pieza,
                                     origen,
                                     destino):
            return CapturaAlPaso(self.contador_jugadas + 1,
                                 origen,
                                 destino,
                                 self.ultima_jugada,
                                 estado_inicial = self.estado_inicial)

        elif self.es_enroque(pieza,
                             origen,
                             destino):
            return Enroque(self.contador_jugadas + 1,
                           origen,
                           destino,
                           self.ultima_jugada,
                           estado_inicial = self.estado_inicial)
        
        else:
            return Jugada(self.contador_jugadas + 1,
                          origen,
                          destino,
                          self.ultima_jugada,
                          estado_inicial = self.estado_inicial)

    def _registrar_jugada(self, 
                          jugada: Jugada) -> None:
        self._enlazar_jugada(jugada)
        self.ultima_jugada = jugada
        self._contador_jugadas = jugada.numero
        jugada.estado_posicion._actualizar_captura_al_paso()
        self._actualizar_turno()

    def _enlazar_jugada(self,
                         jugada: Jugada) -> None:
        if self.ultima_jugada is not None:
            self.ultima_jugada.siguiente = jugada

    """*Resolución y continuidad*"""

    def actualizar_estado(self) -> None:
        """Evalúa la posición vigente, también antes de la primera jugada."""
        estado = (self.estado_inicial if self.ultima_jugada is None
                  else self.ultima_jugada.estado_posicion)

        if self.tablero.es_posicion_muerta():
            self.estado_partida = EstadoPartida.TABLAS
            return

        if self._hay_jugadas_disponibles():
            if (
                estado.jugadas_sin_captura_ni_peon >= 150
                or self.apariciones_posicion_actual >= 5
            ):
                self.estado_partida = EstadoPartida.TABLAS

                return
            self.estado_partida = EstadoPartida.EN_CURSO
        elif self.tablero.el_rey_queda_en_jaque(self.jugador):
            if self.jugador == Color.Negro:
                self.estado_partida = EstadoPartida.VICTORIA_BLANCA
            else:
                self.estado_partida = EstadoPartida.VICTORIA_NEGRA
        else:
            self.estado_partida = EstadoPartida.TABLAS

    def _pieza_con_rango(self,
                         posicion: tuple[int, int]) -> bool:
        pieza = self.tablero.casillas[posicion]
        rango_candidato = self.tablero.calcular_rango_candidato(pieza, posicion)

        for destino in rango_candidato:
            jugada = self._nueva_jugada(posicion, destino)
            if jugada.estado_posicion.movimiento_valido:
                return True

        return False

    def _hay_jugadas_disponibles(self) -> bool:
        for casilla,pieza in self.tablero.casillas.items():
            if pieza is None or pieza.color != self.jugador:
                continue
            if self._pieza_con_rango(casilla):
                return True

        return False

    def abandonar(self,
                  color: Color) -> None:
        adversario = Color.Negro if color is Color.Blanco else Color.Blanco

        if (
            self.tablero.tiene_material_insuficiente_para_mate(adversario)
            or self.tablero.es_posicion_muerta_por_bloqueo()
        ):
            self.estado_partida = EstadoPartida.TABLAS
        elif adversario is Color.Blanco:
            self.estado_partida = EstadoPartida.VICTORIA_BLANCA
        else:
            self.estado_partida = EstadoPartida.VICTORIA_NEGRA

