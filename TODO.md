# TODO: Encapsular Query Params en Clases DTO

## Paso 1: Crear clases DTO en query_params.py
- [x] Crear SearchDayQueryParamsDTO con validaciones
- [x] Crear SearchIntervalQueryParamsDTO con validaciones
- [x] Crear RandomByDayQueryParamsDTO con validaciones
- [x] Crear RandomByIntervalQueryParamsDTO con validaciones

## Paso 2: Actualizar main.py
- [x] Actualizar endpoint /random para usar RandomByDayQueryParamsDTO
- [x] Actualizar endpoint PUT /random para usar RandomByDayQueryParamsDTO y RandomByIntervalQueryParamsDTO
- [x] Actualizar endpoint /search-day para usar SearchDayQueryParamsDTO
- [x] Actualizar endpoint /search-interval para usar SearchIntervalQueryParamsDTO

## Paso 3: Actualizar IVideoService y VideoService
- [x] Actualizar firmas de métodos en IVideoService
- [x] Actualizar firmas de métodos en VideoService
- [x] Agregar métodos DTO en VideoService
- [x] Mantener métodos legacy para compatibilidad

## Paso 4: Verificar Repository
- [x] Verificar que VideoRepository no requiera cambios (ya trabaja con datetime)

## Verificación
- [ ] Verificar sintaxis con python -m py_compile

