"""
Waiting The Longest™ - Export Utilities
========================================
Data export functionality for various formats.
"""

import csv
import json
from datetime import datetime
from io import StringIO, BytesIO
from typing import Any, Iterator
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# Export Formats
# =============================================================================

class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    JSON_LINES = "jsonl"
    EXCEL = "xlsx"


# =============================================================================
# Export Configuration
# =============================================================================

@dataclass
class ExportConfig:
    """Configuration for data export."""
    
    format: ExportFormat = ExportFormat.CSV
    include_headers: bool = True
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%dT%H:%M:%SZ"
    null_value: str = ""
    encoding: str = "utf-8"
    
    # CSV specific
    csv_delimiter: str = ","
    csv_quoting: int = csv.QUOTE_MINIMAL
    
    # JSON specific
    json_indent: int | None = 2
    json_ensure_ascii: bool = False


# =============================================================================
# Data Exporters
# =============================================================================

class BaseExporter:
    """Base class for data exporters."""
    
    def __init__(self, config: ExportConfig | None = None):
        self.config = config or ExportConfig()
    
    def export(self, data: list[dict]) -> str | bytes:
        """Export data to format."""
        raise NotImplementedError
    
    def export_stream(self, data: Iterator[dict]) -> Iterator[str | bytes]:
        """Export data as a stream."""
        raise NotImplementedError
    
    def _format_value(self, value: Any) -> Any:
        """Format a value for export."""
        if value is None:
            return self.config.null_value
        
        if isinstance(value, datetime):
            return value.strftime(self.config.datetime_format)
        
        if isinstance(value, bool):
            return "true" if value else "false"
        
        return value
    
    def _format_row(self, row: dict) -> dict:
        """Format all values in a row."""
        return {k: self._format_value(v) for k, v in row.items()}


class CSVExporter(BaseExporter):
    """Export data to CSV format."""
    
    def export(self, data: list[dict]) -> str:
        """Export data to CSV string."""
        if not data:
            return ""
        
        output = StringIO()
        
        # Get all unique keys
        fieldnames = list(data[0].keys())
        
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self.config.csv_delimiter,
            quoting=self.config.csv_quoting,
            extrasaction="ignore",
        )
        
        if self.config.include_headers:
            writer.writeheader()
        
        for row in data:
            writer.writerow(self._format_row(row))
        
        return output.getvalue()
    
    def export_stream(self, data: Iterator[dict]) -> Iterator[str]:
        """Export data as CSV stream."""
        first_row = True
        fieldnames = None
        
        for row in data:
            if first_row:
                fieldnames = list(row.keys())
                if self.config.include_headers:
                    yield self.config.csv_delimiter.join(fieldnames) + "\n"
                first_row = False
            
            formatted = self._format_row(row)
            values = [str(formatted.get(f, "")) for f in fieldnames]
            yield self.config.csv_delimiter.join(values) + "\n"


class JSONExporter(BaseExporter):
    """Export data to JSON format."""
    
    def export(self, data: list[dict]) -> str:
        """Export data to JSON string."""
        formatted_data = [self._format_row(row) for row in data]
        
        return json.dumps(
            formatted_data,
            indent=self.config.json_indent,
            ensure_ascii=self.config.json_ensure_ascii,
            default=str,
        )
    
    def export_stream(self, data: Iterator[dict]) -> Iterator[str]:
        """Export data as JSON stream (JSON Lines format)."""
        for row in data:
            formatted = self._format_row(row)
            yield json.dumps(
                formatted,
                ensure_ascii=self.config.json_ensure_ascii,
                default=str,
            ) + "\n"


class JSONLinesExporter(BaseExporter):
    """Export data to JSON Lines format (one JSON object per line)."""
    
    def export(self, data: list[dict]) -> str:
        """Export data to JSON Lines string."""
        lines = []
        for row in data:
            formatted = self._format_row(row)
            lines.append(json.dumps(
                formatted,
                ensure_ascii=self.config.json_ensure_ascii,
                default=str,
            ))
        return "\n".join(lines)
    
    def export_stream(self, data: Iterator[dict]) -> Iterator[str]:
        """Export data as JSON Lines stream."""
        for row in data:
            formatted = self._format_row(row)
            yield json.dumps(
                formatted,
                ensure_ascii=self.config.json_ensure_ascii,
                default=str,
            ) + "\n"


# =============================================================================
# Export Factory
# =============================================================================

def get_exporter(
    format: ExportFormat | str,
    config: ExportConfig | None = None,
) -> BaseExporter:
    """Get the appropriate exporter for a format."""
    if isinstance(format, str):
        format = ExportFormat(format.lower())
    
    exporters = {
        ExportFormat.CSV: CSVExporter,
        ExportFormat.JSON: JSONExporter,
        ExportFormat.JSON_LINES: JSONLinesExporter,
    }
    
    exporter_class = exporters.get(format)
    if not exporter_class:
        raise ValueError(f"Unsupported format: {format}")
    
    return exporter_class(config)


