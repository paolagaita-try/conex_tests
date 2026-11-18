package com.trycore.parametros.core

/**
 * La tarea que da el ámbito de una lectura, vista por quien llama: en el runtime
 * la da un adaptador de processAPI. Devuelve [proceso: nombre de la definición, actividad: nombre del
 * flow node, actor: nombre del actor de la tarea, ejecutable: si quien llama puede ejecutarla], o null
 * si la tarea no existe o ya no está activa.
 *
 * Un formulario de instanciación no tiene tarea: su ámbito lo da la definición del proceso
 * ({@link #deLaInstanciacion}).
 */
interface Tareas {
    Map<String, Object> deLaTarea(long id)

    /**
     * La definición de proceso que abre un formulario de instanciación, vista por quien llama: [proceso: nombre de la
     * definición, actor: nombre del actor iniciador (null si no tiene: ninguna familia interna), ejecutable: si quien
     * llama puede iniciarla] (sin actividad: el ámbito es el del proceso), o null si no existe o no está activa.
     */
    Map<String, Object> deLaInstanciacion(long idDefinicion)
}
