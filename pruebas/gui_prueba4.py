from __future__ import annotations
import tkinter as tk
from ajedrez.gráficos.temas_graficos import cargar_tema
from ajedrez.sesion import SesionLocal,AsignacionColores, ModalidadAsignacion
from ajedrez.gráficos.interfaz_partida import InterfazPartida
from ajedrez.gráficos.graficos_tablero import Casillero

def main():
    ventana = tk.Tk()

    sesion = SesionLocal(AsignacionColores(ModalidadAsignacion.ALEATORIA))

    tema = cargar_tema(ventana)

    contenedor_partida = tk.Frame(ventana)
    contenedor_partida.pack(fill="both", expand=True)

    interfaz = InterfazPartida(sesion,
                               Casillero(contenedor_partida,
                                         tema),
                               contenedor=contenedor_partida)

    ventana.mainloop()

if __name__ == "__main__":
    main()