# =============================================================================
# Animal-Specific Export
# =============================================================================

class AnimalExporter:
    """
    Export animal data with optional transformations.
    """
    
    # Fields to include in export
    EXPORT_FIELDS = [
        "id",
        "name",
        "species",
        "breed",
        "age",
        "gender",
        "size",
        "description",
        "intake_date",
        "days_waiting",
        "shelter_name",
        "shelter_city",
        "shelter_state",
        "photo_url",
        "profile_url",
    ]
    
    def __init__(
        self,
        format: ExportFormat = ExportFormat.CSV,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
    ):
        self.format = format
        self.include_fields = include_fields or self.EXPORT_FIELDS
        self.exclude_fields = exclude_fields or []
    
    def _get_fields(self) -> list[str]:
        """Get list of fields to include."""
        return [f for f in self.include_fields if f not in self.exclude_fields]
    
    def _transform_animal(self, animal: Any) -> dict:
        """Transform animal model to export dictionary."""
        fields = self._get_fields()
        data = {}
        
        for field in fields:
            if field == "days_waiting":
                # Calculate from intake_date
                if hasattr(animal, "intake_date") and animal.intake_date:
                    days = (datetime.utcnow().date() - animal.intake_date.date()).days
                    data[field] = max(0, days)
                else:
                    data[field] = 0
            
            elif field == "shelter_name" and hasattr(animal, "shelter"):
                data[field] = animal.shelter.name if animal.shelter else ""
            
            elif field == "shelter_city" and hasattr(animal, "shelter"):
                data[field] = animal.shelter.city if animal.shelter else ""
            
            elif field == "shelter_state" and hasattr(animal, "shelter"):
                data[field] = animal.shelter.state if animal.shelter else ""
            
            elif field == "photo_url" and hasattr(animal, "photos"):
                photos = animal.photos or []
                data[field] = photos[0] if photos else ""
            
            elif field == "profile_url":
                data[field] = f"https://waitingthelongest.com/animals/{animal.id}"
            
            elif hasattr(animal, field):
                data[field] = getattr(animal, field)
            
            else:
                data[field] = ""
        
        return data
    
    def export(self, animals: list[Any]) -> str:
        """Export list of animals."""
        data = [self._transform_animal(a) for a in animals]
        exporter = get_exporter(self.format)
        return exporter.export(data)
    
    def export_stream(self, animals: Iterator[Any]) -> Iterator[str]:
        """Export animals as stream."""
        def transform_iter():
            for animal in animals:
                yield self._transform_animal(animal)
        
        exporter = get_exporter(self.format)
        yield from exporter.export_stream(transform_iter())


# =============================================================================
# Report Generation
# =============================================================================

@dataclass
class ReportConfig:
    """Configuration for report generation."""
    
    title: str = "Waiting The Longest Report"
    generated_at: datetime | None = None
    include_summary: bool = True
    include_charts: bool = False
    
    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.utcnow()


class ReportGenerator:
    """
    Generate reports from animal data.
    """
    
    def __init__(self, config: ReportConfig | None = None):
        self.config = config or ReportConfig()
    
    def generate_summary_report(
        self,
        animals: list[dict],
        stats: dict | None = None,
    ) -> str:
        """Generate a summary report."""
        lines = [
            f"# {self.config.title}",
            f"Generated: {self.config.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]
        
        if stats:
            lines.extend([
                "## Summary",
                f"- Total Animals: {stats.get('total_animals', 0)}",
                f"- Dogs: {stats.get('total_dogs', 0)}",
                f"- Cats: {stats.get('total_cats', 0)}",
                f"- Average Days Waiting: {stats.get('average_days_waiting', 0):.1f}",
                "",
            ])
        
        # Top 10 longest waiting
        lines.append("## Longest Waiting Animals")
        sorted_animals = sorted(
            animals,
            key=lambda x: x.get("days_waiting", 0),
            reverse=True,
        )[:10]
        
        for i, animal in enumerate(sorted_animals, 1):
            lines.append(
                f"{i}. {animal.get('name', 'Unknown')} - "
                f"{animal.get('species', '?')} - "
                f"{animal.get('days_waiting', 0)} days"
            )
        
        return "\n".join(lines)


# =============================================================================
# Content Types
# =============================================================================

CONTENT_TYPES = {
    ExportFormat.CSV: "text/csv",
    ExportFormat.JSON: "application/json",
    ExportFormat.JSON_LINES: "application/x-ndjson",
    ExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def get_content_type(format: ExportFormat) -> str:
    """Get content type for export format."""
    return CONTENT_TYPES.get(format, "application/octet-stream")


def get_file_extension(format: ExportFormat) -> str:
    """Get file extension for export format."""
    extensions = {
        ExportFormat.CSV: ".csv",
        ExportFormat.JSON: ".json",
        ExportFormat.JSON_LINES: ".jsonl",
        ExportFormat.EXCEL: ".xlsx",
    }
    return extensions.get(format, ".txt")
