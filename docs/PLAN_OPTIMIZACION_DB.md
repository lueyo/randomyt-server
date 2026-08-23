# Plan de optimización de base de datos (`/random` y búsquedas)

## Contexto

La colección `videos` de MongoDB está creciendo y las consultas de `/random` y de búsqueda
están empeorando linealmente con el tamaño de la base. Tras revisar el código, el problema no
es la lógica sino que **la base no tiene ningún índice** (solo el implícito de `_id`) y **cada
request de búsqueda recalcula el total con un `count_documents` con collation**, que escanea
toda la colección.

### Diagnóstico

| # | Problema | Dónde | Impacto |
|---|----------|-------|---------|
| 1 | Cero índices: filtros por `upload_date`, `posted_date`, `tags` y todos los `.sort()` son *collection scans* | Toda la app | COLLSCAN en cada request; empeora al crecer la BD |
| 2 | `count_documents` con collation `es/strength-1` en cada request de búsqueda | `repository/VideoRepository.py:414` y `:501` | Recuento completo de la colección por cada página pedida |
| 3 | Búsqueda por título con `$regex` no anclado (equivalente a `LIKE '%q%'`) | `repository/VideoRepository.py:401`, `:472` | Ningún índice puede acelerarlo; siempre escanea |
| 4 | `$sample` tras `$match` por fecha en `/random`: sin índice, el match escanea toda la colección | `repository/VideoRepository.py:110-127`, `:285-289`, `:315-327`, `:357-365`, `:547-556` | `/random` con fechas lento |
| 5 | Dos clientes de Motor independientes para la misma URL | `db/client.py:4-5` | Dos pools de conexiones innecesarios |

### Restricciones acordadas

- **Los resultados deben ser idénticos**: se mantiene la semántica exacta del regex
  (substring, case-insensitive, accent-insensitive vía collation), la paginación offset y los
  contratos de respuesta.
- **Sin Atlas Search**: la base se migrará a otro servidor en el futuro, así que nada del plan
  puede depender de servicios propietarios de Atlas.
- El campo `results` (total) de las búsquedas puede estar desfasado hasta ~45 s (caché TTL),
  acordado. La lista de videos devuelta sigue siendo exacta.

---

## Cambios

### 1. Índices creados en hook de startup (mayor impacto)

**Archivo:** `main.py` (nuevo `@app.on_event("startup") async def ensure_indexes()`)
y nueva función auxiliar en `db/client.py` o `db/indexes.py`.

```python
@app.on_event("startup")
async def ensure_indexes():
    try:
        await db_client.videos.create_index([("upload_date", ASCENDING)])
        await db_client.videos.create_index([("posted_date", ASCENDING)])
        await db_client.videos.create_index([("tags", ASCENDING)])
        await db_tasks.tasks.create_index(
            [("completed_at", ASCENDING), ("date", ASCENDING)]
        )
    except Exception as e:
        print(f"No se pudieron crear los índices: {e}")
```

- `create_index` es **idempotente**: si ya existe, no hace nada. Sin costo en arranques
  posteriores.
- Envuelto en `try/except` con log: si falla la creación, el server arranca igual (degradado,
  no roto).

Índices y qué aceleran:

| Índice | Colección | Qué acelera |
|--------|-----------|-------------|
| `{upload_date: 1}` | `videos` | `/random?day/startDay/endDay` (el `$match` pasa de COLLSCAN a IXSCAN), `search-day`, `search-interval`, `/search` con fechas, y todos los `.sort()` por `upload_date` (elimina el sort en memoria) |
| `{posted_date: 1}` | `videos` | Ídem cuando `isPostedDate=true` |
| `{tags: 1}` | `videos` | Filtros `{"tags": {"$in": [...]}}` multikey |
| `{completed_at: 1, date: 1}` | `tasks` | `get_next_pending_task()` (bot/procesador de cola) |

**Nota sobre collation:** los índices se crean con collation por defecto y eso es correcto.
En MongoDB la collation solo afecta comparaciones de strings; los rangos y sorts por campos
fecha usan el índice igual aunque la query lleve `{"locale": "es", "strength": 1}`. Crear los
índices *con* esa collation sería contraproducente: las queries que no especifican collation
(p. ej. los pipelines de `/random`) dejarían de usarlos.

**Nota sobre el regex:** un `$regex` no anclado nunca puede usar índices; es una limitación
estructural, no de este plan. Su costo queda mitigado con la caché de counts (cambio 2) porque
el regex se ejecuta dos veces por request (count + find). La lista de la página ya solo
escanea hasta llenar el `limit` tras aplicar el resto de filtros indexados.

### 2. Caché TTL para `count_documents`

**Dependencia:** añadir `cachetools` a `pyproject.toml` y `requirements.txt`.

