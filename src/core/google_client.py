import webbrowser
from urllib.parse import quote

class GoogleClient:
    def __init__(self):
        self.base_url = "https://www.google.com/search"

    def explain_package(self, package_name: str, description: str):
        """
        Abre el navegador con google preguntando sobre la app
        """
        from PyQt6.QtCore import QCoreApplication
        prompt = QCoreApplication.translate("GoogleClient", 
            "Explica qué es la aplicación {0} de Linux ({1}) de forma simple para un usuario normal, "
            "incluyendo para qué sirve y si vale la pena instalarla."
        ).format(package_name, description)
        encoded_prompt = quote(prompt)
        url = f"{self.base_url}?q={encoded_prompt}"
        webbrowser.open(url, new=2)
