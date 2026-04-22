# 🛵 Rappi Competitive Intelligence System

Sistema automatizado de inteligencia competitiva que compara **precios, tiempos de entrega y promociones** de Rappi vs Uber Eats en **24 direcciones** de México (CDMX, Guadalajara, Monterrey), generando insights accionables para los equipos de Pricing, Operations y Strategy.

**🔗 Demo en vivo:** [rappi-competitive-intel.streamlit.app](https://rappi-competitive-insights-a7wa6cj56bbjw9ngay2vnu.streamlit.app/)

---

## 🎯 TL;DR — Top findings

| # | Hallazgo | Data |
|---|---|---|
| 1 | **Rappi entrega 2.5× más rápido que Uber Eats.** Mediana de ETA 12 min vs 35 min (+66% de ventaja). | 291 observaciones, 2 ventanas temporales |
| 2 | **En zonas premium, Rappi es ~3% más caro que Uber Eats.** Worst case: MTY San Pedro (+11%). En zonas periféricas, Rappi es ~2.5% más barato. | 65 pares directamente comparables |
| 3 | **En Monterrey late-night (11 PM), Uber Eats no tiene Big Mac en 7 de 8 tiendas** (menú "McNoches" restringido). Rappi sí — ventana nocturna es un *moat* operacional. | n=16 MTY Big Mac obs |
| 4 | **Rappi muestra promociones 1.8× más seguido que Uber Eats** (89% vs 51%), pero el 80% es la misma recurrente ("Envío gratis primera orden"). Oportunidad de diversificar el portafolio. | 291 obs, 2 runs |
| 5 | El producto McNuggets 10 pz es ~5% más barato en Rappi; Big Mac y Cajita Feliz son ~3% más caros. Pricing icónico vs pricing de ticket medio. | n=65 pares |

---

## 🏗️ Arquitectura

```text
config/                  Direcciones, productos, McDonald's UUIDs
scrapers/
├── base.py              Proxy manager, logging, schema unificado
├── product_matcher.py   Normaliza nombres de productos entre plataformas
├── rappi.py             POST directo a /restaurant-bus/store/brand/id/706
└── ubereats.py          Playwright bootstrap + httpx replay vía getStoreV1
run_all.py               Orquestador — 24 direcciones × 2 plataformas
scripts/retry_failed.py  Re-run solo de direcciones que fallaron
analysis/
├── core.py              Funciones puras: load, compute, chart (0 UI)
└── insights.py          Notebook/script runner (5 insights)
dashboard/app.py         Streamlit dashboard (6 tabs, reusa analysis/core)
data/
├── raw/                 Dumps JSON por observación (para auditoría)
└── processed/           CSVs unificados por corrida
```
**Principio de diseño:** `analysis/core.py` expone funciones puras (sin UI, sin side effects). Tanto el notebook como el dashboard de Streamlit las consumen. Cero duplicación, una sola fuente de verdad.

---

## 🛠️ Stack

- **Scraping:** Python 3.12 + Playwright (sólo para bootstrap de cookies en Uber Eats) + `httpx` (replays de API)
- **Anti-bot:** IPRoyal residential proxy (MX geo-targeted, city-level rotation por sesión)
- **Datos:** pandas 2.2, Parquet/CSV
- **Viz:** Plotly (HTML + PNG exportables)
- **Dashboard:** Streamlit (deploy gratis en Streamlit Cloud)
- **Retry:** tenacity con exponential backoff

**Costo total de infraestructura: ~$7 USD** (1 GB de proxy residencial — consumido <30%).

---

## 🔬 Enfoque técnico

### 1. API replay sobre scraping de HTML
Ambas plataformas exponen endpoints JSON para el menú de una tienda (Rappi `POST /restaurant-bus/store/brand/id/706`; Uber Eats `POST /_p/api/getStoreV1`). En lugar de renderizar HTML con Playwright para cada una de las 24 direcciones (lento, frágil), **replayeamos el llamado HTTP con `httpx`** — 10× más rápido, 10× menos bandwidth de proxy.

Playwright se usa **solo una vez** para hacer bootstrap de cookies de sesión en Uber Eats (cookies `cf_clearance`, `uev2.id.session_v2`, `dId` requeridas por el CSRF de Uber).

### 2. Una dirección → múltiples McDonald's
- **Rappi:** `brand/id/706` (McDonald's) + lat/lng en el body → la API de Rappi devuelve la tienda más cercana. Una llamada, todas las direcciones.
- **Uber Eats:** requiere `storeUuid` en el body. Pre-mapeamos 6 McDonald's en MX (2 por ciudad) y para cada dirección calculamos la tienda más cercana por haversine.

### 3. Esquema de observación unificado
Una fila por (plataforma × dirección × producto × corrida). Long format para `groupby` trivial en pandas. Incluye `zone_type` (premium/media/periférica) para análisis de variabilidad geográfica, y `run_id` para análisis temporal.

### 4. Defensas operacionales
- Retry con exponential backoff (tenacity, 3 intentos)
- Dumps JSON crudos por observación (auditoría + debug)
- Validación de UUIDs al cargar config (falla rápido si `store_uuid` no es un UUID válido)
- Rate limiting randomizado (3–8s entre requests)
- Rotación de sticky sessions por dirección (IPRoyal `session-xxx_lifetime-10m`)
- Script de retry que sólo re-ejecuta las direcciones con error

---

## 📊 Dataset capturado

| Métrica | Valor |
|---|---|
| Observaciones totales | **308** |
| Observaciones con precio válido | **291** |
| Plataformas | Rappi, Uber Eats |
| Ciudades | CDMX, Guadalajara, Monterrey |
| Tipos de zona | premium, media, periférica |
| Productos estandarizados | Big Mac, McNuggets 10 pz, Cajita Feliz |
| Direcciones únicas | 24 (8 por ciudad, 2–3 por zona) |
| Ventanas temporales | 2 (late night CDMX ~00:18 + lunch rush ~13:47) |
| Pares comparables (apples-to-apples) | **65** |
| Tasa de éxito Rappi | 100% (Run 2) / 92% (Run 1) |
| Tasa de éxito Uber Eats | 79% (Run 2) / 100% (Run 1 con retries) |

---

## 🚀 Cómo reproducir

### Requisitos
- Python 3.12+
- Windows / Linux / macOS
- Proxy residencial mexicano (IPRoyal recomendado, ~$7 USD / GB)

### Setup
```bash
git clone <este-repo>
cd rappi-competitive-intel
python -m venv venv
# Windows:  .\venv\Scripts\Activate.ps1
# Linux:    source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Editar .env con tus credenciales de proxy
```

### Ejecutar
```bash
# Corrida completa (24 direcciones × 2 plataformas, ~15 min)
python run_all.py

# Solo una plataforma
python run_all.py --platform rappi

# Modo prueba (3 direcciones)
python run_all.py --limit 3

# Retry de direcciones que fallaron en una corrida
python -m scripts.retry_failed data/processed/observations_run_<id>.csv

# Análisis + export de insights
python -m analysis.insights

# Dashboard local
streamlit run dashboard/app.py
```

---

## ⚠️ Limitaciones conocidas (documentadas explícitamente)

1. **DiDi Food excluida.** Su sitio redirige forzosamente a login antes de mostrar cualquier dato. Implementar scraping autenticado (SMS verification de número MX) fue evaluado y descartado: ~4 horas de desarrollo adicional vs cobertura limitada, fuera del budget de 2 días.

2. **Delivery fee y service fee requieren login.** Ambas plataformas sólo exponen estos costos en el checkout post-login. Estos insights quedan ausentes del análisis actual. *Next step:* sesión autenticada con número MX verificado para completar el esquema.

3. **Tokens de autenticación de Rappi tienen TTL corto** (~12 h). Documentado cómo refrescarlos manualmente. *Next step:* bootstrap de token desde Playwright para rotación automática.

4. **504 Gateway Timeouts en Uber Eats Hidalgo (MTY) durante hora pico.** No es un problema de scraping — es timeout del backend de Uber. Documentado como señal de confiabilidad de la plataforma competidora.

5. **No hay login en Uber Eats** → no se capturan promos personalizadas ni cupones gated. La tasa del 51% de promos visibles es un piso, no un techo.

6. **Sample size:** 24 direcciones × 2 corridas. Suficiente para identificar patrones direccionales pero no para inferencia estadística estricta (IC 95% requeriría ~100+ direcciones).

---

## 🔮 Next steps (si tuviera 1 semana más)

1. **Auth flow para Rappi + Uber Eats** (número MX verificado) → captura delivery_fee, service_fee, promo personalizado
2. **Productización como KPI recurrente:** GitHub Actions corriendo 3× por semana → snapshot histórico → alertas cuando Rappi cae por debajo del top-2 en costo total por zona
3. **Escalar a retail + pharmacy** (Coca-Cola 500ml, paracetamol, pañales) — verticales bonus del brief
4. **Machine readable comparator:** endpoint REST que devuelve el delta competitivo por lat/lng en tiempo real, consumible por apps internas de Rappi

---

## 📁 Estructura de deliverables

- **`data/processed/observations_*.csv`** — Data raw exportable
- **`analysis/output/insight{1-5}_*.html`** — Gráficos Plotly interactivos
- **`analysis/output/insights_summary.json`** — Resumen estructurado para BI tools
- **Dashboard en vivo** — [https://rappi-competitive-insights-a7wa6cj56bbjw9ngay2vnu.streamlit.app/]
- **Este README** — overview ejecutivo + reproducibilidad

---

## 🧭 Consideración ética

El scraping se realizó sobre datos de menú públicamente visibles, respetando rate limits (3–8 s entre requests), con User-Agents identificables y sin intentar bypass de auth flows. Todo el análisis agrega datos a nivel de zona/ciudad; no se recolectaron datos personales de usuarios ni repartidores.

---

## 👤 Autor

Juan Camilo Herrera
Contacto: [wilchesch@hotmail.com] / [[LinkedIn](https://www.linkedin.com/in/juan-wilches/)]
