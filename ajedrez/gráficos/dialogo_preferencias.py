"""Elección de preferencias visuales; sólo Aplicar confirma el borrador."""

from collections.abc import Callable
from dataclasses import replace
import tkinter as tk
from tkinter import ttk

from .opciones_visuales import (
    ModoResaltadoJaque, OpcionesVisuales, OPCIONES_VISUALES_PREDETERMINADAS,
)
from .temas_graficos import IDENTIFICADOR_TEMA_PREDETERMINADO


class DialogoPreferencias(tk.Toplevel):
    def __init__(self, master: tk.Misc, opciones: OpcionesVisuales, *,
                 temas: dict[str, str], tema_actual: str,
                 aplicar: Callable[[OpcionesVisuales, str], bool]):
        super().__init__(master)
        self._opciones_iniciales = opciones
        self._aplicar = aplicar
        self._foco_anterior = master.focus_get()
        self._modo_jaque = tk.StringVar(master=self, value=opciones.modo_resaltado_jaque.value)
        self._opciones_jaque: dict[ModoResaltadoJaque, ttk.Radiobutton] = {}
        self._identificadores_temas = tuple(temas)
        self.title('Preferencias visuales')
        self.transient(master)
        self.resizable(False, False)

        self._contenido = ttk.Frame(self, padding=16)
        self._contenido.grid(sticky='nsew')
        self._grupo_tema = ttk.LabelFrame(self._contenido, text='Tema del tablero', padding=12)
        self._grupo_tema.grid(row=0, column=0, sticky='ew', pady=(0, 12))
        self._selector_tema = ttk.Combobox(self._grupo_tema, state='readonly',
                                          values=tuple(temas.values()), width=42)
        self._selector_tema.pack(fill='x')
        self._selector_tema.current(self._identificadores_temas.index(tema_actual))
        self._grupo_jaque = ttk.LabelFrame(self._contenido, text='Resaltado del jaque', padding=12)
        self._grupo_jaque.grid(row=1, column=0, sticky='ew')
        for fila, (modo, texto) in enumerate((
            (ModoResaltadoJaque.REY_PERMANENTE, 'Resaltar el rey de forma permanente'),
            (ModoResaltadoJaque.INTERMITENTE_TRAS_RECHAZO, 'Parpadear al rechazar un movimiento que deja al rey en jaque'),
            (ModoResaltadoJaque.REY_Y_ATACANTES, 'Resaltar el rey y las piezas que lo amenazan'),
        )):
            boton = ttk.Radiobutton(self._grupo_jaque, text=texto, variable=self._modo_jaque,
                                    value=modo.value)
            boton.grid(row=fila, column=0, sticky='w', pady=6)
            self._opciones_jaque[modo] = boton

        self._aviso = ttk.Label(self._contenido, text='Los cambios se guardan al pulsar «Aplicar».')
        self._aviso.grid(row=2, column=0, sticky='w', pady=(12, 0))
        self._controles = ttk.Frame(self._contenido)
        self._controles.grid(row=3, column=0, sticky='ew', pady=(16, 0))
        self._controles.columnconfigure(0, weight=1)
        self._boton_restablecer = ttk.Button(self._controles, text='Restablecer valores predeterminados',
                                            command=self.restablecer)
        self._boton_restablecer.grid(row=0, column=0, sticky='w', padx=(0, 16))
        self._boton_cancelar = ttk.Button(self._controles, text='Cancelar', command=self.cancelar)
        self._boton_cancelar.grid(row=0, column=1, padx=(0, 6))
        self._boton_aplicar = ttk.Button(self._controles, text='Aplicar', command=self.aplicar)
        self._boton_aplicar.grid(row=0, column=2)

        self.protocol('WM_DELETE_WINDOW', self.cancelar)
        self.bind('<Escape>', lambda evento: self.cancelar())
        self.grab_set()
        self._selector_tema.focus_set()

    def restablecer(self) -> None:
        """Restablece la elección visible, pendiente de confirmación."""
        self._modo_jaque.set(OPCIONES_VISUALES_PREDETERMINADAS.modo_resaltado_jaque.value)
        self._selector_tema.current(self._identificadores_temas.index(IDENTIFICADOR_TEMA_PREDETERMINADO))

    def aplicar(self) -> None:
        # Conserva los demás campos, incluidos los de futuras ampliaciones.
        opciones = replace(self._opciones_iniciales,
                           modo_resaltado_jaque=ModoResaltadoJaque(self._modo_jaque.get()))
        identificador = self._identificadores_temas[self._selector_tema.current()]
        if self._aplicar(opciones, identificador):
            self.cancelar()
        else:
            # Un aviso de error puede haber tomado y liberado el control modal.
            self.grab_set()

    def cancelar(self) -> None:
        self.destroy()
        if self._foco_anterior is not None and self._foco_anterior.winfo_exists():
            self._foco_anterior.focus_set()
