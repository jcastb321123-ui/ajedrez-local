import tkinter as tk
from tkinter import messagebox
from .sesion import SesionLocal,AsignacionColores, ModalidadAsignacion
from .gráficos.temas_graficos import cargar_tema, TemaGrafico
from .gráficos.interfaz_partida import InterfazPartida
from .gráficos.graficos_tablero import Casillero
from .partida import EstadoPartida

class AplicacionAjedrez:
    def __init__(self,
                 *,
                 ventana: tk.Tk | None = None,
                 modalidad_asignacion: ModalidadAsignacion | None = None):
        if not ventana:
            ventana = tk.Tk()
        self._ventana = ventana
        self._ventana.title("Ajedrez")
        self._tema = cargar_tema(ventana)
        self._panel_controles = tk.Frame(ventana)
        self.panel_controles.pack()
        self._contenedor_partida = None
        self._interfaz_partida = None
        self._boton_nueva_partida = tk.Button(self.panel_controles,
                                              anchor = "n",
                                              text = "Nueva partida",
                                              command = self.solicitar_nueva_partida)
        self.boton_nueva_partida.grid(column = 0,           
                                      row = 0)
        if not modalidad_asignacion:
            self._modalidad_asignacion = ModalidadAsignacion.ALEATORIA
        else:
            self._modalidad_asignacion = modalidad_asignacion
        self._interfaz_partida = None

        self._crear_partida_local()

        self.ventana.protocol("WM_DELETE_WINDOW", 
                              self.solicitar_cierre)
        
    def solicitar_nueva_partida(self) -> None:
        respuesta = messagebox.askyesno(title = "Nueva partida",
                                        message = "¿Quieres iniciar una nueva partida?")

        if respuesta:
            self._crear_partida_local()

    def ejecutar(self) -> None:
        self.ventana.mainloop()

    def _crear_partida_local(self) -> None:
        if self.contenedor_partida:
            self.contenedor_partida.destroy()

        nuevo_contenedor = tk.Frame(self.ventana)

        self.contenedor_partida = nuevo_contenedor

        self.contenedor_partida.pack(fill = "both",
                                     expand = True)

        sesion_local = SesionLocal(AsignacionColores
                                   (self.modalidad_asignacion))

        casillero = Casillero(self.contenedor_partida,
                              self.tema)

        self.interfaz_partida = InterfazPartida(sesion_local,
                                   casillero,
                                   contenedor = self.contenedor_partida)


    @property
    def ventana(self) -> tk.Tk:
        return self._ventana

    @property
    def tema(self) -> TemaGrafico:
        return self._tema

    @property
    def panel_controles(self) -> tk.Frame:
        return self._panel_controles

    @property
    def contenedor_partida(self) -> tk.Frame | None:
        return self._contenedor_partida

    @contenedor_partida.setter
    def contenedor_partida(self,
                           nuevo_contenedor = tk.Frame) -> None:
        self._contenedor_partida = nuevo_contenedor

    @property
    def interfaz_partida(self) -> InterfazPartida | None:
        return self._interfaz_partida

    @property
    def modalidad_asignacion(self) -> ModalidadAsignacion:
        return self._modalidad_asignacion

    @interfaz_partida.setter
    def interfaz_partida(self,
                         nueva_interfaz: InterfazPartida) -> None:
        self._interfaz_partida = nueva_interfaz

    @property
    def boton_nueva_partida(self) -> tk.Button:
        return self._boton_nueva_partida

    def solicitar_cierre(self) -> None:
        if self.interfaz_partida.sesion.partida.estado_partida == EstadoPartida.EN_CURSO:
            respuesta = messagebox.askyesno(parent = self.ventana,
                                            message = "La aplicación se cerrará")

            if respuesta:
                self.ventana.destroy()
        else:
            self.ventana.destroy()
def main():
    aplicacion = AplicacionAjedrez()

    aplicacion.ejecutar()

if __name__ == "__main__":
    main()
