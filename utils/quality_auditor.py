import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from config.logging_config import setup_logger
from utils.audit_dictionaries import build_audit_dictionaries
from utils.audit_regex import AuditRegexSet, build_audit_regex_set

logger = setup_logger(__name__)


@dataclass
class QualityAuditReport:
    status: str
    score: int
    seo_issues: list[str] = field(default_factory=list)
    content_issues: list[str] = field(default_factory=list)
    image_issues: list[str] = field(default_factory=list)
    structure_issues: list[str] = field(default_factory=list)
    link_issues: list[str] = field(default_factory=list)
    button_issues: list[str] = field(default_factory=list)
    technical_issues: list[str] = field(default_factory=list)
    release_blocked: bool = False
    release_blockers: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "score": self.score,
            "seo_issues": self.seo_issues,
            "content_issues": self.content_issues,
            "image_issues": self.image_issues,
            "structure_issues": self.structure_issues,
            "link_issues": self.link_issues,
            "button_issues": self.button_issues,
            "technical_issues": self.technical_issues,
            "release_blocked": self.release_blocked,
            "release_blockers": self.release_blockers,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
        }


class QualityAuditor:
    def __init__(self, timeout: int = settings.REQUEST_TIMEOUT):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(settings.DEFAULT_HEADERS)
        self._dicts = build_audit_dictionaries()
        self._regex = build_audit_regex_set()
        self._driver: webdriver.Chrome | None = None
        self._browser_confirms = 0
        self._max_browser_confirms = 15

    def build_report(self, html: str, base_url: str, metadata: dict | None = None) -> QualityAuditReport:
        metadata = metadata or {}
        self._browser_confirms = 0
        html_lines = html.splitlines()
        soup = BeautifulSoup(html, settings.BS4_PARSER)
        crawl_stats = {"tested": 0, "broken": 0, "skipped": 0}

        seo_issues: list[str] = []
        content_issues: list[str] = []
        image_issues: list[str] = []
        structure_issues: list[str] = []
        link_issues: list[str] = []
        button_issues: list[str] = []
        technical_issues: list[str] = []
        recommendations: list[str] = []
        asset_stats = {"checked": 0, "broken": 0, "mixed_content": 0}

        try:
            if self._is_banned_url(base_url):
                warning = f"URL prohibida para pruebas de red por politica: {base_url}"
                link_issues.append(warning)
                recommendations.append("Cambiar URL objetivo por un dominio permitido para validar enlaces e imagenes.")
            else:
                self._warm_up_cookies(base_url)

            self._check_structure(soup, structure_issues)
            self._check_seo(soup, seo_issues)
            self._check_content(soup, content_issues, html_lines)
            self._check_images(soup, base_url, html_lines, image_issues)
            self._check_links_recursive(soup, base_url, html_lines, link_issues, crawl_stats)
            self._check_buttons(soup, base_url, html_lines, button_issues)
            self._check_technical(html, soup, base_url, html_lines, technical_issues, asset_stats)
        finally:
            self._close_driver()

        self._ensure_non_empty("seo_issues", seo_issues)
        self._ensure_non_empty("content_issues", content_issues)
        self._ensure_non_empty("image_issues", image_issues)
        self._ensure_non_empty("structure_issues", structure_issues)
        self._ensure_non_empty("link_issues", link_issues)
        self._ensure_non_empty("button_issues", button_issues)
        self._ensure_non_empty("technical_issues", technical_issues)

        metrics = self._collect_metrics(
            soup,
            metadata,
            image_issues,
            link_issues,
            button_issues,
            technical_issues,
            crawl_stats,
            asset_stats,
        )
        score = self._calculate_score(
            seo_issues,
            content_issues,
            image_issues,
            structure_issues,
            link_issues,
            button_issues,
            technical_issues,
        )
        status = self._status_from_score(score)
        release_blocked, release_blockers = self._evaluate_release_gate(
            score=score,
            content_issues=content_issues,
            link_issues=link_issues,
            technical_issues=technical_issues,
            image_issues=image_issues,
            button_issues=button_issues,
        )
        metrics["release_gate_blocked"] = release_blocked
        metrics["release_blockers_count"] = len(release_blockers)

        recommendations.extend(
            self._build_recommendations(
                seo_issues,
                content_issues,
                image_issues,
                structure_issues,
                link_issues,
                button_issues,
                technical_issues,
            )
        )
        if not recommendations:
            recommendations.append("No se detectan mejoras criticas. Mantener monitorizacion periodica.")
        if release_blocked:
            recommendations.insert(0, "BLOQUEAR despliegue a produccion hasta resolver blockers del gate.")

        return QualityAuditReport(
            status=status,
            score=score,
            seo_issues=seo_issues,
            content_issues=content_issues,
            image_issues=image_issues,
            structure_issues=structure_issues,
            link_issues=link_issues,
            button_issues=button_issues,
            technical_issues=technical_issues,
            release_blocked=release_blocked,
            release_blockers=release_blockers,
            recommendations=recommendations,
            metrics=metrics,
        )

    @staticmethod
    def report_to_text(report: QualityAuditReport) -> str:
        lines = [
            "INFORME DE CALIDAD WEB",
            "======================",
            f"Estado: {report.status}",
            f"Puntuacion: {report.score}/100",
            f"Gate de produccion: {'BLOQUEADO' if report.release_blocked else 'APTO'}",
            "",
            "Bloqueadores de release:",
            *([f"- {item}" for item in report.release_blockers] or ["- Sin bloqueadores criticos."]),
            "",
            "Metricas:",
            *[f"- {k}: {v}" for k, v in report.metrics.items()],
            "",
            "SEO:",
            *[f"- {item}" for item in report.seo_issues],
            "",
            "Estructura HTML:",
            *[f"- {item}" for item in report.structure_issues],
            "",
            "Contenido:",
            *[f"- {item}" for item in report.content_issues],
            "",
            "Imagenes:",
            *[f"- {item}" for item in report.image_issues],
            "",
            "Enlaces:",
            *[f"- {item}" for item in report.link_issues],
            "",
            "Botones y formularios:",
            *[f"- {item}" for item in report.button_issues],
            "",
            "Tecnico / DevOps:",
            *[f"- {item}" for item in report.technical_issues],
            "",
            "Mejoras recomendadas:",
            *[f"- {item}" for item in report.recommendations],
        ]
        return "\n".join(lines)

    def _check_technical(
        self,
        html: str,
        soup: BeautifulSoup,
        base_url: str,
        html_lines: list[str],
        issues: list[str],
        asset_stats: dict,
    ) -> None:
        html_lower = html.lower()
        if "<!doctype html>" not in html_lower[:300]:
            issues.append("Falta <!DOCTYPE html> al inicio del documento (modo estandares).")

        charset_meta = soup.find("meta", attrs={"charset": True})
        if not charset_meta:
            issues.append("Falta <meta charset='utf-8'> para codificacion consistente.")

        if not soup.find("meta", attrs={"name": "robots"}):
            issues.append("Falta meta robots (definir index/follow segun entorno).")

        iframes = soup.find_all("iframe")
        for iframe in iframes:
            if not (iframe.get("title") or "").strip():
                ln, line = self._find_line_for_tag(html_lines, iframe)
                issues.append(f"Iframe sin atributo title en linea aproximada {ln}: {line}")

        id_count: dict[str, int] = {}
        for tag in soup.find_all(attrs={"id": True}):
            tid = (tag.get("id") or "").strip()
            if not tid:
                continue
            id_count[tid] = id_count.get(tid, 0) + 1
        duplicates = [item for item, count in id_count.items() if count > 1]
        for dup in duplicates[:20]:
            issues.append(f"ID duplicado detectado: #{dup} (rompe selectores y accesibilidad).")

        headings = [int(h.name[1]) for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])]
        for idx in range(1, len(headings)):
            if headings[idx] - headings[idx - 1] > 1:
                issues.append(
                    f"Salto brusco de jerarquia de headings: h{headings[idx - 1]} -> h{headings[idx]}."
                )
                break

        self._check_assets(soup, base_url, html_lines, issues, asset_stats)
        self._check_forms_accessibility(soup, html_lines, issues)

        inline_script_chars = sum(len(script.get_text(strip=True)) for script in soup.find_all("script") if not script.get("src"))
        if inline_script_chars > 4000:
            issues.append(
                f"JavaScript inline excesivo ({inline_script_chars} chars). Considerar mover a archivo versionado."
            )
        inline_style_chars = sum(len(style.get_text(strip=True)) for style in soup.find_all("style"))
        if inline_style_chars > 2500:
            issues.append(
                f"CSS inline excesivo ({inline_style_chars} chars). Considerar extraer a stylesheet cacheable."
            )

    def _check_assets(
        self,
        soup: BeautifulSoup,
        base_url: str,
        html_lines: list[str],
        issues: list[str],
        asset_stats: dict,
    ) -> None:
        base_is_https = base_url.lower().startswith("https://")

        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel", [])).lower()
            href = (link.get("href") or "").strip()
            if "stylesheet" not in rel:
                continue
            ln, line = self._find_line_for_tag(html_lines, link)
            if not href:
                issues.append(f"Stylesheet <link> sin href en linea aproximada {ln}: {line}")
                continue
            full = urljoin(base_url, href)
            if base_is_https and full.lower().startswith("http://"):
                asset_stats["mixed_content"] += 1
                issues.append(f"Mixed content CSS: {full} (linea aproximada {ln})")
            ok, elapsed_ms, status_code = self._check_url_with_strategies(full)
            asset_stats["checked"] += 1
            if not ok:
                asset_stats["broken"] += 1
                issues.append(f"CSS no accesible {full} status={status_code} tiempo={elapsed_ms}ms")

        for script in soup.find_all("script"):
            src = (script.get("src") or "").strip()
            if not src:
                continue
            ln, line = self._find_line_for_tag(html_lines, script)
            full = urljoin(base_url, src)
            if base_is_https and full.lower().startswith("http://"):
                asset_stats["mixed_content"] += 1
                issues.append(f"Mixed content JS: {full} (linea aproximada {ln})")
            ok, elapsed_ms, status_code = self._check_url_with_strategies(full)
            asset_stats["checked"] += 1
            if not ok:
                asset_stats["broken"] += 1
                issues.append(f"JS no accesible {full} status={status_code} tiempo={elapsed_ms}ms")
            if soup.head and script in soup.head.contents and not script.get("defer") and not script.get("async"):
                issues.append(
                    f"Script bloqueante en <head> sin defer/async: {full} (linea aproximada {ln}: {line[:120]})"
                )

    def _check_forms_accessibility(self, soup: BeautifulSoup, html_lines: list[str], issues: list[str]) -> None:
        for field in soup.find_all(["input", "select", "textarea"]):
            if field.name == "input" and (field.get("type") or "").lower() in {"hidden", "submit", "button"}:
                continue
            has_aria = bool((field.get("aria-label") or "").strip())
            fid = (field.get("id") or "").strip()
            has_label = bool(fid and soup.find("label", attrs={"for": fid}))
            if not has_aria and not has_label:
                ln, line = self._find_line_for_tag(html_lines, field)
                issues.append(
                    f"Campo de formulario sin label/aria-label en linea aproximada {ln}: {line}"
                )

    def _check_structure(self, soup: BeautifulSoup, issues: list[str]) -> None:
        if soup.html is None:
            issues.append("Falta etiqueta <html>. Revisar plantilla base.")
            return
        if soup.head is None:
            issues.append("Falta <head>. Algunos metadatos SEO no pueden aplicarse.")
        if soup.body is None:
            issues.append("Falta <body>. HTML incompleto.")
        if not soup.find("h1"):
            issues.append("No existe ningun <h1>; dificulta estructura semantica.")
        if not soup.find_all(["h2", "h3"]):
            issues.append("No hay jerarquia de subtitulos <h2>/<h3>.")

    def _check_seo(self, soup: BeautifulSoup, issues: list[str]) -> None:
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        if not title:
            issues.append("Falta <title>.")
        elif len(title) < 20 or len(title) > 65:
            issues.append(f"Longitud no optima de <title> ({len(title)} chars).")

        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_text = (meta_desc.get("content") or "").strip() if meta_desc else ""
        if not desc_text:
            issues.append("Falta meta description.")
        elif len(desc_text) < 70 or len(desc_text) > 160:
            issues.append(f"Longitud no optima de meta description ({len(desc_text)} chars).")

        html_tag = soup.find("html")
        if html_tag and not html_tag.get("lang"):
            issues.append("La etiqueta <html> no define lang.")
        if not soup.find("link", attrs={"rel": "canonical"}):
            issues.append("Falta canonical (<link rel='canonical'>).")
        if not soup.find("meta", attrs={"name": "viewport"}):
            issues.append("Falta meta viewport para responsive.")

    def _check_content(self, soup: BeautifulSoup, issues: list[str], html_lines: list[str]) -> None:
        text = soup.get_text(" ", strip=True)
        text_l = text.lower()
        if not text_l:
            issues.append("No se encontro texto visible en el body.")
            return

        for pattern in (
            *self._dicts.lorem_patterns,
            *self._dicts.incoherent_patterns,
            *self._dicts.explicit_patterns,
            *self._dicts.profanity_patterns,
        ):
            if pattern in text_l:
                line_no, line = self._find_line_for_text(html_lines, pattern)
                issues.append(
                    f"Texto problematico '{pattern}' detectado en linea aproximada {line_no}: {line}"
                )

        if self._regex.gibberish_regex.search(text_l):
            issues.append("Detectadas secuencias repetitivas anormales (posible contenido incoherente).")
        if self._regex.multi_symbol_regex.search(text_l):
            issues.append("Detectados bloques de simbolos excesivos (posible ruido).")
        if self._regex.character_noise_regex.search(text_l):
            issues.append("Detectados caracteres repetitivos no lingüisticos (ruido de contenido).")
        if len(self._regex.typo_regex.findall(text_l)) >= 5:
            issues.append("Exceso de tokens posiblemente mal tipados.")
        if len(self._regex.long_token_regex.findall(text_l)) >= 2:
            issues.append("Detectados tokens extremadamente largos (posible texto sin sentido o hash pegado).")
        incoherent_samples = self._detect_incoherent_segments(text_l, self._regex)
        if incoherent_samples:
            for reason, token in incoherent_samples[:8]:
                line_no, line = self._find_line_for_text(html_lines, token)
                issues.append(
                    f"Incoherencia heuristica ({reason}) en linea aproximada {line_no}: {line}"
                )

        for segment in self._dicts.blocked_admin_segments:
            if segment in text_l:
                line_no, line = self._find_line_for_text(html_lines, segment)
                issues.append(
                    f"Texto prohibido '{segment}' encontrado en linea aproximada {line_no}: {line}"
                )

    @staticmethod
    def _detect_incoherent_segments(text_l: str, regex_set: AuditRegexSet) -> list[tuple[str, str]]:
        """
        Detecta incoherencias sin depender de un diccionario fijo.
        Señales:
        - bloques repetidos (ej: 'abcabcabc')
        - clusters largos de consonantes (ej: 'xtrplmn')
        - baja proporcion de vocales en palabras largas
        - mezcla anomala de letras+numeros en muchas palabras
        """
        words = regex_set.word_regex.findall(text_l)
        if not words:
            return []

        suspicious: list[tuple[str, str]] = []
        alnum_noise_count = 0

        for w in words:
            if len(w) >= 7:
                vowel_count = sum(1 for c in w if c in "aeiouáéíóúü")
                vowel_ratio = vowel_count / max(1, len(w))
                if vowel_ratio < 0.22:
                    suspicious.append(("baja_ratio_vocales", w[:30]))
                    continue

            if regex_set.repeated_chunk_regex.search(w):
                suspicious.append(("bloque_repetido", w[:30]))
                continue

            if regex_set.consonant_cluster_regex.search(w):
                suspicious.append(("cluster_consonantes", w[:30]))
                continue

            has_letters = any(ch.isalpha() for ch in w)
            has_digits = any(ch.isdigit() for ch in w)
            if has_letters and has_digits and len(w) >= 8:
                alnum_noise_count += 1

        if alnum_noise_count >= 4:
            suspicious.append(("muchos_tokens_alnum_raros", str(alnum_noise_count)))

        # Umbral para no marcar textos legitimos por falsos positivos aislados.
        min_hits = max(2, int(len(words) * 0.08))
        if len(suspicious) < min_hits:
            return []
        return suspicious

    def _check_images(self, soup: BeautifulSoup, base_url: str, html_lines: list[str], issues: list[str]) -> None:
        images = soup.find_all("img")
        if not images:
            issues.append("No hay imagenes en la pagina; comprobar si es esperado.")
            return

        for img in images:
            src = (img.get("src") or "").strip()
            alt = (img.get("alt") or "").strip()
            line_no, line = self._find_line_for_tag(html_lines, img)
            location = f"linea aproximada {line_no}: {line}"

            if not src:
                issues.append(f"Imagen sin src en {location}")
                continue
            if not alt:
                issues.append(f"Imagen sin alt (src={src}) en {location}")

            absolute_url = urljoin(base_url, src)
            if self._is_banned_url(absolute_url):
                issues.append(f"Imagen no verificada por URL prohibida: {absolute_url} ({location})")
                continue
            if src.startswith("data:"):
                continue

            ok, elapsed_ms, status_code = self._check_url_with_strategies(absolute_url)
            speed = self._classify_speed(elapsed_ms)
            if not ok:
                issues.append(
                    f"Imagen rota src={absolute_url} status={status_code} tiempo={elapsed_ms}ms ({speed}) en {location}"
                )

    def _check_links_recursive(
        self,
        soup: BeautifulSoup,
        base_url: str,
        html_lines: list[str],
        issues: list[str],
        crawl_stats: dict,
    ) -> None:
        if self._is_banned_url(base_url):
            issues.append("Crawl recursivo omitido por URL prohibida.")
            return

        base_host = self._normalize_host(urlparse(base_url).netloc)
        queue: list[tuple[str, int]] = []
        visited: set[str] = set()

        for anchor in soup.find_all("a"):
            href = (anchor.get("href") or "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            full = urljoin(base_url, href)
            queue.append((full, 0))
            if any(seg in full.lower() for seg in self._dicts.blocked_admin_segments):
                ln, line = self._find_line_for_tag(html_lines, anchor)
                issues.append(f"Enlace prohibido detectado {full} en linea aproximada {ln}: {line}")

        while queue and crawl_stats["tested"] < settings.AUDIT_MAX_RECURSIVE_LINKS:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            if self._is_banned_url(url):
                crawl_stats["skipped"] += 1
                issues.append(f"Enlace omitido por politica de bloqueo: {url}")
                continue

            ok, elapsed_ms, status_code, content = self._check_url_with_strategies(
                url,
                include_content=(depth < settings.AUDIT_MAX_CRAWL_DEPTH),
            )
            crawl_stats["tested"] += 1
            speed = self._classify_speed(elapsed_ms)
            if not ok:
                crawl_stats["broken"] += 1
                issues.append(
                    f"Enlace roto confirmado (HTTP+navegador) {url} status={status_code} tiempo={elapsed_ms}ms ({speed})"
                )

            if content and depth < settings.AUDIT_MAX_CRAWL_DEPTH:
                page_soup = BeautifulSoup(content, settings.BS4_PARSER)
                for inner_anchor in page_soup.find_all("a"):
                    href = (inner_anchor.get("href") or "").strip()
                    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                        continue
                    full_inner = urljoin(url, href)
                    inner_host = self._normalize_host(urlparse(full_inner).netloc)
                    if inner_host != base_host:
                        continue
                    queue.append((full_inner, depth + 1))

    def _check_buttons(self, soup: BeautifulSoup, base_url: str, html_lines: list[str], issues: list[str]) -> None:
        buttons = soup.find_all(["button", "input"])
        forms = soup.find_all("form")

        if not buttons:
            issues.append("No hay botones detectables en HTML estatico.")

        for btn in buttons:
            if btn.name == "input" and (btn.get("type") or "").lower() not in {"submit", "button"}:
                continue
            ln, line = self._find_line_for_tag(html_lines, btn)
            text = btn.get_text(" ", strip=True) if isinstance(btn, Tag) else ""
            if not text:
                text = btn.get("value", "(sin texto)")
            if not text or text == "(sin texto)":
                issues.append(f"Boton sin texto visible en linea aproximada {ln}: {line}")

        for form in forms:
            action = (form.get("action") or "").strip()
            method = (form.get("method") or "get").lower()
            ln, line = self._find_line_for_tag(html_lines, form)
            if not action:
                issues.append(f"Formulario sin action en linea aproximada {ln}: {line}")
                continue

            target = urljoin(base_url, action)
            if self._is_banned_url(target):
                issues.append(f"Formulario no probado por URL prohibida: {target}")
                continue
            if any(seg in target.lower() for seg in self._dicts.blocked_admin_segments):
                issues.append(f"Formulario apunta a ruta prohibida ({target}) en linea aproximada {ln}: {line}")
                continue

            ok, elapsed_ms, status_code = self._check_url_with_strategies(target, method=method)
            speed = self._classify_speed(elapsed_ms)
            if not ok:
                issues.append(
                    f"Fallo al probar action de formulario {target} metodo={method.upper()} status={status_code} tiempo={elapsed_ms}ms ({speed})"
                )

    def _check_url(
        self,
        url: str,
        method: str = "head",
        include_content: bool = False,
    ) -> tuple:
        if self._is_banned_url(url):
            return (False, 0, "blocked", "") if include_content else (False, 0, "blocked")
        time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)

        start = time.perf_counter()
        response = None
        try:
            method_l = method.lower()
            if method_l == "post":
                response = self._session.post(url, timeout=self._timeout, data={})
            elif method_l == "get":
                response = self._session.get(url, timeout=self._timeout)
            else:
                response = self._session.head(url, timeout=self._timeout, allow_redirects=True)
                if response.status_code == 405 or response.status_code >= 400:
                    response = self._session.get(url, timeout=self._timeout, allow_redirects=True)

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            ok = response.status_code < 400
            if include_content:
                content = response.text if "text/html" in response.headers.get("content-type", "").lower() else ""
                return ok, elapsed_ms, response.status_code, content
            return ok, elapsed_ms, response.status_code
        except requests.RequestException:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            if include_content:
                return False, elapsed_ms, "request_exception", ""
            return False, elapsed_ms, "request_exception"

    def _check_url_with_strategies(
        self,
        url: str,
        method: str = "head",
        include_content: bool = False,
    ) -> tuple:
        """
        Doble verificacion de enlaces/recursos:
        1) requests (HTTP)
        2) Selenium (navegador) solo cuando HTTP falla
        """
        primary = self._check_url(url, method=method, include_content=include_content)
        if include_content:
            ok, elapsed_ms, status_code, content = primary
        else:
            ok, elapsed_ms, status_code = primary
            content = ""

        if ok:
            return primary

        browser_ok, browser_ms = self._check_url_browser(url)
        if browser_ok:
            if include_content:
                return True, browser_ms, f"{status_code}->ok_browser", content
            return True, browser_ms, f"{status_code}->ok_browser"

        if include_content:
            return False, elapsed_ms, status_code, content
        return False, elapsed_ms, status_code

    def _check_url_browser(self, url: str) -> tuple[bool, int]:
        if self._is_banned_url(url):
            return False, 0
        if self._browser_confirms >= self._max_browser_confirms:
            return False, 0

        driver = self._get_driver()
        if driver is None:
            return False, 0

        start = time.perf_counter()
        try:
            self._browser_confirms += 1
            driver.get(url)
            WebDriverWait(driver, max(4, settings.SELENIUM_IMPLICIT_WAIT)).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return True, elapsed_ms
        except (TimeoutException, WebDriverException):
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return False, elapsed_ms

    def _warm_up_cookies(self, base_url: str) -> None:
        """
        Primer request para poblar cookies y reducir falsos positivos.
        """
        try:
            self._session.get(base_url, timeout=self._timeout, allow_redirects=True)
        except requests.RequestException:
            logger.debug("No se pudo hacer warm-up de cookies para %s", base_url)

    def _get_driver(self) -> webdriver.Chrome | None:
        if self._driver is not None:
            return self._driver
        try:
            opts = Options()
            if settings.SELENIUM_HEADLESS:
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1366,768")
            opts.add_argument(f"user-agent={settings.DEFAULT_HEADERS['User-Agent']}")
            service = Service(settings.SELENIUM_DRIVER_PATH) if settings.SELENIUM_DRIVER_PATH else Service()
            driver = webdriver.Chrome(service=service, options=opts)
            driver.set_page_load_timeout(settings.SELENIUM_PAGE_LOAD_TIMEOUT)
            self._driver = driver
            return self._driver
        except Exception as exc:
            logger.debug("Selenium no disponible para confirmaciones: %s", exc)
            self._driver = None
            return None

    def _close_driver(self) -> None:
        if self._driver is None:
            return
        try:
            self._driver.quit()
        except Exception:
            pass
        self._driver = None

    @staticmethod
    def _collect_metrics(
        soup: BeautifulSoup,
        metadata: dict,
        image_issues: list[str],
        link_issues: list[str],
        button_issues: list[str],
        technical_issues: list[str],
        crawl_stats: dict,
        asset_stats: dict,
    ) -> dict:
        source_response_ms = metadata.get("response_time_ms", -1)
        source_speed = QualityAuditor._classify_speed(source_response_ms) if source_response_ms >= 0 else "sin_dato"
        return {
            "status_code": metadata.get("status_code", "sin_dato"),
            "release_gate_blocked": False,  # se actualiza al construir el informe final
            "source_response_time_ms": source_response_ms,
            "source_response_speed": source_speed,
            "title_length": len(soup.title.string.strip()) if soup.title and soup.title.string else 0,
            "meta_description_present": bool(soup.find("meta", attrs={"name": "description"})),
            "h1_count": len(soup.find_all("h1")),
            "image_count": len(soup.find_all("img")),
            "links_count": len(soup.find_all("a")),
            "forms_count": len(soup.find_all("form")),
            "buttons_count": len(soup.find_all(["button", "input"])),
            "word_count": len(soup.get_text(" ", strip=True).split()),
            "image_issue_count": len([i for i in image_issues if "Sin incidencias" not in i]),
            "link_issue_count": len([i for i in link_issues if "Sin incidencias" not in i]),
            "button_issue_count": len([i for i in button_issues if "Sin incidencias" not in i]),
            "technical_issue_count": len([i for i in technical_issues if "Sin incidencias" not in i]),
            "recursive_links_tested": crawl_stats["tested"],
            "recursive_links_broken": crawl_stats["broken"],
            "recursive_links_skipped": crawl_stats["skipped"],
            "assets_checked": asset_stats["checked"],
            "assets_broken": asset_stats["broken"],
            "assets_mixed_content": asset_stats["mixed_content"],
        }

    @staticmethod
    def _calculate_score(
        seo_issues: list[str],
        content_issues: list[str],
        image_issues: list[str],
        structure_issues: list[str],
        link_issues: list[str],
        button_issues: list[str],
        technical_issues: list[str],
    ) -> int:
        score = 100
        score -= len([i for i in seo_issues if "Sin incidencias" not in i]) * 6
        score -= len([i for i in content_issues if "Sin incidencias" not in i]) * 7
        score -= len([i for i in image_issues if "Sin incidencias" not in i]) * 5
        score -= len([i for i in structure_issues if "Sin incidencias" not in i]) * 6
        score -= len([i for i in link_issues if "Sin incidencias" not in i]) * 8
        score -= len([i for i in button_issues if "Sin incidencias" not in i]) * 6
        score -= len([i for i in technical_issues if "Sin incidencias" not in i]) * 7
        return max(0, min(100, score))

    @staticmethod
    def _status_from_score(score: int) -> str:
        if score >= 85:
            return "excelente"
        if score >= 70:
            return "bueno"
        if score >= 50:
            return "mejorable"
        return "critico"

    @staticmethod
    def _build_recommendations(
        seo_issues: list[str],
        content_issues: list[str],
        image_issues: list[str],
        structure_issues: list[str],
        link_issues: list[str],
        button_issues: list[str],
        technical_issues: list[str],
    ) -> list[str]:
        recommendations: list[str] = []
        if any("Sin incidencias" not in i for i in seo_issues):
            recommendations.append("Corregir metadatos SEO: title, description, canonical, viewport y lang.")
        if any("Sin incidencias" not in i for i in structure_issues):
            recommendations.append("Reforzar estructura semantica: html/head/body y jerarquia de encabezados.")
        if any("Sin incidencias" not in i for i in image_issues):
            recommendations.append("Arreglar imagenes rotas y completar atributos alt con textos descriptivos.")
        if any("Sin incidencias" not in i for i in content_issues):
            recommendations.append("Eliminar contenido de relleno/incoherente o malsonante.")
        if any("Sin incidencias" not in i for i in link_issues):
            recommendations.append("Corregir enlaces rotos y eliminar rutas admin/wp-admin del sitio.")
        if any("Sin incidencias" not in i for i in button_issues):
            recommendations.append("Revisar botones y formularios (texto visible, action valida y respuesta).")
        if any("Sin incidencias" not in i for i in technical_issues):
            recommendations.append(
                "Aplicar hardening tecnico: doctype/charset, assets accesibles, sin mixed-content, labels y IDs unicos."
            )
        return recommendations

    @staticmethod
    def _evaluate_release_gate(
        score: int,
        content_issues: list[str],
        link_issues: list[str],
        technical_issues: list[str],
        image_issues: list[str],
        button_issues: list[str],
    ) -> tuple[bool, list[str]]:
        blockers: list[str] = []

        if score < 70:
            blockers.append(f"Score global insuficiente para produccion ({score}/100).")

        strong_content_flags = (
            "contenido explicito",
            "contenido sexual",
            "porno",
            "nsfw",
            "texto problematico",
            "incoherencia heuristica",
        )
        if any(any(flag in issue.lower() for flag in strong_content_flags) for issue in content_issues):
            blockers.append("Contenido sensible/incoherente detectado en texto visible.")

        broken_links = [i for i in link_issues if "enlace roto confirmado" in i.lower()]
        if broken_links:
            blockers.append(f"Enlaces rotos confirmados ({len(broken_links)}).")

        broken_images = [i for i in image_issues if "imagen rota" in i.lower()]
        if broken_images:
            blockers.append(f"Imagenes rotas detectadas ({len(broken_images)}).")

        critical_tech_flags = ("mixed content", "id duplicado", "doctype", "charset", "script bloqueante")
        if any(any(flag in issue.lower() for flag in critical_tech_flags) for issue in technical_issues):
            blockers.append("Incidencias tecnicas criticas para estabilidad/seguridad detectadas.")

        form_failures = [i for i in button_issues if "fallo al probar action de formulario" in i.lower()]
        if form_failures:
            blockers.append(f"Formularios con fallos de action detectados ({len(form_failures)}).")

        return (len(blockers) > 0), blockers

    @staticmethod
    def _classify_speed(response_time_ms: int) -> str:
        if response_time_ms < 0:
            return "sin_dato"
        if response_time_ms < 400:
            return "rapido"
        if response_time_ms < 1200:
            return "medio"
        return "lento"

    @staticmethod
    def _normalize_host(host: str) -> str:
        host = host.lower().strip()
        return host[4:] if host.startswith("www.") else host

    def _is_banned_url(self, url: str) -> bool:
        host = self._normalize_host(urlparse(url).netloc)
        return host in {self._normalize_host(x) for x in settings.AUDIT_BANNED_HOSTS}

    @staticmethod
    def _find_line_for_tag(html_lines: list[str], tag: Tag) -> tuple[int, str]:
        text = str(tag).strip().split("\n")[0][:300]
        return QualityAuditor._find_line_for_text(html_lines, text)

    @staticmethod
    def _find_line_for_text(html_lines: list[str], text: str) -> tuple[int, str]:
        token = text.strip().lower()
        if not token:
            return -1, "(linea no localizada)"
        token = token[:120]
        for idx, line in enumerate(html_lines, start=1):
            if token in line.lower():
                return idx, line.strip()[:350]
        return -1, f"(linea no localizada para '{token}')"

    @staticmethod
    def _ensure_non_empty(section_name: str, issues: list[str]) -> None:
        if not issues:
            issues.append(f"Sin incidencias detectadas en {section_name}.")