**Archivo:** `repository/VideoRepository.py`

- Un único `TTLCache(maxsize=1024, ttl=45)` a nivel de módulo.
- Clave de caché: JSON canónico (ordenado) de `filter_query + collation`.
- Aplica a las 4 búsquedas: `search_by_title`, `search_by_day`, `search_by_interval`,
  `search_combined`. El resto del método no cambia.

```python
from cachetools import TTLCache
import json

_count_cache = TTLCache(maxsize=1024, ttl=45)

def _cache_key(filter_query: dict, collation: dict) -> str:
    return json.dumps({"f": filter_query, "c": collation},
                      default=str, sort_keys=True)

# en cada search_*:
key = _cache_key(filter_query, collation)
total = _count_cache.get(key)
if total is None:
    total = await db_client.videos.count_documents(filter_query, collation=collation)
    _count_cache[key] = total
```

Efecto: la segunda petición de la misma búsqueda dentro de 45 s no ejecuta ningún count;
saltarse el scan completo es el mayor alivio de CPU en Atlas/servidor cuando hay tráfico
repetido sobre las mismas búsquedas (patrón típico: paginar resultados).

### 3. Caché de `GET /find/{video_id}` y `GET /count`

**Archivo:** `repository/VideoRepository.py`

- `get_video_by_id`: caché `_video_cache = TTLCache(maxsize=4096, ttl=3600)` indexada por
  ID de video. Seguro porque la colección `videos` es *insert-only* (no hay `update_one`
  sobre ella), así que un video nunca cambia una vez insertado. Los IDs inexistentes **no**
  se cachean: si el video se inserta más tarde, la siguiente petición ya lo encuentra.
- `count_videos`: caché `_total_count_cache = TTLCache(maxsize=8, ttl=10)` con clave única
  `"all"`. TTL corto (10 s) a propósito porque el total puede crecer con cada video nuevo
  insertado por el procesador de tareas.

### 4. Un solo cliente de Motor

**Archivo:** `db/client.py`

```python
from motor.motor_asyncio import AsyncIOMotorClient
from common.config import DATABASE_URL

_client = AsyncIOMotorClient(DATABASE_URL)
db_client = _client.get_database("randomyt_db")
db_tasks = _client.get_database("randomyt_cola")
```

Un único pool de conexiones compartido por ambas bases. Sin cambio de comportamiento.

### 5. Lo que NO se cambia

- Semántica del regex ni collation → mismos resultados.
- Paginación offset (`skip`/`limit`) → mismo contrato de API.
- Estructura de respuestas (`PageModel`, DTOs).
- Lógica de `/random`: `$sample` se queda tal cual; gana velocidad sola gracias a los índices.
- Nada dependiente de Atlas (ver siguiente sección).

---

## Verificación

1. Arrancar el server y comprobar en el log que `ensure_indexes` corre sin errores.
2. Confirmar índices: `db.videos.getIndexes()` en mongosh debe listar los 3 nuevos.
3. Confirmar uso de índices con explain antes/después:

   ```js
   db.videos.find({upload_date: {$gte: ISODate("2010-01-01"), $lte: ISODate("2010-01-02")}})
            .explain("executionStats").executionStats.stage  // COLLSCAN -> IXSCAN
   ```
4. Comparar respuestas JSON idénticas (excepto posible desfase de `results` ≤ 45 s) de
   `/random`, `/random` PUT con exclusiones, `/search-day`, `/search-interval`,
   `/search-title` y `/search` contra el estado actual.
5. Medir latencia de las búsquedas repetidas (segunda llamada debe evitar el count).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| La creación de índices en arranque bloquea el server si la colección es enorme | `create_index` en background es rápido en versiones modernas de Mongo (4.2+); si falla, el try/except deja el server arriba |
| Total desfasado en caché durante 45 s | Acordado; si molesta, bajar `ttl` o invalidar en los inserts de tareas |
| Memoria de la caché | `maxsize=1024` acota la memoria; claves son strings pequeños |

---

## Fuera de alcance (opciones futuras, documentadas a propósito)

Como hay migración de servidor prevista y se descarta Atlas Search:

- **Índice de texto estándar de MongoDB (`$text`)**: disponible también en Mongo
  Community/self-hosted, sobrevive a la migración. Cambia la semántica (busca palabras
  completas, no substrings), así que requeriría decidir si el cambio de resultados es
  aceptable. Es la primera opción a evaluar si el regex pesa demasiado tras la migración.
- **Motor externo de búsqueda** (OpenSearch/Meilisearch): solo si el volumen lo justifica.
- **Paginación keyset (cursor)** en vez de offset: elimina el coste de `skip` profundos;
  cambiaría el contrato de la API, así que requiere decisión de producto aparte.
