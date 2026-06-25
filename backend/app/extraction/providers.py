from app.core.config import get_settings
from app.extraction.base import ExtractionProvider
from app.extraction.mock_provider import MockExtractionProvider


def get_extraction_provider() -> ExtractionProvider:
    settings = get_settings()
    provider = settings.EXTRACTION_PROVIDER.lower()
    if provider == "mock":
        return MockExtractionProvider()
    if provider == "textract":
        from app.extraction.textract_provider import TextractExtractionProvider

        return TextractExtractionProvider(settings)
    raise ValueError(f"Unsupported extraction provider: {settings.EXTRACTION_PROVIDER}")

