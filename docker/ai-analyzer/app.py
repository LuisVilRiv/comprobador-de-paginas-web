import logging

from analyzer import AIContentAnalyzer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Configurar logs
logger = logging.getLogger("ai_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI Web Page Analyzer Microservice",
    description="Microservicio local de IA para el análisis semántico y de calidad de páginas web.",
    version="1.0.0",
)

# Inicializar el analizador
analyzer = AIContentAnalyzer()


@app.on_event("startup")
def startup_event():
    logger.info("⏳ Inicializando modelos semánticos en el arranque de la aplicación...")
    analyzer._load_model()
    if analyzer.enable_strong_fallback:
        analyzer._load_strong_fallback_model()
    logger.info("✓ Todos los modelos se cargaron e inicializaron exitosamente.")


class AnalysisRequest(BaseModel):
    html: str = Field(..., description="Contenido HTML completo de la página web.")
    url: str = Field(..., description="URL de la página web analizada.")
    status_code: int = Field(200, description="Código de estado HTTP obtenido en la petición.")
    metadata: dict | None = Field(None, description="Metadatos adicionales del scraping.")


class AnalysisResponse(BaseModel):
    is_inoperative: bool = Field(..., description="Indica si la página está inoperativa (404, 500, parking, etc.).")
    inoperative_reason: str | None = Field(None, description="Razón detallada de la inoperatividad.")
    confidence: float = Field(..., description="Nivel de confianza en la predicción semántica (0.0 a 1.0).")
    has_spam: bool = Field(..., description="Indica si se detectó spam o keyword stuffing.")
    has_malicious_content: bool = Field(..., description="Indica si se detectó contenido malicioso o no apto.")
    has_incoherent_content: bool = Field(
        ..., description="Indica si el contenido de texto es incoherente o autogenerado."
    )
    detected_language: str = Field(..., description="Idioma detectado de la página (código de 2 letras).")
    quality_score: int = Field(..., description="Puntuación aproximada de calidad semántica (5 a 100).")
    issues: list[str] = Field(..., description="Lista de problemas semánticos y de contenido detectados.")
    warnings: list[str] = Field(..., description="Lista de advertencias menores detectadas.")


@app.get("/health", summary="Obtener estado de salud del servicio")
def health_check():
    """
    Endpoint de comprobación de salud que indica si el servicio FastAPI está
    operativo y si el modelo de HuggingFace ya ha sido cargado en memoria.
    Retorna 503 Service Unavailable si los modelos aún no están listos.
    """
    model_loaded = analyzer.model is not None
    if not model_loaded:
        raise HTTPException(
            status_code=503,
            detail="Los modelos de IA aún se están cargando en memoria."
        )
    return {
        "status": "healthy",
        "model_loaded": True,
        "device": "cpu",
        "model_name": "paraphrase-multilingual-MiniLM-L12-v2",
    }


@app.post("/analyze", response_model=AnalysisResponse, summary="Analizar semánticamente el contenido HTML")
def analyze_page(payload: AnalysisRequest):
    """
    Endpoint principal para realizar el análisis semántico en profundidad del HTML.
    Limpia el contenido, calcula similitudes de embeddings y detecta problemas de calidad.
    """
    try:
        logger.info("📥 Petición de análisis recibida para URL: %s", payload.url)
        result = analyzer.analyze(
            html=payload.html, url=payload.url, status_code=payload.status_code, metadata=payload.metadata
        )
        logger.info("✓ Análisis finalizado para %s. Score de Calidad: %d", payload.url, result["quality_score"])
        return result
    except Exception as e:
        logger.exception("Error durante el análisis semántico de la página:")
        raise HTTPException(status_code=500, detail=f"Error interno en el analizador de IA: {str(e)}") from e
