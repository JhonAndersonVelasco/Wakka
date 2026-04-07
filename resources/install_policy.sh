#!/bin/bash
# Script de instalación de política de PolicyKit para Wakka

# Obtener el directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

POLICY_FILE="com.wakka.package-manager.policy"
POLICY_DIR="/usr/share/polkit-1/actions"
HELPER_SCRIPT="wakka-helper"
HELPER_DIR="/usr/bin"

echo "=== Instalador de política PolicyKit para Wakka ==="
echo "Ejecutando desde: $SCRIPT_DIR"
echo

# Verificar archivos
if [ ! -f "$POLICY_FILE" ]; then
    echo "❌ Error: No se encuentra $POLICY_FILE"
    exit 1
fi

if [ ! -f "$HELPER_SCRIPT" ]; then
    echo "❌ Error: No se encuentra $HELPER_SCRIPT"
    exit 1
fi

# Instalar helper script
echo "📋 Instalando helper script en $HELPER_DIR/$HELPER_SCRIPT"
sudo cp "$HELPER_SCRIPT" "$HELPER_DIR/"
sudo chmod +x "$HELPER_DIR/$HELPER_SCRIPT"

if [ $? -ne 0 ]; then
    echo "❌ Error al instalar helper script"
    exit 1
fi

# Instalar política
echo "📋 Instalando política en $POLICY_DIR/$POLICY_FILE"
sudo cp "$POLICY_FILE" "$POLICY_DIR/"

if [ $? -eq 0 ]; then
    echo "✅ Instalación completada correctamente"
    echo
    echo "Ahora el diálogo de pkexec mostrará:"
    echo "  'Gestionar paquetes del sistema'"
    echo "en lugar del comando completo de yay"
else
    echo "❌ Error al instalar la política"
    exit 1
fi
