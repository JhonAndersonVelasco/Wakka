import sys
import os
from PyQt6.QtCore import QTranslator, QLocale, QLibraryInfo

# Add project root to path for standalone execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config_manager import ConfigManager

class Translator:
    def __init__(self):
        self.translator = QTranslator()
        self.qt_translator = QTranslator()
        
        config = ConfigManager()
        conf_lang = config.get("language", "auto")
        
        if conf_lang == "auto":
            self.locale = QLocale.system().name()  # ex. es_ES
        else:
            self.locale = conf_lang

    @staticmethod
    def run_update_tool(output_file: str = None) -> tuple[bool, str]:
        """Ejecuta pylupdate6 para generar o actualizar archivos .ts"""
        import subprocess
        from pathlib import Path
        
        # El directorio raíz para buscar es src/
        root = Path(__file__).resolve().parent.parent
        i18n_dir = root / "i18n"
        
        # Archivos .py fuente
        py_files = [str(p) for p in root.rglob("*.py")]
        
        # Archivos .ts destino (template + los que ya existan)
        ts_targets = [str(i18n_dir / "template.ts")]
        if i18n_dir.exists():
            for f in i18n_dir.glob("*.ts"):
                if f.name != "template.ts" and f.name != "template.ts":
                   ts_targets.append(str(f))
        
        try:
            # pylupdate6 solo acepta UN archivo -ts por llamada, así que iteramos
            for ts_file in ts_targets:
                cmd = ["pylupdate6"] + py_files + ["-ts", ts_file]
                subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))
            
            print(f"✓ Archivos .ts actualizados: {', '.join([Path(t).name for t in ts_targets])}")
            return True, "All files updated"
        except Exception as e:
            print(f"Excepción: {e}")
            return False, str(e)

    def load(self, app):
        # Directorio de traducciones será local a src/i18n
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        translations_dir = os.path.join(root, "i18n")


        # 1. Cargar Traducción de Wakka (ej. wakka_es.qm o es.qm)
        # Intentar varias combinaciones: wakka_en_US, en_US, wakka_en, en
        locales_to_try = [f"wakka_{self.locale}", self.locale]
        if "_" in self.locale:
            short_loc = self.locale.split("_")[0]
            locales_to_try.extend([f"wakka_{short_loc}", short_loc])

        loaded = False
        for loc in locales_to_try:
            if self.translator.load(loc, translations_dir):
                loaded = True
                app.installTranslator(self.translator)
                break

        # 2. Cargar Traducción Base de Qt (ej. qt_es.qm)
        qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        qt_loaded = self.qt_translator.load(f"qt_{self.locale}", qt_path)
        
        # Fallback a nombre corto para Qt
        if not qt_loaded and "_" in self.locale:
            short_loc = self.locale.split("_")[0]
            qt_loaded = self.qt_translator.load(f"qt_{short_loc}", qt_path)
            
        if qt_loaded:
            app.installTranslator(self.qt_translator)

        return loaded

    @staticmethod
    def compile_ts(ts_path: str) -> tuple[bool, str]:
        """Compila un archivo .ts a .qm usando lrelease"""
        import subprocess
        from pathlib import Path
        
        ts_file = Path(ts_path)
        qm_file = ts_file.with_suffix('.qm')
        
        try:
            cmd = ["lrelease", str(ts_file), "-qm", str(qm_file)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode == 0:
                return True, f"✓ Compilado: {qm_file.name}"
            else:
                return False, proc.stderr
        except Exception as e:
            return False, str(e)

if __name__ == "__main__":
    # Si se ejecuta directamente, genera el template.ts
    Translator.run_update_tool()