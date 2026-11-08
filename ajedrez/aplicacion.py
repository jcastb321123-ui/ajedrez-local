import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from .sesion import SesionLocal,AsignacionColores, ModalidadAsignacion
from .gráficos.temas_graficos import cargar_tema, TemaGrafico
from .gráficos.interfaz_partida import InterfazPartida
from .gráficos.graficos_tablero import Casillero
from .partida import EstadoPartida, Partida
from .persistencia import ErrorArchivoPartida, cargar_partida, guardar_partida, partida_a_datos

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
        self._ruta_partida: Path | None = None
        self._datos_ultimo_guardado: dict | None = None
        self._boton_nueva_partida = tk.Button(self.panel_controles,
                                              anchor = "n",
                                              text = "Nueva partida",
                                              command = self.solicitar_nueva_partida)
        self.boton_nueva_partida.grid(column = 0,           
                                      row = 0)
        self._boton_abrir_partida = tk.Button(
            self.panel_controles, text="Abrir partida", command=self.solicitar_abrir_partida,
        )
        self._boton_abrir_partida.grid(column=1, row=0)
        self._boton_guardar_partida = tk.Button(
            self.panel_controles, text="Guardar partida", command=self.solicitar_guardar_partida,
        )
        self._boton_guardar_partida.grid(column=2, row=0)
        if not modalidad_asignacion:
            self._modalidad_asignacion = ModalidadAsignacion.ALEATORIA
        else:
            self._modalidad_asignacion = modalidad_asignacion
        self._crear_partida_local()

        self.ventana.protocol("WM_DELETE_WINDOW", 
                              self.solicitar_cierre)
        
    def solicitar_nueva_partida(self) -> None:
        if self._hay_cambios_sin_guardar():
            continuar = self._confirmar_guardado_pendiente()
        else:
            continuar = messagebox.askyesno(
                parent=self.ventana, title="Nueva partida",
                message="¿Quieres iniciar una nueva partida?",
            )
        if continuar:
            self._crear_partida_local()

    def solicitar_guardar_partida(self) -> bool:
        """Guarda la partida original, incluso mientras se consulta su historial."""
        sesion = self.interfaz_partida.sesion
        if not sesion.admite_guardado_local:
            return False
        try:
            datos = partida_a_datos(sesion.partida)
        except ErrorArchivoPartida as error:
            messagebox.showinfo(parent=self.ventana, title="Guardar partida", message=str(error))
            return False
        ruta = self._ruta_partida
        if ruta is None:
            elegida = filedialog.asksaveasfilename(
                parent=self.ventana, title="Guardar partida local",
                defaultextension=".json", initialfile="partida.json",
                filetypes=[("Partida de Ajedrez local", "*.json")],
            )
            if not elegida:
                return False
            ruta = Path(elegida)
        try:
            guardar_partida(sesion.partida, ruta)
        except OSError as error:
            messagebox.showerror(parent=self.ventana, title="No se pudo guardar", message=str(error))
            return False
        self._ruta_partida = ruta
        self._datos_ultimo_guardado = datos
        self.ventana.title(f"Ajedrez — {ruta.name}")
        return True

    def solicitar_abrir_partida(self) -> None:
        elegida = filedialog.askopenfilename(
            parent=self.ventana, title="Abrir partida local",
            filetypes=[("Partida de Ajedrez local", "*.json")],
        )
        if not elegida:
            return
        try:
            partida = cargar_partida(elegida)
        except (OSError, ErrorArchivoPartida) as error:
            messagebox.showerror(parent=self.ventana, title="No se pudo abrir", message=str(error))
            return
        # El archivo se valida antes de sustituir la partida que está en pantalla.
        if not self._confirmar_guardado_pendiente():
            return
        # Si se acaba de guardar sobre el archivo elegido, abre su contenido actual.
        if self._ruta_partida is not None and Path(elegida).resolve() == self._ruta_partida.resolve():
            try:
                partida = cargar_partida(elegida)
            except (OSError, ErrorArchivoPartida) as error:
                messagebox.showerror(parent=self.ventana, title="No se pudo abrir", message=str(error))
                return
        self._crear_partida_local(partida=partida)
        self._ruta_partida = Path(elegida)
        self.ventana.title(f"Ajedrez — {self._ruta_partida.name}")

    def _hay_cambios_sin_guardar(self) -> bool:
        sesion = self.interfaz_partida.sesion
        return sesion.admite_guardado_local and (
            sesion.partida.promocion_pendiente
            or partida_a_datos(sesion.partida) != self._datos_ultimo_guardado
        )

    def _confirmar_guardado_pendiente(self) -> bool:
        if not self._hay_cambios_sin_guardar():
            return True
        respuesta = messagebox.askyesnocancel(
            parent=self.ventana, title="Cambios sin guardar",
            message="¿Quieres guardar la partida antes de continuar?\n"
                    "Se guarda la partida original con su historial, sin anotaciones ni variantes.",
        )
        if respuesta is None:
            return False
        return self.solicitar_guardar_partida() if respuesta else True

    def ejecutar(self) -> None:
        self.ventana.mainloop()

    def _crear_partida_local(self, *, partida: Partida | None = None) -> None:
        if self.contenedor_partida:
            self.contenedor_partida.destroy()

        nuevo_contenedor = tk.Frame(self.ventana)

        self.contenedor_partida = nuevo_contenedor

        self.contenedor_partida.pack(fill = "both",
                                     expand = True)

        sesion_local = SesionLocal(AsignacionColores
                                   (self.modalidad_asignacion), partida=partida)

        casillero = Casillero(self.contenedor_partida,
                              self.tema)

        self.interfaz_partida = InterfazPartida(sesion_local,
                                   casillero,
                                   contenedor = self.contenedor_partida)
        if partida is not None:
            self.interfaz_partida.mostrar_estado(sesion_local.estado_actual)
        if self._ruta_partida is not None:
            self.ventana.title("Ajedrez")
        self._ruta_partida = None
        self._datos_ultimo_guardado = partida_a_datos(sesion_local.partida)
        self._boton_guardar_partida.configure(
            state="normal" if sesion_local.admite_guardado_local else "disabled",
        )


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
        if self._hay_cambios_sin_guardar():
            if self._confirmar_guardado_pendiente():
                self.ventana.destroy()
            return
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
