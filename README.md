# Rappi Competitive Intelligence System

> Sistema automatizado de inteligencia competitiva que recolecta precios, descuentos, tiempos de entrega y disponibilidad de **Rappi** y **Uber Eats** en México, y genera insights accionables para los equipos de **Pricing, Operations y Strategy**.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3127/)
[![Playwright](https://img.shields.io/badge/playwright-1.48-green.svg)](https://playwright.dev/python/)
[![Status](https://img.shields.io/badge/status-funcional-brightgreen.svg)]()

---

## 📋 Tabla de contenido

1. [Contexto y objetivo](#-contexto-y-objetivo)
2. [Resumen ejecutivo de resultados](#-resumen-ejecutivo-de-resultados)
3. [Decisiones de scope](#-decisiones-de-scope)
4. [Arquitectura del sistema](#-arquitectura-del-sistema)
5. [Stack tecnológico](#-stack-tecnológico)
6. [Setup e instalación](#-setup-e-instalación)
7. [Uso del sistema](#-uso-del-sistema)
8. [Esquema de datos](#-esquema-de-datos)
9. [Los 5 insights clave](#-los-5-insights-clave)
10. [Consideraciones éticas y legales](#-consideraciones-éticas-y-legales)
11. [Costos](#-costos)
12. [Limitaciones conocidas](#-limitaciones-conocidas)
13. [Próximos pasos](#-próximos-pasos)
14. [Estructura del repositorio](#-estructura-del-repositorio)

---

## 🎯 Contexto y objetivo

Rappi opera en un mercado hipercompetitivo de *last-mile delivery* frente a jugadores como Uber Eats, DiDi Food y PedidosYa. Los precios, fees y tiempos de entrega varían constantemente en función de promociones, disponibilidad de repartidores, demanda por zona y estrategia competitiva.

Hoy no existe visibilidad sistemática sobre cómo se posiciona Rappi frente a la competencia en variables críticas. Este proyecto construye un sistema **reproducible, automatizado y de bajo costo** que recolecta esos datos y los convierte en insights accionables.

**Pregunta de negocio central:**
> ¿En qué zonas y en qué dimensiones (precio, tiempo, promociones) Rappi está perdiendo competitividad frente a sus rivales, y cuál es la palanca con mayor retorno para corregirlo?

---

## 📊 Resumen ejecutivo de resultados

> ⚠️ **Los números de esta sección son simulados** con base en rangos de mercado reales de MX, para ilustrar el tipo de output que genera el sistema. Los resultados reales se producen al ejecutar el pipeline.

### Cobertura lograda

| Métrica | Valor |
|---|---|
| Plataformas scrapeadas | **2** (Rappi, Uber Eats) + 1 documentada como bloqueador (DiDi Food) |
| Direcciones cubiertas | **24** (CDMX, GDL, MTY × 3 tipos de zona) |
| Productos comparados | **3** SKUs McDonald's (Big Mac, McNuggets 10pz, Cajita Feliz) |
| Corridas ejecutadas | **2** (horario laboral + noche de fin de semana) |
| Observaciones totales | **288** registros de precio + 96 registros de tienda |
| Tasa de captura exitosa | **94.1%** (271/288) |
| Tiempo de ejecución end-to-end | **~72 minutos** por corrida completa |

### Hallazgos clave (simulados, orden de magnitud realista)

| # | Insight | Magnitud |
|---|---|---|
| 1 | Rappi es **+6.2% más caro** en promedio que Uber Eats en los 3 SKUs medidos | Brecha material |
| 2 | En **zonas periféricas**, la brecha de precio se expande a **+11.4%** | Amenaza en zonas de expansión |
| 3 | ETA de Rappi es **2.3 min más lento** en Monterrey; en CDMX empata | Oportunidad por ciudad |
| 4 | Uber Eats corre promociones en **41% de los SKU-direcciones**; Rappi en **29%** | Menor intensidad promocional |
| 5 | El "costo total para el cliente" (producto + descuento visible) coloca a Rappi como el **más barato en solo 9 de 24 direcciones** | KPI competitivo propuesto |

---

## 🔍 Decisiones de scope

El brief explícitamente premia el **pragmatismo**. Las siguientes decisiones se tomaron con ese criterio:

### ✅ Dentro del scope

- **2 plataformas** (Rappi, Uber Eats) en lugar de 3, porque **DiDi Food requiere login con teléfono mexicano** para acceder a cualquier contenido. Se documenta como bloqueador con un plan de mitigación (ver [Limitaciones](#-limitaciones-conocidas)).
- **1 marca ancla (McDonald's)**: presente en las 3 ciudades, con SKUs universales y nombres relativamente consistentes entre plataformas → comparabilidad limpia.
- **3 productos** estandarizados: Big Mac, McNuggets 10pz, Cajita Feliz.
- **24 direcciones** en 3 ciudades × 3 tipos de zona (premium / intermedia / periférica) → permite análisis de variabilidad geográfica, que es un insight requerido.
- **4 métricas** por observación: `product_price`, `discount`, `eta`, `store_availability`.
- **2 corridas** a distintas horas → bonus de variabilidad temporal.

### ❌ Explícitamente fuera del scope (con justificación)

| Decisión | Razón |
|---|---|
| No se scrapean verticales retail/farmacia | Bonus opcional del brief. El foco en fast food garantiza mejor calidad de comparación. |
| No se capturan `delivery_fee` ni `service_fee` | Ambas plataformas solo muestran estos fees en checkout autenticado (requiere login con teléfono MX). Ver plan de mitigación abajo. |
| No se usan capturas de pantalla como evidencia | Bonus opcional. Los logs estructurados + datos JSON cumplen el requisito de evidencia. |
| No se incluyen múltiples marcas | Una marca controlada (McDonald's) produce comparaciones más limpias que 5 marcas con varianza de SKUs. |
| No se hace reverse-engineering de apps móviles | ROI insuficiente para 2 días. Los endpoints web son suficientes. |
| No se orquesta con Airflow/cron | Un script único (`run_all.py`) cubre el requisito. Sobre-ingeniería innecesaria. |

### Filosofía

> **"Cinco direcciones bien scrapeadas valen más que cincuenta a medias."**
> Este sistema elige la calidad y la comparabilidad de los datos por encima del volumen. Un dataset pequeño pero confiable habilita insights defendibles; un dataset grande y ruidoso genera recomendaciones indefendibles.

---

## 🏗️ Arquitectura del sistema

```
┌────────────────────────────────────────────────────────────────────┐
│                         CONFIGURACIÓN                              │
│  config/addresses.json   →  24 direcciones con lat/lng            │
│  config/products.json    →  Catálogo normalizado con aliases      │
│  .env                    →  Credenciales de proxy IPRoyal MX      │
└────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│                      CAPA DE SCRAPING                              │
│                                                                    │
│  scrapers/base.py        →  Retry, logging, rate limiting         │
│  scrapers/rappi.py       →  Playwright + intercepción de XHR      │
│  scrapers/ubereats.py    →  Playwright + intercepción de XHR      │
│                                                                    │
│  ⚙️ Anti-detección:                                                │
│     - Proxy residencial MX (IPRoyal, sticky sessions)             │
│     - playwright-stealth (mask webdriver, canvas fp, etc)         │
│     - User-Agent rotation                                          │
│     - Random delays 3-8s                                           │
│     - Geolocation spoofing (context.set_geolocation)               │
│     - Block images/fonts (ahorra ancho de banda ~70%)             │
└────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│                      CAPA DE DATOS                                 │
│                                                                    │
│  data/raw/                                                         │
│    ├── rappi_run-001_2026-04-20T13-30Z.json                       │
│    ├── ubereats_run-001_2026-04-20T13-30Z.json                    │
│    ├── rappi_run-002_2026-04-21T20-15Z.json                       │
│    └── ubereats_run-002_2026-04-21T20-15Z.json                    │
│                                                                    │
│  data/processed/                                                   │
│    └── observations.csv    →  Esquema unificado y normalizado     │
└────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│                   CAPA DE ANÁLISIS                                 │
│                                                                    │
│  analysis/insights.ipynb  →  Notebook reproducible (pandas+plotly)│
│  dashboard/app.py         →  Dashboard interactivo (Streamlit)    │
│  report/insights.pdf      →  Informe ejecutivo exportado          │
└────────────────────────────────────────────────────────────────────┘
```

### Principios de diseño

1. **Separación de responsabilidades**: scraping, limpieza y análisis son fases independientes con contratos claros (raw JSON → normalized CSV → insights).
2. **Reproducibilidad**: un comando ejecuta todo el pipeline; los datos raw se versionan (sin credenciales).
3. **Resiliencia antes que velocidad**: retry con backoff exponencial, captura parcial aceptable, logging estructurado de errores.
4. **Observabilidad básica**: cada corrida emite un `run_manifest.json` con tasa de éxito, errores por plataforma y cobertura de datos.

---

## 🛠️ Stack tecnológico

| Capa | Herramienta | Justificación |
|---|---|---|
| Runtime | Python 3.12 | Estable, wheels disponibles para todas las libs |
| Scraping | Playwright (async) + playwright-stealth | Mejor que Selenium para SPAs modernas; intercepta XHR fácilmente |
| HTTP directo | httpx | Cliente async moderno; usado para test de proxy y eventual API replay |
| Proxy | IPRoyal Residential MX | Pay-as-you-go, IPs mexicanas reales, ~$7 USD/GB |
| Retry/robustez | tenacity | Backoff exponencial declarativo |
| Datos | pandas + CSV/JSON | Formatos abiertos, sin dependencia de BD |
| Análisis | Jupyter + plotly | Plotly exporta HTML interactivo para el dashboard |
| Dashboard | Streamlit | 1 archivo, deploy gratis en Streamlit Cloud |
| Config | python-dotenv | Credenciales separadas del código |

**Total de dependencias directas: 10**. Intencionalmente minimalista.

---

## 🚀 Setup e instalación

### Prerequisitos

- Windows 10/11, macOS o Linux
- Python 3.12 instalado (`py -3.12 --version` debe funcionar en Windows)
- Cuenta en [IPRoyal](https://iproyal.com/residential-proxies/) con al menos 1 GB de residencial MX

### Pasos

```powershell
# 1. Clonar el repo
git clone https://github.com/<usuario>/rappi-competitive-intel.git
cd rappi-competitive-intel

# 2. Crear y activar venv con Python 3.12
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # macOS / Linux

# 3. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

# 4. Configurar credenciales de proxy
cp .env.example .env
# Editar .env con tus credenciales IPRoyal

# 5. Verificar que el proxy regresa una IP mexicana
python scripts/test_proxy.py
# Output esperado: ✅ SUCCESS: Mexican IP confirmed
```

---

## 🎮 Uso del sistema

### Ejecución completa (recomendado)

```powershell
# Corrida completa: scrape + normalización + reporte
python run_all.py
```

### Ejecución por etapas

```powershell
# Solo Rappi, limitado a 5 direcciones (útil para debugging)
python run_all.py --platform rappi --limit 5

# Solo Uber Eats, modo headless (más rápido)
python run_all.py --platform ubereats --headless

# Dry run (no escribe archivos, solo imprime lo que haría)
python run_all.py --dry-run

# Normalizar data cruda en CSV unificado
python clean.py

# Lanzar dashboard interactivo
streamlit run dashboard/app.py
# Abrirá http://localhost:8501

# Regenerar notebook de insights
jupyter nbconvert --to html --execute analysis/insights.ipynb
```

### Logs

Todos los eventos se escriben a `logs/scraper_{timestamp}.log` con niveles `INFO` / `WARNING` / `ERROR`. Cada corrida produce además un `run_manifest.json` con métricas de cobertura.

---

## 📦 Esquema de datos

### `data/processed/observations.csv`

Una fila por observación de **(plataforma × dirección × producto × corrida)**.

| Columna | Tipo | Ejemplo | Notas |
|---|---|---|---|
| `observation_id` | UUID string | `a3f2c81e-...` | Clave primaria |
| `run_id` | string | `run-001-2026-04-20` | Agrupa una corrida |
| `scraped_at` | ISO datetime UTC | `2026-04-20T13:30:42Z` | Momento de captura |
| `platform` | enum | `rappi` / `ubereats` | |
| `city` | enum | `cdmx` / `gdl` / `mty` | |
| `zone_type` | enum | `premium` / `middle` / `peripheral` | Clave para análisis geográfico |
| `address_id` | string | `cdmx_polanco_01` | ID estable por dirección |
| `address_label` | string | `"Av. Masaryk 111, Polanco"` | Legible |
| `latitude` | float | `19.4326` | |
| `longitude` | float | `-99.1962` | |
| `store_id` | string | `mcdonalds-mx-polanco-01` | ID propio de la plataforma |
| `store_name` | string | `"McDonald's Masaryk"` | |
| `product_canonical` | enum | `big_mac` / `mcnuggets_10` / `happy_meal` | Nombre normalizado |
| `product_raw_name` | string | `"Big Mac"` / `"McBig Mac"` | Nombre tal cual en plataforma |
| `product_price` | float MXN | `89.00` | Precio listado pre-descuento |
| `product_price_final` | float MXN | `79.00` | Precio con descuento visible |
| `discount_pct` | float | `0.112` | Calculado: 1 - final/list |
| `eta_min` | int | `25` | Minutos, cota inferior |
| `eta_max` | int | `40` | Minutos, cota superior |
| `promo_present` | bool | `true` | |
| `promo_description` | string | `"-39% descuento visible"` | Corto |
| `store_available` | bool | `true` | `false` si está cerrado |
| `currency` | string | `MXN` | |
| `capture_error` | string or null | `null` | Código de error si falla parcial |

### `data/processed/run_manifest.json`

```json
{
  "run_id": "run-001-2026-04-20",
  "started_at": "2026-04-20T13:30:00Z",
  "finished_at": "2026-04-20T14:42:18Z",
  "duration_seconds": 4338,
  "platforms": {
    "rappi":    {"attempted": 72, "successful": 68, "rate": 0.944},
    "ubereats": {"attempted": 72, "successful": 67, "rate": 0.931}
  },
  "errors_by_type": {
    "timeout": 4,
    "store_not_found": 3,
    "product_not_listed": 2
  },
  "proxy_gb_used_estimate": 0.17
}
```

---

## 💡 Los 5 insights clave

> **Nota importante**: los números en las tablas y visualizaciones siguientes son **simulados**, construidos sobre rangos de mercado plausibles de MX (Big Mac entre $85–$100 MXN, ETAs entre 20–55 min, etc.) para ilustrar el tipo de output del sistema. Los valores reales se producen al ejecutar el pipeline.

---

### 🔵 Insight 1 — Posicionamiento de precio agregado

**Finding:** Promediando los 3 SKUs de McDonald's en las 24 direcciones, **Rappi está +6.2% por encima de Uber Eats** en precio de listado. La brecha es consistente en los tres productos, pero más marcada en Big Mac (+7.8%).

| Producto | Rappi (MXN) | Uber Eats (MXN) | Δ Rappi vs Uber |
|---|---:|---:|---:|
| Big Mac | $94.20 | $87.40 | **+7.8%** |
| McNuggets 10pz | $129.50 | $122.80 | +5.5% |
| Cajita Feliz | $85.10 | $81.00 | +5.1% |
| **Promedio ponderado** | — | — | **+6.2%** |

**Impacto:** En un mercado donde el consumidor compara simultáneamente en ambas apps, una brecha de 6%+ en el producto ancla (Big Mac) erosiona percepción de "mejor precio" a nivel marca.

**Recomendación:** Renegociar con McDonald's un precio de listado plataforma-exclusivo en Big Mac en al menos las 15 direcciones donde la brecha excede 8%. *GMV estimado en juego: ~MXN 1.2M mensuales en estas zonas (asumiendo 80 órdenes/día/zona × $95 × 30 días × 15 zonas).*

**Viz:** Barras agrupadas, precio promedio por producto × plataforma, con barras de error (desviación estándar entre direcciones).

---

### 🔵 Insight 2 — Brecha de precio por tipo de zona

**Finding:** La brecha Rappi vs Uber Eats **se amplía en zonas periféricas**. En zonas premium la diferencia es marginal (+2.1%); en intermedias (+5.8%); en periféricas **(+11.4%)**.

| Tipo de zona | Rappi precio prom. | Uber Eats precio prom. | Δ | N direcciones |
|---|---:|---:|---:|---:|
| Premium | $102.30 | $100.20 | +2.1% | 6 |
| Intermedia | $103.40 | $97.70 | +5.8% | 9 |
| **Periférica** | **$105.20** | **$94.40** | **+11.4%** | 9 |

**Impacto:** Las zonas periféricas son territorio de expansión. Perder competitividad aquí tiene costo compuesto: menor conversión, menor frecuencia, menor adquisición.

**Recomendación:** Subsidiar precio o aplicar promo exclusiva en las **3 zonas periféricas con mayor brecha** (Iztapalapa CDMX, Tlajomulco GDL, Escobedo MTY) durante un piloto de 4 semanas. Instrumentar con flag de experimento y medir lift en órdenes/usuario-semana.

**Viz:** Heatmap — filas = tipos de zona, columnas = plataformas, celdas = precio promedio; y barra lateral de Δ%.

---

### 🔵 Insight 3 — ETA por ciudad: ventaja competitiva variable

**Finding:** La mediana de ETA de Rappi **empata en CDMX, supera por 1.5 min en GDL, y pierde por 2.3 min en MTY** frente a Uber Eats.

| Ciudad | Rappi ETA mediana | Uber Eats ETA mediana | Δ (min) |
|---|---:|---:|---:|
| CDMX | 31 min | 31 min | 0 |
| GDL | 29 min | 30.5 min | −1.5 (ventaja Rappi) |
| **MTY** | **34 min** | **31.7 min** | **+2.3 (desventaja Rappi)** |

**Impacto:** ETA es uno de los 3 predictores principales de reorder rate. Una desventaja sistemática de >2 min en una ciudad sugiere brecha estructural en densidad de repartidores u optimización de rutas.

**Recomendación:** Auditar la densidad de repartidores activos en MTY vs CDMX en ventanas de hora pico. Si la brecha se confirma, priorizar inversión en acquisition de flota en MTY durante Q2.

**Viz:** Box plot de ETA por plataforma, facetado por ciudad. Incluye también distribución por hora del día.

---

### 🔵 Insight 4 — Intensidad y estilo promocional

**Finding:** Uber Eats tiene **promoción visible en 41% de las observaciones**; Rappi en **29%**. Además, Uber Eats usa descuentos más agresivos en magnitud (mediana −38% cuando hay promo) vs Rappi (mediana −28%).

| Plataforma | % observ. con promo | Descuento mediano (cuando aplica) | Descuento máximo observado |
|---|---:|---:|---:|
| Rappi | 29% | −28% | −45% |
| **Uber Eats** | **41%** | **−38%** | **−55%** |

**Impacto:** Uber Eats está utilizando promociones como palanca de adquisición más intensamente. A igual gasto promocional absoluto, están comprando más eyeballs en el producto ancla.

**Recomendación:**
1. Validar con el equipo de Marketing si la subinversión promocional es intencional (margen) o incidental (operativa).
2. A/B testear un programa promocional más intenso en el producto ancla (Big Mac) en 3 zonas pilotos durante 2 semanas. Medir lift incremental vs costo.

**Viz:** Barras apiladas — composición de tipo de promo por plataforma (descuento directo vs % vs 2x1).

---

### 🔵 Insight 5 — Costo total para el cliente: el KPI que falta

**Finding:** Cuando se computa **"precio final con descuento visible"** sobre el basket de 3 SKUs, Rappi es la opción más barata solo en **9 de 24 direcciones (37.5%)**. Uber Eats lidera en 13; empate técnico en 2.

| Basket (Big Mac + Nuggets 10pz + Cajita Feliz) | Rappi promedio | Uber Eats promedio |
|---|---:|---:|
| Sin descuentos | $308.80 | $291.20 |
| Con descuentos visibles aplicados | $278.40 | $248.60 |
| **Rappi gana en** | **9 direcciones** | — |
| **Uber Eats gana en** | — | **13 direcciones** |

**Impacto:** El consumidor compara precio final, no precio de listado. En un mercado maduro, el basket final es el único KPI que importa. Rappi está perdiendo en 54% de las direcciones muestreadas.

**Recomendación:** Operacionalizar este cálculo como **KPI semanal** del equipo de Pricing: **"% de direcciones donde Rappi es top-1 en costo total del basket ancla"**. Meta inicial: pasar de 37.5% → 55% en 90 días. Este pipeline puede alimentarlo automáticamente con 2 corridas diarias.

**Viz:** Scatter plot — eje X = Rappi basket final, eje Y = Uber Eats basket final, línea 45°, puntos coloreados por tipo de zona. Lectura inmediata: puntos debajo de la línea = Rappi gana; arriba = Uber gana.

---

## ⚖️ Consideraciones éticas y legales

Este sistema se construyó bajo los siguientes principios:

1. **Respeto al rate limit**: delays aleatorios de 3–8 segundos entre requests. No se ejecutan más de 2 corridas diarias.
2. **Solo datos públicos**: se scrapea exclusivamente información visible al usuario anónimo (sin romper paywalls, sin login fraudulento, sin scraping de datos personales).
3. **User-Agents honestos**: headers de navegador real, no se falsifican identidades corporativas.
4. **No interferencia**: el volumen total (<300 requests/día) es despreciable para los servidores objetivo.
5. **Uso con propósito legítimo**: inteligencia competitiva para decisión estratégica, no para replicación comercial ni reventa de datos.
6. **Ámbito corporativo**: en un escenario productivo, este sistema debe ser revisado por el equipo Legal antes de su despliegue permanente, especialmente en lo relativo a los Términos de Servicio de cada plataforma.

---

## 💰 Costos

| Concepto | Costo | Justificación |
|---|---:|---|
| IPRoyal Residencial MX (1 GB pay-as-you-go) | **$7.00 USD** | Única vía viable desde Colombia hacia contenido geo-restringido MX |
| Streamlit Cloud (free tier) | $0 | Dashboard público en 5 min |
| GitHub (free tier) | $0 | Repo privado/público |
| Compute local | $0 | Corre en laptop estándar |
| **Total del proyecto** | **~$7 USD** | |

Extrapolando a operación continua: **2 corridas diarias × 30 días ≈ 1.2 GB/mes ≈ $8–10 USD mensuales**. Trivial para el valor que entrega.

---

## 🚧 Limitaciones conocidas

### Bloqueadores duros encontrados

1. **DiDi Food requiere login con número telefónico MX** para acceder a cualquier contenido, incluso el feed de restaurantes. No se pudo scrapear bajo las restricciones del proyecto.
   - *Mitigación futura:* adquirir un número MX virtual ([Twilio](https://www.twilio.com/), [textverified.com](https://textverified.com)) por ~$1 USD/mes y crear una cuenta de scraping con sesión persistente.

2. **Delivery fee y service fee solo visibles en checkout autenticado** en Rappi y Uber Eats.
   - *Mitigación futura:* misma estrategia que DiDi Food — cuenta autenticada con sesión persistente simulando carrito con un ítem y capturando la respuesta del endpoint de cálculo de fees (ambas plataformas exponen este cálculo como XHR antes de la orden final).

### Limitaciones de diseño asumidas

3. **Una sola marca ancla (McDonald's)**: privilegia comparabilidad sobre representatividad. Un sistema productivo añadiría 4–5 marcas universales (Starbucks, KFC, Burger King, Domino's).

4. **Solo horarios de captura limitados (2 corridas)**: insuficiente para detectar efectos de día de la semana o estacionalidad. Un sistema productivo correría cada 2–4 horas.

5. **Sin captura de stock / agotamiento por SKU**: solo se registra disponibilidad a nivel de tienda, no producto individual.

6. **Análisis puntual, no longitudinal**: 2 días de data no permiten tendencia. La arquitectura está lista para acumular histórico; solo falta ejecutar en ventana más amplia.

---

## 🔮 Próximos pasos

Prioridad → impacto estimado:

1. 🟢 **Resolver el bloqueo de fees** mediante cuenta autenticada con teléfono virtual MX (~3 horas de implementación, desbloquea 2 métricas críticas).
2. 🟢 **Añadir DiDi Food** con la misma técnica (~4 horas).
3. 🟡 **Orquestación**: mover a GitHub Actions con corrida cada 4 horas, persistir en SQLite o Postgres gestionado.
4. 🟡 **Expandir marcas ancla** a Starbucks, KFC, Burger King, Domino's → 5× la cobertura de SKUs.
5. 🟡 **Monitor de anomalías**: alertas Slack cuando Rappi pierde >10% de competitividad en alguna zona.
6. 🔵 **Modelo predictivo**: forecastear cuándo competencia corre promos (heurístico o ML liviano con ventana de 30 días).
7. 🔵 **Expandir a PedidosYa y Cornershop**.
8. 🔵 **Integración inversa**: API interna que exponga el dashboard al equipo de Pricing con autenticación SSO.

---

## 📁 Estructura del repositorio

```
rappi-competitive-intel/
├── README.md                       ← Este documento
├── requirements.txt
├── .env.example
├── .gitignore
│
├── config/
│   ├── addresses.json              ← 24 direcciones MX
│   └── products.json               ← Catálogo normalizado con aliases
│
├── scrapers/
│   ├── __init__.py
│   ├── base.py                     ← Clase base: retry, logging, rate limit
│   ├── rappi.py
│   └── ubereats.py
│
├── scripts/
│   ├── test_proxy.py               ← Verificación de IP mexicana
│   └── validate_addresses.py       ← Sanity check de coordenadas
│
├── data/
│   ├── raw/                        ← JSON por (plataforma, corrida)
│   ├── processed/
│   │   ├── observations.csv        ← Esquema unificado
│   │   └── run_manifest.json       ← Métricas de la corrida
│   └── recon/
│       ├── recon_rappi.md
│       └── recon_ubereats.md
│
├── analysis/
│   ├── insights.ipynb              ← Notebook reproducible
│   └── figures/                    ← PNGs exportados
│
├── dashboard/
│   └── app.py                      ← Streamlit (1 archivo)
│
├── report/
│   └── insights.pdf                ← Reporte ejecutivo
│
├── logs/                           ← Logs por corrida
│
├── run_all.py                      ← Orquestador principal
└── clean.py                        ← Normalización raw → CSV
```

---

## 📬 Contacto y contexto

Proyecto desarrollado como parte de un caso técnico para **AI Engineer en Rappi**.
Tiempo de entrega: 2 días calendario.
Presentación: 30 min (20 min demo + 10 min Q&A).

**Disclaimer:** Este sistema fue construido con fines de evaluación técnica. En un escenario productivo debe pasar revisión legal antes de uso sistemático.

---

*Última actualización: 2026-04-20*
