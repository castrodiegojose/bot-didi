# Didi

Lista del super para dos, por Telegram. Cuando marcan comida como comprada, manda 10 recetas.

## Ponerlo en marcha

1. En Telegram, abrí [@BotFather](https://t.me/BotFather) y mandá `/newbot`. Te da un token.
2. Copiá el ejemplo de entorno y pegá el token:

```bash
cp .env.example .env
```

3. Iniciá el bot:

```bash
python3 main.py
```

4. Los dos le escriben al bot por privado y quedan en la misma lista. El tercero que escriba no entra, salvo que uno de ustedes mande `salir`.

Dejá esa terminal abierta. Si la cerrás, el bot deja de contestar. La lista queda guardada en `data/household.json`.

## Cómo se habla

- `agrega leche y huevos`
- `comprar pan`
- `eliminar leche` o `borra el 2`
- `eliminar la lista` (borra lo que falta comprar)
- `lista`, y tocá cada casilla para ir marcando lo que comprás. Tocá de nuevo para destildar
- `ya compré pollo`
- `ya compramos todo`
- Un número del 1 al 10 para ver la receta

También andan `/agregar`, `/sacar`, `/lista`, `/compre` y `/ayuda`.

La limpieza (lavandina, detergente, papel higiénico) se marca comprada y no trae recetas.
