package com.trycore.parametros.core

/** ¿Está quien llama mapeado a alguno de estos actores en algún proceso desplegado? (adaptador de processAPI) */
interface MapeoDeActores {
    boolean mapeadoAAlguno(Collection<String> actores)

    /** ¿Está mapeado a algún actor, de algún proceso desplegado, que NO sea de estos? */
    boolean mapeadoAAlgunoFueraDe(Collection<String> actores)
}
