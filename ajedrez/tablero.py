from .piezas import *
from dataclasses import dataclass
from copy import copy
from collections.abc import Iterator

Posicion = tuple[int, int]

@dataclass(frozen = True, slots = True)
class PiezaEnJuego:
    pieza: Pieza
    posicion: Posicion
    posiciones_amenazadas: frozenset[Posicion]


class Tablero:
    def __init__(self):
        self._casillas = self._inicializar()
        self._colocar_piezas()
        self._posicion_de_captura_al_paso = None

    @property
    def casillas(self) -> dict[tuple[int, int], Pieza | None]:
        return self._casillas

    @property
    def posicion_de_captura_al_paso(self) -> tuple[int, int] | None:
        return self._posicion_de_captura_al_paso

    @posicion_de_captura_al_paso.setter
    def posicion_de_captura_al_paso(self, 
                                    estado: tuple[int, int] | None) -> None:
        self._posicion_de_captura_al_paso = estado

    def pieza_en(self, coordenadas: tuple[int, int]) -> Pieza | None:
            return self.casillas.get(coordenadas)

    def _inicializar(self) -> dict[tuple[int, int], Pieza | None]:
        return {(fila, columna): None
                for fila in range(8)
                for columna in range(8)}

    def _colocar_piezas(self) -> None:
        self._colocar_primera_fila(Color.Blanco)
        self._colocar_fila_peones(Color.Blanco)
        self._colocar_primera_fila(Color.Negro)
        self._colocar_fila_peones(Color.Negro)

    def _colocar_primera_fila(self, color: Color) -> None:
        if color == Color.Blanco:
            f = 0
        else:
            f = 7

        for c in range(8):
            clave = (f, c)

            if c == 0 or c == 7:
                self.colocar(Torre(color), clave)

            if c == 1 or c == 6:
                self.colocar(Caballo(color), clave)

            if c == 2 or c == 5:
                self.colocar(Alfil(color), clave)

            if c == 3:
                self.colocar(Reina(color), clave)

            if c == 4:
                self.colocar(Rey(color), clave)

    def _colocar_fila_peones(self, color: Color) -> None:
        if color == Color.Blanco:
            for c in range(8):
                clave = (1, c)
                self.colocar(PeonBlanco(), clave)
        else:
            for c in range(8):
                clave = (6, c)
                self.colocar(PeonNegro(), clave)

    def colocar(self, pieza: Pieza | None, coordenadas: tuple[int, int]) -> None:
        self.casillas[coordenadas] = pieza

    """Precondición: La casilla no puede estar vacía"""

    def trasladar_pieza(self, origen: tuple[int, int], destino: tuple[int, int]) -> None:
        if origen == destino:
            return
        
        pieza = self.casillas[origen]

        self.colocar(pieza, destino)

        self.colocar(None, origen)

    def _trasladar_pieza(self, pieza: Pieza, origen: tuple[int, int], destino: tuple[int, int]) -> None:
        self.colocar(pieza, destino)
        self.colocar(None, origen)

    """*Condiciones de movimiento*"""

    def el_rey_queda_en_jaque(self, jugador: Color) -> bool:
        return next(self._iterar_atacantes_del_rey(jugador), None) is not None

    def obtener_atacantes_del_rey(self, jugador: Color) -> tuple[Posicion, ...]:
        """Casillas de todas las piezas que dan jaque, sin modificar el tablero."""
        return tuple(self._iterar_atacantes_del_rey(jugador))

    def _iterar_atacantes_del_rey(self, jugador: Color) -> Iterator[Posicion]:
        posiciones_rey = {
            posicion for posicion, pieza in self.casillas.items()
            if isinstance(pieza, Rey) and pieza.color == jugador
        }
        if not posiciones_rey:
            return
        for posicion, pieza in self.casillas.items():
            if pieza is not None and pieza.color != jugador:
                if posiciones_rey & self.posiciones_amenazadas(pieza, posicion):
                    yield posicion

    def _no_ocupada_por_aliado(
            self,
            jugador: Color,
            destino: tuple[int, int]
    ) -> bool:
        pieza_destino = self.casillas[destino]

        return (
            pieza_destino is None or 
            jugador != pieza_destino.color
                )

    def _ocupada_por_enemigo(self,
                             jugador: Color,
                             posicion: tuple[int, int]
    ) -> bool:
        return (
            self.casillas[posicion] is not None and 
            jugador != self.casillas[posicion].color
                )

    def trayectoria_despejada(
            self,
            origen: tuple[int, int],
            destino: tuple[int, int]
    ) -> bool:
        return self._trayectoria_despejada(origen, destino)

    def _trayectoria_despejada(
            self,
            origen: tuple[int, int],
            destino: tuple[int, int]
    ) -> bool:
        desplazamiento_vertical = destino[0] - origen[0]
        desplazamiento_horizontal = destino[1] - origen [1]

        if desplazamiento_horizontal == 0:
            desplazamiento = desplazamiento_vertical

            if desplazamiento_vertical > 0:
                vector = Arriba()

            if desplazamiento_vertical < 0:
                vector = Abajo()

        if desplazamiento_vertical == 0:
            desplazamiento = desplazamiento_horizontal

            if desplazamiento_horizontal > 0:
                vector = Derecha()

            if desplazamiento_horizontal < 0:
                vector = Izquierda()

        for _ in range(abs(desplazamiento) - 1):
                        origen = (origen[0] + vector.desplazamiento[0],
                                   origen[1] + vector.desplazamiento[1])
        
                        if self.casillas.get(origen) is not None:
                            return False
                        
        return True

    def _primer_movimiento_no_realizado(self, 
                                        pieza: PiezaConPrimerMovimiento) -> bool:
        return pieza.ha_movido

    def _captura_al_paso_posible(self,
                                 pieza: Pieza,
                                 posicion: tuple[int, int],
                                 movimiento: Movimiento) -> bool:
        if not self._captura_al_paso_permitida():
            return False
        
        posicion_a_la_derecha = ((posicion[0] + 
                                 Derecha().desplazamiento[0],
                                 posicion[1] +
                                 Derecha().desplazamiento[1]) == 
                                 self.posicion_de_captura_al_paso)

        posicion_a_la_izquierda = ((posicion[0] + 
                                   Izquierda().desplazamiento[0],
                                   posicion[1] +
                                   Izquierda().desplazamiento[1]) == 
                                   self.posicion_de_captura_al_paso)

        casilla_destino = (posicion[0] + movimiento.vector.desplazamiento[0],
                           posicion[1] + movimiento.vector.desplazamiento[1])

        if casilla_destino not in self.casillas:
            return False
        
        if isinstance(pieza, PeonBlanco):
            return (
                (                 
                    (posicion_a_la_derecha) and
                    (
                        isinstance(movimiento,
                                AlPasoBlancoDerecha)   
                    )
                ) or
                (
                    (posicion_a_la_izquierda) and 
                    (
                        isinstance(movimiento,
                                   AlPasoBlancoIzquierda)
                    )              
                )
                )
        if isinstance(pieza, PeonNegro):
            return (
                (
                    (posicion_a_la_derecha) and
                    (
                        isinstance(movimiento,
                                    AlPasoNegroDerecha)
                    )
                ) or
                (
                    (posicion_a_la_izquierda) and
                    (
                        isinstance(
                            movimiento,
                            AlPasoNegroIzquierda
                        )
                    )
                )               
            )

        return False

    def _destinos_candidatos_del_peon(self,
                                    peon: PeonBlanco | PeonNegro,
                                    posicion: tuple[int, int]) -> set[tuple[int, int]]:
        movimientos = set()
        color = peon.color

        if color == Color.Blanco:
            vector_avance = Arriba()
            vector_captura_derecha = ArribaDerecha()
            vector_captura_izquierda = ArribaIzquierda()
        else:
            vector_avance = Abajo()
            vector_captura_derecha = AbajoDerecha()
            vector_captura_izquierda = AbajoIzquierda()

        casilla = (
            posicion[0] + vector_avance.desplazamiento[0],
            posicion[1] + vector_avance.desplazamiento[1]
        ) 

        if (
            casilla in self.casillas and
            self.casillas[casilla] is None
        ):
            movimientos.add(casilla)

            casilla = (
                        casilla[0] + vector_avance.desplazamiento[0],
                        casilla[1] + vector_avance.desplazamiento[1]
                    )

            if (
                casilla in self.casillas and
                self.casillas[casilla] is None
            ):
                movimientos.add(casilla)


        casilla = (
            posicion[0] + vector_captura_derecha.desplazamiento[0],
            posicion[1] + vector_captura_derecha.desplazamiento[1]
        )

        if (
            casilla in self.casillas and
            self._ocupada_por_enemigo(color,
                                    casilla)
         ):
            movimientos.add(casilla)

        casilla = (
            posicion[0] + vector_captura_izquierda.desplazamiento[0],
            posicion[1] + vector_captura_izquierda.desplazamiento[1]
        )

        if (
            casilla in self.casillas and
            self._ocupada_por_enemigo(color,
                                      casilla)
        ):
            movimientos.add(casilla)

        for movimiento in peon.movimientos:
            if self._captura_al_paso_posible(peon, posicion, movimiento):
                destino_al_paso = (
                    posicion[0] + movimiento.vector.desplazamiento[0],
                    posicion[1] + movimiento.vector.desplazamiento[1]
                )
                movimientos.add(destino_al_paso)

        return movimientos

    """Para evalular esta condición, es necesario tener acceso a los rangos de movimientos de las piezas adversarias"""

    def _captura_al_paso_permitida(self) -> bool:
        return self.posicion_de_captura_al_paso is not None

    """Para evaluar esta condición, es necesario conocer el último movimiento realizado por el adversario, en concreto:
            - Pieza movida (peón)
            - Tipo de movimiento (avance doble)
            - Destino"""
    
    """*Movimientos*"""

    """Precondición: la casilla de origen NO puede estar vacía"""

    def _aplicar_vector(
            self,
            pieza: Pieza,
            origen: tuple[int, int],
            vector: Vector,
            posiciones: dict[tuple[int, int], None]
    ) -> dict[tuple[int, int] , None]:
        nuevo_origen = (origen[0] + vector.desplazamiento[0],
                        origen[1] + vector.desplazamiento[1])
        
        if nuevo_origen not in self.casillas: 
                    return posiciones     
        
        if (
            not pieza.es_deslizante and
            self._no_ocupada_por_aliado(
                pieza.color,
                nuevo_origen
            )
        ):           
            posiciones.update({nuevo_origen: None})
            
            return posiciones
        
        elif not self._no_ocupada_por_aliado(
            pieza.color,
            nuevo_origen 
        ):
            return posiciones

        pieza_adyacente = self.casillas[nuevo_origen]

        if pieza_adyacente is not None:
            if pieza_adyacente.color == pieza.color:
                return posiciones
            else:
                posiciones.update({nuevo_origen: None})
                return posiciones

        posiciones.update({nuevo_origen: None})

        return self._aplicar_vector(pieza,
                                    nuevo_origen,
                                    vector,
                                    posiciones)


    def calcular_rango_candidato(self, 
                                      pieza: Pieza, 
                                      origen: tuple[int, int]) -> set[tuple[int, int]]:
        conjunto_candidato = set()

        for movimiento in pieza.movimientos:
            movimiento_valido = True

            for condicion in movimiento.condiciones:
                if (
                    condicion == CondicionMovimiento.TRAYECTORIA_DESPEJADA and
                    not self._trayectoria_despejada(
                        origen,
                        (origen[0] + movimiento.vector.desplazamiento[0],
                         origen[1] + movimiento.vector.desplazamiento[1])
                        )
                ):
                    movimiento_valido = False

                if (
                    condicion == CondicionMovimiento.PRIMER_MOVIMIENTO_NO_REALIZADO and
                    pieza.ha_movido
                ):
                    movimiento_valido = False

                if condicion == CondicionMovimiento.MOVIMIENTO_PEON:
                    destino = (origen[0] + movimiento.vector.desplazamiento[0],
                               origen[1] + movimiento.vector.desplazamiento[1])
                    
                    disponibles = self._destinos_candidatos_del_peon(pieza, origen)

                    if not destino in disponibles:
                        movimiento_valido = False

            if not movimiento_valido:
                continue
            
            conjunto_candidato.update(
                self._aplicar_vector(
                    pieza, 
                    origen, 
                    movimiento.vector, 
                    {}
                    )
                                       )
        return conjunto_candidato
                
    """Precondición: La casilla de origen no puede estar vacía"""

    def posiciones_amenazadas(self, 
                               pieza: Pieza,
                               origen: tuple[int, int]) -> frozenset[tuple[int, int]]:
        posiciones = set()
        movimientos = pieza.movimientos

        for movimiento in movimientos:
            if self._es_condicion(movimiento, 
                                  CondicionMovimiento.TRAYECTORIA_DESPEJADA):
                continue

            if (
                (isinstance(pieza, PeonBlanco) and 
                 isinstance(movimiento, OrtogonalArriba)) or 
                 (isinstance(pieza, PeonNegro) and 
                  isinstance(movimiento, OrtogonalAbajo))
                  ):
                continue

            aux = {}

            aux = self._aplicar_vector(pieza,
                                       origen,
                                       movimiento.vector,
                                       aux)

            if aux:
                ultima_posicion = next(reversed(aux))
            else:
                continue

            if self._ocupada_por_enemigo(pieza.color, ultima_posicion):
                posiciones.add(ultima_posicion)

        return frozenset(posiciones)

        

    def _es_condicion(self, movimiento: Movimiento, 
                      condicion_buscada: CondicionMovimiento) -> bool:
        condiciones = movimiento.condiciones

        for condicion in condiciones:
            if condicion == condicion_buscada:
                return True

        return False

    def tiene_material_insuficiente_para_mate(self, color: Color) -> bool:
        """Indica si el material impide a ese color dar cualquier mate.

        Precondición: posición válida con ambos reyes. Se consideran también
        las piezas rivales que podrían bloquear las salidas de su propio rey.
        False no garantiza un mate posible: no se estudian bloqueos ni líneas
        forzadas. La consulta no modifica el tablero.
        """
        material = [
            (posicion, pieza)
            for posicion, pieza in self.casillas.items()
            if pieza is not None and not isinstance(pieza, Rey)
        ]
        piezas_propias = [pieza for _, pieza in material if pieza.color is color]

        if not piezas_propias:
            return True

        if len(piezas_propias) == 1 and isinstance(piezas_propias[0], Caballo):
            # Una dama rival no puede ayudar a encerrar al rey ante un caballo;
            # un peón, caballo, alfil o torre sí puede hacerlo.
            return all(
                isinstance(pieza, Reina)
                for _, pieza in material if pieza.color is not color
            )

        if all(isinstance(pieza, Alfil) for pieza in piezas_propias):
            if any(isinstance(pieza, (PeonBlanco, PeonNegro, Caballo))
                   for _, pieza in material):
                return False

            colores_de_casilla = {
                (fila + columna) % 2
                for (fila, columna), pieza in material
                if isinstance(pieza, Alfil)
            }
            # Torres y damas rivales no hacen posible el mate de estos alfiles.
            return len(colores_de_casilla) == 1

        return False

    def es_posicion_muerta_por_material(self) -> bool:
        """Indica si el material impide el mate de ambos colores.

        False no descarta posiciones muertas por bloqueos o secuencias forzadas.
        """
        return all(self.tiene_material_insuficiente_para_mate(color) for color in Color)

    def es_posicion_muerta(self) -> bool:
        """Reconoce los casos demostrados por material o bloqueo permanente.

        Es una condición suficiente, no una búsqueda de todas las secuencias
        legales: False no demuestra que sea posible dar mate.
        """
        return (
            self.es_posicion_muerta_por_material()
            or self.es_posicion_muerta_por_bloqueo()
        )

    def es_posicion_muerta_por_bloqueo(self) -> bool:
        """Demuestra un bloqueo en el que sólo pueden desplazarse los reyes.

        Precondición: posición válida con ambos reyes. Se quitan los reyes de
        una copia del diccionario para comprobar que ninguna otra pieza podría
        moverse aunque aquellos se apartasen. Se incluyen las capturas al paso.

        Después se busca si algún rey podría alcanzar una captura que rompiese
        el bloqueo, ignorando la oposición del otro rey. Si ni siquiera así
        existe una captura, las demás piezas permanecerán inmóviles siempre.
        Sin un jaque previo, tampoco puede aparecer un mate: sus ataques no
        cambiarán y los reyes no pueden darse jaque mediante movimientos legales.

        False significa que esta prueba no demuestra el bloqueo. El tablero,
        las piezas y los derechos de movimiento originales no se modifican.
        """
        reyes = [(posicion, pieza) for posicion, pieza in self.casillas.items()
                 if isinstance(pieza, Rey)]
        piezas_bloqueadas = [(posicion, pieza) for posicion, pieza in self.casillas.items()
                            if pieza is not None and not isinstance(pieza, Rey)]
        if not piezas_bloqueadas:
            return False

        tablero_sin_reyes = copy(self)
        tablero_sin_reyes._casillas = self.casillas.copy()
        for posicion, _ in reyes:
            tablero_sin_reyes.colocar(None, posicion)

        for posicion, pieza in piezas_bloqueadas:
            if tablero_sin_reyes.calcular_rango_candidato(pieza, posicion):
                return False

        if any(self.el_rey_queda_en_jaque(rey.color) for _, rey in reyes):
            return False

        return not any(
            tablero_sin_reyes._rey_puede_capturar_pieza_bloqueada(posicion, rey)
            for posicion, rey in reyes
        )

    def _rey_puede_capturar_pieza_bloqueada(self,
                                          origen: Posicion,
                                          rey: Rey) -> bool:
        """Busca una primera captura en una copia sin reyes ni piezas móviles.

        Se examina cada casilla como máximo una vez. El rey adversario se omite
        deliberadamente: puede apartarse. Los ataques de las piezas fijas sí
        impiden avanzar. Cada colocación provisional se restaura antes de seguir.
        """
        pendientes = [origen]
        visitadas = {origen}

        while pendientes:
            fila, columna = pendientes.pop()
            for desplazamiento_fila in (-1, 0, 1):
                for desplazamiento_columna in (-1, 0, 1):
                    destino = (fila + desplazamiento_fila, columna + desplazamiento_columna)
                    if destino not in self.casillas or destino in visitadas:
                        continue
                    visitadas.add(destino)
                    pieza_destino = self.casillas[destino]
                    if pieza_destino is not None and pieza_destino.color is rey.color:
                        continue

                    self.colocar(rey, destino)
                    queda_en_jaque = self.el_rey_queda_en_jaque(rey.color)
                    self.colocar(pieza_destino, destino)
                    if queda_en_jaque:
                        continue
                    if pieza_destino is not None:
                        return True
                    pendientes.append(destino)

        return False

    def obtener_clave_distribucion(self) -> tuple[tuple[tuple[int, int],
                                                  type[Pieza], Color], ...]:
        aux = []

        for (fila, columna) in self.casillas:
            if not self.casillas[(fila, columna)]:
                continue

            aux.append(((fila, columna), 
                        type(self.casillas[(fila, columna)]),
                        self.casillas[(fila, columna)].color))

        return tuple(aux)

    def obtener_derechos_enroque(self) -> frozenset[tuple[Color, int]]:
        derechos = set()
        
        for color, fila in ((Color.Blanco, 0), 
                            (Color.Negro, 7)):
            rey = self.pieza_en((fila, 4))

            if (
                not isinstance(rey, Rey) or 
                rey.color is not color or 
                rey.ha_movido
            ):
                continue
            
            for columna in (0, 7):
                torre = self.pieza_en((fila, columna))

                if (
                    isinstance(torre, Torre) 
                    and torre.color is color and 
                    not torre.ha_movido
                ):
                    derechos.add((color, columna))
                    
        return frozenset(derechos)