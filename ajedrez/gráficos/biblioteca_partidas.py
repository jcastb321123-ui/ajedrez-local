"""Ventana de biblioteca; las acciones sobre la partida abierta se delegan."""

from collections.abc import Callable
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from ..repositorio_partidas import RepositorioPartidasSQLite, ResumenPartida


class VentanaBiblioteca(tk.Toplevel):
    def __init__(self, master: tk.Misc, repositorio: RepositorioPartidasSQLite, *,
                 abrir_partida: Callable[[ResumenPartida], bool],
                 guardar_partida: Callable[[bool], bool],
                 eliminar_partida: Callable[[ResumenPartida], bool],
                 puede_guardar: Callable[[], bool]):
        super().__init__(master)
        self._repositorio = repositorio
        self._abrir_partida = abrir_partida
        self._guardar_partida = guardar_partida
        self._eliminar_partida = eliminar_partida
        self._puede_guardar = puede_guardar
        self._resumenes: dict[str, ResumenPartida] = {}
        self.title('Biblioteca de partidas')
        self.geometry('760x380')
        self.minsize(640, 300)
        self.transient(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._encabezado = ttk.Label(self, text='Partidas guardadas en este equipo')
        self._encabezado.grid(row=0, column=0, sticky='w', padx=12, pady=10)
        self._tabla = ttk.Treeview(self, columns=('titulo', 'actualizacion', 'creacion'),
                                   show='headings', selectmode='browse')
        for columna, texto, ancho in (('titulo', 'Título', 350),
                                      ('actualizacion', 'Último guardado', 170),
                                      ('creacion', 'Creación', 170)):
            self._tabla.heading(columna, text=texto)
            self._tabla.column(columna, width=ancho, minwidth=100,
                               stretch=columna == 'titulo')
        self._tabla.grid(row=1, column=0, sticky='nsew', padx=(12, 0))
        self._barra = ttk.Scrollbar(self, orient='vertical', command=self._tabla.yview)
        self._barra.grid(row=1, column=1, sticky='ns', padx=(0, 12))
        self._tabla.configure(yscrollcommand=self._barra.set)
        self._estado = ttk.Label(self)
        self._estado.grid(row=2, column=0, sticky='w', padx=12, pady=6)
        self._controles = ttk.Frame(self)
        self._controles.grid(row=3, column=0, columnspan=2, sticky='ew', padx=12, pady=(0, 12))
        self._boton_abrir = ttk.Button(self._controles, text='Abrir', command=self._abrir)
        self._boton_eliminar = ttk.Button(self._controles, text='Eliminar', command=self._eliminar)
        self._boton_guardar = ttk.Button(self._controles, text='Guardar partida actual',
                                         command=lambda: self._guardar(False))
        self._boton_copia = ttk.Button(self._controles, text='Guardar copia',
                                       command=lambda: self._guardar(True))
        self._boton_cerrar = ttk.Button(self._controles, text='Cerrar', command=self.destroy)
        for columna, boton in enumerate((self._boton_abrir, self._boton_eliminar,
                                         self._boton_guardar, self._boton_copia, self._boton_cerrar)):
            boton.grid(row=0, column=columna, padx=(0, 6))
        self._tabla.bind('<<TreeviewSelect>>', self._actualizar_controles)
        self._tabla.bind('<Double-1>', self._abrir_con_raton)
        self._tabla.bind('<Return>', lambda evento: self._abrir())
        self.bind('<Escape>', lambda evento: self.destroy())
        self.refrescar()
        self.grab_set()

    def refrescar(self) -> None:
        seleccion = self._tabla.selection()
        try:
            resumenes = self._repositorio.listar_partidas()
        except (OSError, sqlite3.Error, ValueError) as error:
            messagebox.showerror(parent=self, title='No se pudo consultar la biblioteca', message=str(error))
            self._actualizar_controles()
            return
        self._resumenes = {str(resumen.id_partida): resumen for resumen in resumenes}
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        for clave, resumen in self._resumenes.items():
            self._tabla.insert('', 'end', iid=clave, values=(
                resumen.titulo,
                resumen.fecha_actualizacion.astimezone().strftime('%d/%m/%Y %H:%M'),
                resumen.fecha_creacion.astimezone().strftime('%d/%m/%Y %H:%M'),
            ))
        if self._resumenes:
            clave = seleccion[0] if seleccion and seleccion[0] in self._resumenes else next(iter(self._resumenes))
            self._tabla.selection_set(clave)
            self._tabla.focus(clave)
        self._estado.configure(text=f'{len(resumenes)} partidas' if resumenes else 'Todavía no hay partidas guardadas.')
        self._actualizar_controles()

    def _actualizar_controles(self, evento=None) -> None:
        estado = 'normal' if self._tabla.selection() else 'disabled'
        self._boton_abrir.configure(state=estado)
        self._boton_eliminar.configure(state=estado)
        guardado = 'normal' if self._puede_guardar() else 'disabled'
        self._boton_guardar.configure(state=guardado)
        self._boton_copia.configure(state=guardado)

    def _abrir(self) -> None:
        seleccion = self._tabla.selection()
        if seleccion and self._abrir_partida(self._resumenes[seleccion[0]]):
            self.destroy()

    def _abrir_con_raton(self, evento) -> None:
        fila = self._tabla.identify_row(evento.y)
        if fila:
            self._tabla.selection_set(fila)
            self._abrir()

    def _guardar(self, nueva_copia: bool) -> None:
        guardada = self._guardar_partida(nueva_copia)
        # El diálogo de título toma el grab y lo libera al cerrarse.
        self.grab_set()
        if guardada:
            self.refrescar()

    def _eliminar(self) -> None:
        seleccion = self._tabla.selection()
        if seleccion and self._eliminar_partida(self._resumenes[seleccion[0]]):
            self.refrescar()
