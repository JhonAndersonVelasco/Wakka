#!/bin/bash
# Script de instalación de política de PolicyKit para Wakka

# Obtener el directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

POLICY_FILE="com.wakka.package-manager.policy"
POLICY_CLEAN_FILE="com.wakka.package-cleaner.policy"
POLICY_SERVICE_FILE="com.wakka.service-manager.policy"
POLICY_BACKGROUND_FILE="com.wakka.package-background.policy"
POLICY_DIR="/usr/share/polkit-1/actions"
HELPER_SCRIPT="wakka-helper"
HELPER_CLEAN_SCRIPT="wakka-cache-helper"
HELPER_SERVICE_SCRIPT="wakka-service-helper"
HELPER_BACKGROUND_SCRIPT="wakka-background-helper"
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

if [ ! -f "$POLICY_CLEAN_FILE" ]; then
    echo "❌ Error: No se encuentra $POLICY_CLEAN_FILE"
    exit 1
fi

if [ ! -f "$POLICY_SERVICE_FILE" ]; then
    echo "❌ Error: No se encuentra $POLICY_SERVICE_FILE"
    exit 1
fi

if [ ! -f "$POLICY_BACKGROUND_FILE" ]; then
    echo "❌ Error: No se encuentra $POLICY_BACKGROUND_FILE"
    exit 1
fi

if [ ! -f "$HELPER_CLEAN_SCRIPT" ]; then
    echo "❌ Error: No se encuentra $HELPER_CLEAN_SCRIPT"
    exit 1
fi

if [ ! -f "$HELPER_SERVICE_SCRIPT" ]; then
    echo "❌ Error: No se encuentra $HELPER_SERVICE_SCRIPT"
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

echo "📋 Instalando helper de limpieza en $HELPER_DIR/$HELPER_CLEAN_SCRIPT"
sudo cp "$HELPER_CLEAN_SCRIPT" "$HELPER_DIR/"
sudo chmod +x "$HELPER_DIR/$HELPER_CLEAN_SCRIPT"

if [ $? -ne 0 ]; then
    echo "❌ Error al instalar helper de limpieza"
    exit 1
fi

echo "📋 Instalando helper de servicios en $HELPER_DIR/$HELPER_SERVICE_SCRIPT"
sudo cp "$HELPER_SERVICE_SCRIPT" "$HELPER_DIR/"
sudo chmod +x "$HELPER_DIR/$HELPER_SERVICE_SCRIPT"

if [ $? -ne 0 ]; then
    echo "❌ Error al instalar helper de servicios"
    exit 1
fi

echo "📋 Creando link para helper de fondo en $HELPER_DIR/$HELPER_BACKGROUND_SCRIPT"
sudo ln -sf "$HELPER_DIR/$HELPER_SCRIPT" "$HELPER_DIR/$HELPER_BACKGROUND_SCRIPT"

if [ $? -ne 0 ]; then
    echo "❌ Error al crear link de helper de fondo"
    exit 1
fi

# Instalar política
echo "📋 Instalando política en $POLICY_DIR/$POLICY_FILE"
sudo cp "$POLICY_FILE" "$POLICY_DIR/"

if [ $? -ne 0 ]; then
    echo "❌ Error al instalar la política principal"
    exit 1
fi

echo "📋 Instalando política de limpieza en $POLICY_DIR/$POLICY_CLEAN_FILE"
sudo cp "$POLICY_CLEAN_FILE" "$POLICY_DIR/"

if [ $? -ne 0 ]; then
    echo "❌ Error al instalar la política de limpieza"
    exit 1
fi

echo "📋 Instalando política de servicios en $POLICY_DIR/$POLICY_SERVICE_FILE"
sudo cp "$POLICY_SERVICE_FILE" "$POLICY_DIR/"

if [ $? -ne 0 ]; then
    echo "❌ Error al instalar la política de servicios"
    exit 1
fi

echo "📋 Instalando política de fondo en $POLICY_DIR/$POLICY_BACKGROUND_FILE"
sudo cp "$POLICY_BACKGROUND_FILE" "$POLICY_DIR/"

if [ $? -eq 0 ]; then
    echo "✅ Instalación completada correctamente"
    echo
    echo "Ahora el diálogo de pkexec mostrará:"
    echo "  'Gestionar paquetes del sistema'"
    echo "y para limpiezas:"
    echo "  'Se requiere autenticacion para ejecutar limpieza de paquetes'"
    echo "y para configurar la actualización al apagar:"
    echo "  'Se requiere autenticacion para configurar la actualizacion al apagar'"
    echo "y las operaciones de fondo serán silenciosas."
    echo "en lugar del comando completo"
else
    echo "❌ Error al instalar la política"
    exit 1
fi
