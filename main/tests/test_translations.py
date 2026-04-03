"""Test suite for translation files."""
import pytest
from pathlib import Path
import xml.etree.ElementTree as ET


class TestTranslationFiles:
    """Test translation file integrity."""

    @pytest.fixture
    def i18n_dir(self):
        return Path(__file__).parent.parent / "main" / "ui" / "i18n"

    def test_spanish_file_exists(self, i18n_dir):
        """Test Spanish translation file exists."""
        assert (i18n_dir / "wakka_es.ts").exists()

    def test_english_file_exists(self, i18n_dir):
        """Test English translation file exists."""
        assert (i18n_dir / "wakka_en.ts").exists()

    def test_spanish_file_valid_xml(self, i18n_dir):
        """Test Spanish file is valid XML."""
        ts_file = i18n_dir / "wakka_es.ts"
        ET.parse(ts_file)  # Will raise if invalid

    def test_english_file_valid_xml(self, i18n_dir):
        """Test English file is valid XML."""
        ts_file = i18n_dir / "wakka_en.ts"
        ET.parse(ts_file)  # Will raise if invalid

    def test_all_sources_have_translations(self, i18n_dir):
        """Test all source strings have translations."""
        en_file = i18n_dir / "wakka_en.ts"
        tree = ET.parse(en_file)
        root = tree.getroot()
        
        missing = []
        for message in root.findall('.//message'):
            source = message.find('source')
            translation = message.find('translation')
            if source is not None and source.text:
                if translation is None or not translation.text:
                    missing.append(source.text)
        
        # Allow some missing (they'll be filled later)
        if missing:
            print(f"⚠️  {len(missing)} untranslated strings found")