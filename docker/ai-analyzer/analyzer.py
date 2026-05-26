import logging
import os
import re

import numpy as np
from bs4 import BeautifulSoup
from langdetect import DetectorFactory, detect
from transformers import pipeline

# Establecer semilla para langdetect de forma determinista
DetectorFactory.seed = 0

logger = logging.getLogger("ai_analyzer")
logging.basicConfig(level=logging.INFO)

# Configurar torch para CPU only
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Anclas semánticas para la detección de errores (inoperatividad)
ERROR_ANCHORS = {
    "404 HTML": [
        "404 page not found error",
        "error 404 página no encontrada",
        "el recurso solicitado no existe",
        "404 not found requested url not found",
    ],
    "500 HTML": [
        "500 internal server error connection failure",
        "error interno del servidor 500",
        "error al establecer una conexion con la base de datos",
        "database connection failed database error",
    ],
    "parking domain": [
        "this domain is parked by hosting company godaddy cpanel dondoninio plesk",
        "dominio aparcado en plesk cuenta de hosting activada",
        "sitio web en venta comprar dominio",
    ],
    "maintenance page": [
        "website is under maintenance we will be back soon",
        "estamos en mantenimiento disculpe las molestias",
        "sitio temporalmente fuera de servicio por mantenimiento",
    ],
    "access denied": [
        "access denied 403 forbidden cloudflare ddos",
        "acceso denegado no tienes permisos para acceder",
        "please solve the captcha to continue connection blocked",
    ],
    "website suspended": [
        "website suspended hosting account suspended contact support",
        "cuenta suspendida por falta de pago servicio suspendido",
    ],
    "coming soon": [
        "coming soon website under construction stay tuned",
        "próximamente sitio web en desarrollo en construccion",
    ],
}

# Anclas semánticas de contenido técnico/educativo sobre HTTP y documentación.
EDUCATIONAL_ANCHORS = {
    "http_docs": [
        "http status code documentation rfc specification technical reference",
        "documentación técnica de códigos de estado http y semántica del protocolo",
        "este artículo explica el significado del código de estado http",
    ],
    "knowledge_article": [
        "encyclopedia article explaining concepts examples and references",
        "artículo informativo con definición, ejemplos y referencias",
        "developer documentation and standards reference material",
    ],
}

# Términos que aportan contexto de fallo real alrededor de códigos 4xx/5xx.
ERROR_CONTEXT_TERMS = (
    "error",
    "not found",
    "forbidden",
    "service unavailable",
    "internal server",
    "bad gateway",
    "gateway timeout",
    "acceso denegado",
    "pagina no encontrada",
    "página no encontrada",
    "no encontrada",
    "no disponible",
    "fuera de servicio",
    "mantenimiento",
    "temporalmente",
    "reintentar",
    "captcha",
    "cloudflare",
    "blocked",
    "suspendida",
    "suspended",
)

RUNTIME_ERROR_CUES = (
    "reload page",
    "back to previous page",
    "home page",
    "please try again later",
    "temporarily unable to service your request",
    "ray id",
    "request id",
    "maintenance downtime",
    "capacity problems",
)

# Términos frecuentes en páginas informativas/documentales que explican códigos HTTP.
EDUCATIONAL_CONTEXT_TERMS = (
    "codigo de estado",
    "código de estado",
    "http status",
    "rfc",
    "wikipedia",
    "enciclopedia",
    "documentacion",
    "documentación",
    "documentation",
    "definicion",
    "definición",
    "que es",
    "qué es",
    "ejemplo",
    "specification",
    "especificacion",
    "especificación",
)

EXPLANATORY_CUES = (
    "is a status code",
    "es un código de estado",
    "es un codigo de estado",
    "indicates that",
    "indica que",
    "defined in",
    "definido en",
    "semantics",
    "semántica",
    "specification",
    "especificación",
    "reference",
)

