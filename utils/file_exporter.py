import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Sequence

from scraper.models.scrape_result import ScrapeResult
from config import settings
from config.logging_config import setup_logger

logger = setup_logger(__name__)


class FileExporter:
    """
    Exporta una lista de ScrapeResult a disco.

    El JSON de resultados guarda solo metadata + ruta al HTML.
    El HTML prettificado se guarda por separado en data/raw/,
    lo que mantiene el JSON limpio y legible.

    Uso:
        exporter = FileExporter()
        path = exporter.export(results)
        path = exporter.export(results, fmt="csv")
    """

    def __init__(
        self,
        output_dir: Path = settings.OUTPUT_DIR,
        fmt: str = settings.OUTPUT_FORMAT,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fmt = fmt.lower()

    # ── API pública ───────────────────────────────────────────────────────────

    def export(
        self,
        results: Sequence[ScrapeResult],
        fmt: str | None = None,
    ) -> Path:
        fmt  = (fmt or self.fmt).lower()
        path = self._build_path(fmt)

        if fmt == "json":
            self._to_json(results, path)
        elif fmt == "csv":
            self._to_csv(results, path)
        else:
            raise ValueError(f"Formato no soportado: '{fmt}'. Usa 'json' o 'csv'.")

        logger.info("Resultados exportados (%d filas) → %s", len(results), path)
        return path

    # ── Métodos privados ──────────────────────────────────────────────────────

    def _to_json(self, results: Sequence[ScrapeResult], path: Path) -> None:
        rows = []
        for r in results:
            row = r.to_dict()
            if "quality_report" in r.metadata:
                # Cuando hay informe, el campo content ya es un resumen legible.
                row["content"] = r.content
                report_path = self._save_text_report(r)
                row["report_txt"] = str(report_path)
            else:
                # Modo scraping tradicional: guardar HTML por separado.
                raw_path = self._save_raw_content(r)
                row["content"] = str(raw_path)
                row["report_txt"] = "No generado (sin auditoria de calidad)."
            rows.append(row)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    def _to_csv(self, results: Sequence[ScrapeResult], path: Path) -> None:
        if not results:
            path.write_text("", encoding="utf-8")
            return
        rows = []
        for r in results:
            row = r.to_dict()
            if "quality_report" in r.metadata:
                row["content"] = r.content
                report_path = self._save_text_report(r)
                row["report_txt"] = str(report_path)
            else:
                raw_path = self._save_raw_content(r)
                row["content"] = str(raw_path)
                row["report_txt"] = "No generado (sin auditoria de calidad)."
            rows.append(row)
        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _save_raw_content(self, result: ScrapeResult) -> Path:
        """Guarda el HTML prettificado en data/raw/ y devuelve la ruta."""
        raw_dir = settings.RAW_DIR
        raw_dir.mkdir(parents=True, exist_ok=True)
        slug = (
            result.url
            .replace("https://", "")
            .replace("http://", "")
            .replace("/", "_")
            .strip("_")[:60]
        )
        path = raw_dir / f"{slug}_{self._timestamp()}.html"
        path.write_text(result.content, encoding="utf-8")
        logger.debug("HTML guardado → %s", path)
        return path

    def _save_text_report(self, result: ScrapeResult) -> Path:
        """Guarda un informe TXT legible en data/reports/."""
        reports_dir = settings.REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)
        slug = (
            result.url
            .replace("https://", "")
            .replace("http://", "")
            .replace("/", "_")
            .strip("_")[:60]
        )
        path = reports_dir / f"{slug}_{self._timestamp()}.txt"
        path.write_text(result.content, encoding="utf-8")
        logger.debug("Informe TXT guardado → %s", path)
        return path

    def _build_path(self, fmt: str) -> Path:
        name = settings.OUTPUT_FILENAME_TEMPLATE.format(
            timestamp=self._timestamp(),
            ext=fmt,
        )
        return self.output_dir / name

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")