# Firmas fuertes de páginas de error reales (templates de servidor/CDN/WAF).
STRONG_ERROR_SIGNATURES = (
    "server error",
    "service temporarily unavailable",
    "the server is temporarily unable to service your request",
    "please try again later",
    "maintenance downtime",
    "capacity problems",
    "error_docs",
    "bad gateway",
    "gateway timeout",
    "temporarily unavailable",
    "too many requests",
    "rate limit exceeded",
    "origin is unreachable",
    "web server is down",
    "connection timed out",
    "request blocked",
    "access denied",
    "blocked by security",
    "cloudflare",
    "attention required",
)

# Anclas semánticas para contenido malicioso o no apto
MALICIOUS_ANCHORS = {
    "pornography": [
        "explicit sexual content pornography videos photos adult entertainment porn",
        "contenido sexual explícito pornografía erotismo sexo adultos",
    ],
    "violence": [
        "incitement to violence threats hate speech terrorist propagation firearms",
        "incitación a la violencia amenazas extremistas terrorismo armas",
    ],
    "phishing": [
        "scam phishing fake bank login credit card theft credentials steal",
        "estafa phishing robo de credenciales inicio de sesion falso",
    ],
    "gambling": [
        "online gambling casino betting slot machine play and win cash sports book",
        "apuestas en línea casino tragaperras poker ganar dinero",
    ],
    "malware": [
        "malware virus trojan download malicious software cracked program installer",
        "descarga de virus troyanos software malicioso instalador modificado",
    ],
    "seo_spam": [
        "buy cheap viagra online cialis generic prescription pharmacy best price replica watches",
        "comprar viagra barata farmacia online replicas de relojes lujo",
    ],
}


class AIContentAnalyzer:
    def __init__(self):
        self.model = None
        self.zero_shot_classifier = None
        self.cache_dir = os.environ.get("MODEL_CACHE_DIR", "/app/model_cache")
        self.enable_strong_fallback = os.environ.get("ENABLE_STRONG_AI_FALLBACK", "true").lower() == "true"
        self.strong_fallback_model = os.environ.get(
            "STRONG_FALLBACK_MODEL",
            "joeddav/xlm-roberta-large-xnli",
        )
        # Diccionarios para almacenar los embeddings precalculados de las anclas
        self.error_embeddings = {}
        self.educational_embeddings = {}
        self.malicious_embeddings = {}

    def _load_model(self):
        """Carga perezosa del modelo sentence-transformers en CPU."""
        if self.model is None:
            logger.info("⏳ Cargando modelo 'paraphrase-multilingual-MiniLM-L12-v2' en CPU...")
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2", cache_folder=self.cache_dir, device="cpu"
            )
            logger.info("✓ Modelo cargado correctamente.")
            self._precalculate_anchors()

    def _load_strong_fallback_model(self):
        """Carga perezosa del clasificador zero-shot para casos ambiguos."""
        if not self.enable_strong_fallback:
            return
        if self.zero_shot_classifier is None:
            logger.info("⏳ Cargando modelo de fallback fuerte: %s", self.strong_fallback_model)
            self.zero_shot_classifier = pipeline(
                task="zero-shot-classification",
                model=self.strong_fallback_model,
                device=-1,
            )
            logger.info("✓ Modelo de fallback fuerte cargado.")

    def _precalculate_anchors(self):
        """Precalcula los embeddings de todas las anclas semánticas al inicializar el modelo."""
        logger.info("⚙️ Precalculando embeddings para las anclas semánticas...")

        # Precalcular anclas de errores
        for category, sentences in ERROR_ANCHORS.items():
            self.error_embeddings[category] = self.model.encode(sentences, convert_to_numpy=True)

        # Precalcular anclas educativas/documentales
        for category, sentences in EDUCATIONAL_ANCHORS.items():
            self.educational_embeddings[category] = self.model.encode(sentences, convert_to_numpy=True)

        # Precalcular anclas de contenido malicioso
        for category, sentences in MALICIOUS_ANCHORS.items():
            self.malicious_embeddings[category] = self.model.encode(sentences, convert_to_numpy=True)

        logger.info("✓ Embeddings de anclas precalculados correctamente.")

    def clean_html(self, html: str) -> str:
        """Limpia el código HTML, eliminando scripts, estilos y devolviendo texto plano limpio."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")

        # Eliminar elementos irrelevantes
        for element in soup(["script", "style", "noscript", "meta", "iframe", "header", "footer", "nav"]):
            element.decompose()

        text = soup.get_text(separator=" ")

        # Limpieza de espacios y líneas vacías
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _cosine_similarity_matrix(self, embedding_a, embeddings_b):
        """Calcula la similitud de coseno entre un embedding A y una matriz de embeddings B."""
        # Asegurar vectores normalizados
        a_norm = embedding_a / np.linalg.norm(embedding_a)
        b_norms = embeddings_b / np.linalg.norm(embeddings_b, axis=1, keepdims=True)
        return np.dot(b_norms, a_norm)

    def _has_contextual_error_code(self, text: str) -> bool:
        """
        Detecta códigos 4xx/5xx cuando aparecen con contexto semántico de fallo.
        Evita falsos positivos cuando el número forma parte de contenido legítimo.
        """
        lowered_text = text.lower()
        for match in re.finditer(r"\b(4\d{2}|5\d{2})\b", lowered_text):
            start = max(0, match.start() - 90)
            end = min(len(lowered_text), match.end() + 90)
            context_window = lowered_text[start:end]
            if any(term in context_window for term in ERROR_CONTEXT_TERMS):
                return True
        return False

    def _looks_like_educational_content(self, text: str, url: str) -> bool:
        """
        Detecta si el contenido parece explicativo/documental sobre códigos HTTP.
        Se usa para evitar falsos positivos al analizar artículos técnicos.
        """
        lowered_text = text.lower()
        educational_hits = sum(1 for term in EDUCATIONAL_CONTEXT_TERMS if term in lowered_text)
        explanatory_hits = sum(1 for cue in EXPLANATORY_CUES if cue in lowered_text)

        # Dominios conocidos de documentación/educación
        educational_domains = ("wikipedia.org", "rfc-editor.org", "w3.org", "developer.mozilla.org", "mdn.io")
        url_is_educational = any(domain in url.lower() for domain in educational_domains)

        # Señales adicionales típicas de artículos/documentación.
        has_many_words = len(lowered_text.split()) >= 180

        # Contenido educativo si: muchas palabras + términos educativos,
        # o si hay suficientes señales explicativas + contexto educativo,
        # o si la URL es de un dominio educativo conocido + al menos 1 término educativo.
        return bool(
            (educational_hits >= 2 and has_many_words)
            or (educational_hits >= 2 and explanatory_hits >= 1)
            or (url_is_educational and educational_hits >= 1)
        )

    def _layout_evidence(self, html: str, cleaned_text: str) -> tuple[float, float]:
        """Calcula evidencia estructural de plantilla de error vs artículo/documentación."""
        soup = BeautifulSoup(html or "", "html.parser")
        title = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
        h1_text = " ".join(h.get_text(" ", strip=True).lower() for h in soup.find_all("h1"))
        h2_text = " ".join(h.get_text(" ", strip=True).lower() for h in soup.find_all("h2"))
        link_text = " ".join(a.get_text(" ", strip=True).lower() for a in soup.find_all("a"))
        lower = (cleaned_text or "").lower()
        words = lower.split()

        error_layout_hits = 0
        if len(words) < 220:
            error_layout_hits += 1
        if re.search(r"\b(4\d{2}|5\d{2})\b", f"{title} {h1_text} {h2_text}"):
            error_layout_hits += 1
        if any(cue in link_text for cue in ("reload", "back", "home page", "try again")):
            error_layout_hits += 1
        if any(cue in lower for cue in ("temporarily unavailable", "unable to service your request", "server error")):
            error_layout_hits += 1

        educational_layout_hits = 0
        if len(words) >= 300:
            educational_layout_hits += 1
        if len(soup.find_all(["h2", "h3"])) >= 3:
            educational_layout_hits += 1
        if any(cue in lower for cue in ("references", "referencias", "table of contents", "specification", "rfc")):
            educational_layout_hits += 1
        if any(cue in lower for cue in ("is a status code", "es un código de estado", "indicates that", "indica que")):
            educational_layout_hits += 1

        return self._normalize_hits(error_layout_hits, 4), self._normalize_hits(educational_layout_hits, 4)

    def _resolve_ambiguity_with_strong_model(self, text: str) -> tuple[bool | None, float]:
        """
        Segunda opinión con modelo zero-shot:
        - True: más probable que sea página de error/inoperativa
        - False: más probable que sea contenido informativo/operativo
        - None: sin decisión utilizable
        """
        if not self.enable_strong_fallback:
            return None, 0.0
        try:
            self._load_strong_fallback_model()
            if self.zero_shot_classifier is None:
                return None, 0.0

            labels = [
                "error page or maintenance outage",
                "informational or educational content",
            ]
            result = self.zero_shot_classifier(
                text[:2400],
                candidate_labels=labels,
                hypothesis_template="This webpage is {}.",
                multi_label=False,
            )
            top_label = result["labels"][0]
            top_score = float(result["scores"][0])
            if top_label == labels[0]:
                return True, top_score
            return False, top_score
        except Exception as exc:
            logger.warning("Fallback fuerte no disponible: %s", exc)
            return None, 0.0

    def _has_strong_error_signature(self, text: str, html: str = "") -> bool:
        """
        Detecta plantillas explícitas de error del servidor.
        Estas señales tienen prioridad y no deben suprimirse por filtros educativos,
        salvo cuando el contexto es claramente explicativo/documental.
        """
        lowered_text = text.lower()
        lowered_html = (html or "").lower()

        # Si el texto tiene señales explicativas fuertes, no es un error en tiempo de ejecución.
        explanatory_hits = sum(1 for cue in EXPLANATORY_CUES if cue in lowered_text)
        educational_hits = sum(1 for term in EDUCATIONAL_CONTEXT_TERMS if term in lowered_text)
        if explanatory_hits >= 2 and educational_hits >= 1:
            return False

        # 1) Frases inequívocas de error en el contenido visible o en el markup.
        if any(signature in lowered_text or signature in lowered_html for signature in STRONG_ERROR_SIGNATURES):
            return True

        # 2) Códigos HTTP de error junto a palabras de fallo en la página.
        #    Cubre 4xx, 5xx y errores de CDN frecuentes (520-527).
        if re.search(r"\b(4\d{2}|5\d{2})\b", lowered_text):
            if any(term in lowered_text for term in ERROR_CONTEXT_TERMS):
                return True

        return False

    @staticmethod
    def _normalize_hits(hits: int, max_hits: int) -> float:
        if max_hits <= 0:
            return 0.0
        return min(1.0, hits / max_hits)

    def analyze(self, html: str, url: str, status_code: int, metadata: dict | None = None) -> dict:
        """
        Ejecuta el análisis semántico del contenido de una página.
        """
        # Asegurar que el modelo esté cargado (lazy loading)
        self._load_model()

        cleaned_text = self.clean_html(html)

        # Valores por defecto para páginas vacías
        if not cleaned_text:
            return {
                "is_inoperative": True,
                "inoperative_reason": "Página vacía (sin contenido de texto legible)",
                "confidence": 1.0,
                "has_spam": False,
                "has_malicious_content": False,
                "has_incoherent_content": True,
                "detected_language": "unknown",
                "quality_score": 5,
                "issues": ["La página no contiene texto analizable."],
                "warnings": ["Página vacía."],
            }

        # Limitar longitud para evitar uso excesivo de recursos
        # El modelo paraphrase-multilingual MiniLM trunca a ~128/256 tokens de todos modos.
        words = cleaned_text.split()
        limited_text = " ".join(words[:400])  # Primeras 400 palabras

        # Generar embedding del texto del sitio
        text_embedding = self.model.encode(limited_text, convert_to_numpy=True)

        # 1. DETECCIÓN DE PÁGINA INOPERATIVA (ERROR DISFRAZADO)
        is_inoperative = False
        inoperative_reason = None
        max_error_sim = 0.0
        matched_error_category = None

        # Primero, comprobar el código HTTP de la respuesta
        if status_code and status_code >= 400:
            is_inoperative = True
            inoperative_reason = f"Código de estado HTTP de error: {status_code}"
            max_error_sim = 1.0
        else:
            looks_educational = self._looks_like_educational_content(limited_text, url)
            has_strong_error_signature = self._has_strong_error_signature(cleaned_text, html)
            error_layout_score, educational_layout_score = self._layout_evidence(html, cleaned_text)

            # Similitud semántica con contenido educativo para desambiguar
            max_educational_sim = 0.0
            for _, embeddings in self.educational_embeddings.items():
                edu_sim = float(np.max(self._cosine_similarity_matrix(text_embedding, embeddings)))
                if edu_sim > max_educational_sim:
                    max_educational_sim = edu_sim

            # Evaluar similitud con anclas de error
            # Umbral de similitud semántica para error: 0.52
            ERROR_THRESHOLD = 0.52

            for category, embeddings in self.error_embeddings.items():
                similarities = self._cosine_similarity_matrix(text_embedding, embeddings)
                max_sim = float(np.max(similarities))
                if max_sim > max_error_sim:
                    max_error_sim = max_sim
                    matched_error_category = category

            contextual_error = self._has_contextual_error_code(limited_text)
            lower_cleaned = cleaned_text.lower()
            runtime_hits = sum(1 for cue in RUNTIME_ERROR_CUES if cue in lower_cleaned)
            explanatory_hits = sum(1 for cue in EXPLANATORY_CUES if cue in lower_cleaned)
            educational_hits = sum(1 for cue in EDUCATIONAL_CONTEXT_TERMS if cue in lower_cleaned)

            error_evidence = (
                max_error_sim
                + (0.18 if contextual_error else 0.0)
                + (0.22 if has_strong_error_signature else 0.0)
                + 0.12 * self._normalize_hits(runtime_hits, 4)
                + 0.15 * error_layout_score
            )
            educational_evidence = (
                max_educational_sim
                + (0.14 if looks_educational else 0.0)
                + 0.12 * self._normalize_hits(educational_hits, 5)
                + 0.12 * self._normalize_hits(explanatory_hits, 4)
                + 0.15 * educational_layout_score
            )

            ERROR_MARGIN = 0.10
            AMBIGUITY_BAND = 0.10
            evidence_delta = error_evidence - educational_evidence

            # Resolver casos ambiguos con un modelo más potente (segunda etapa).
            if abs(evidence_delta) <= AMBIGUITY_BAND:
                fallback_decision, fallback_confidence = self._resolve_ambiguity_with_strong_model(cleaned_text)
                if fallback_decision is True and fallback_confidence >= 0.62:
                    is_inoperative = True
                    inoperative_reason = (
                        f"Detectado por fallback fuerte como página de error (confianza={fallback_confidence:.2f})"
                    )
                    max_error_sim = max(max_error_sim, fallback_confidence)
                elif fallback_decision is False and fallback_confidence >= 0.62:
                    is_inoperative = False
                    inoperative_reason = None

            if (
                max_error_sim > ERROR_THRESHOLD
                and evidence_delta > ERROR_MARGIN
                and not (
                    is_inoperative is False and inoperative_reason is None and abs(evidence_delta) <= AMBIGUITY_BAND
                )
            ):
                is_inoperative = True
                inoperative_reason = (
                    f"Detectado semánticamente como '{matched_error_category}' "
                    f"(error={error_evidence:.2f}, educativo={educational_evidence:.2f})"
                )

        # 2. DETECCIÓN DE CONTENIDO MALICIOSO O NO APTO
        has_malicious_content = False
        has_spam = False
        malicious_reasons = []
        max_malicious_sim = 0.0

        # Umbral de similitud semántica para contenido malicioso: 0.53
        MALICIOUS_THRESHOLD = 0.53

        for category, embeddings in self.malicious_embeddings.items():
            similarities = self._cosine_similarity_matrix(text_embedding, embeddings)
            max_sim = float(np.max(similarities))
            if max_sim > MALICIOUS_THRESHOLD:
                if max_sim > max_malicious_sim:
                    max_malicious_sim = max_sim
                if category == "seo_spam":
                    has_spam = True
                    malicious_reasons.append(f"Spam SEO detectado ({category}, Similitud: {max_sim:.2f})")
                else:
                    has_malicious_content = True
                    malicious_reasons.append(
                        f"Contenido no apto o malicioso detectado ({category}, Similitud: {max_sim:.2f})"
                    )

        # 3. DETECCIÓN DE INCOHERENCIA
        has_incoherent_content = False
        coherence_score = 1.0

        # Dividir en oraciones (por punto) para medir la coherencia semántica
        sentences = [s.strip() for s in re.split(r"[.!?]+", cleaned_text) if len(s.strip()) > 15]

        # Analizar hasta las primeras 8 oraciones significativas
        sentences = sentences[:8]
        if len(sentences) >= 3:
            sentence_embeddings = self.model.encode(sentences, convert_to_numpy=True)
            similarities = []
            for i in range(len(sentence_embeddings) - 1):
                sim = float(self._cosine_similarity_matrix(sentence_embeddings[i], sentence_embeddings[i + 1 : i + 2])[0])
                similarities.append(sim)
            coherence_score = float(np.mean(similarities))

            # Si la coherencia semántica media entre oraciones es extremadamente baja, hay incoherencia
            if coherence_score < 0.12:
                has_incoherent_content = True

        # 4. DETECCIÓN DE IDIOMA
        try:
            detected_language = detect(limited_text)
        except Exception as e:
            logger.warning("Error al detectar idioma con langdetect: %s", e)
            detected_language = "unknown"

        # 5. CÁLCULO DE SCORE GENERAL DE CALIDAD
        quality_score = 100.0
        issues = []
        warnings = []

        if is_inoperative:
            quality_score -= 95.0
            issues.append(f"Página no operativa: {inoperative_reason}")
        if has_malicious_content:
            quality_score -= 80.0
            issues.append("Contenido potencialmente no apto o malicioso detectado semánticamente.")
        if has_spam:
            quality_score -= 50.0
            issues.append("Contenido identificado como Spam / SEO keyword stuffing.")
        if has_incoherent_content:
            quality_score -= 40.0
            issues.append(f"Incoherencia semántica alta detectada en los textos (Coherencia: {coherence_score:.2f}).")

        # Penalizaciones menores
        if len(words) < 50:
            quality_score -= 15.0
            warnings.append(f"Contenido extremadamente delgado ({len(words)} palabras).")
        elif len(words) < 150:
            quality_score -= 5.0
            warnings.append(f"Contenido bajo en texto plano ({len(words)} palabras).")

        if detected_language == "unknown":
            quality_score -= 5.0
            warnings.append("No se pudo identificar con precisión el idioma del contenido.")

        # Garantizar límites
        quality_score = max(5, min(100, int(quality_score)))

        # Construir listas de issues y warnings detallados
        for reason in malicious_reasons:
            if "Spam" in reason:
                warnings.append(reason)
            else:
                issues.append(reason)

        confidence = 1.0
        if not is_inoperative and not has_malicious_content:
            confidence = float(1.0 - max(max_error_sim, max_malicious_sim) * 0.2)
        else:
            confidence = float(max(max_error_sim, max_malicious_sim))

        confidence = max(0.5, min(1.0, confidence))

        return {
            "is_inoperative": is_inoperative,
            "inoperative_reason": inoperative_reason,
            "confidence": round(confidence, 2),
            "has_spam": has_spam,
            "has_malicious_content": has_malicious_content,
            "has_incoherent_content": has_incoherent_content,
            "detected_language": detected_language,
            "quality_score": quality_score,
            "issues": issues,
            "warnings": warnings,
        }
