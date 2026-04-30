#!/bin/bash
# Script de instalación de políticas de PolicyKit y Helpers para Wakka

# Obtener el directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

POLICY_DIR="/usr/share/polkit-1/actions"
HELPER_DIR="/usr/bin"
SYSTEMD_DIR="/etc/systemd/system"

# Listas de archivos a instalar
HELPERS=(
    "wakka-helper"
    "wakka-cache-helper"
    "wakka-service-helper"
    "wakka-background-helper"
    "wakka-shutdown-helper"
)

POLICIES=(
    "com.wakka.package-manager.policy"
    "com.wakka.package-cleaner.policy"
    "com.wakka.service-manager.policy"
    "com.wakka.package-background.policy"
)

SERVICES=(
    "wakka-shutdown.service"
)

# Función para desinstalar
uninstall() {
    echo "=== Desinstalador de componentes del sistema para Wakka ==="
    echo

    # 1. Eliminar Helpers
    echo "--- Eliminando Helpers de $HELPER_DIR ---"
    for helper in "${HELPERS[@]}"; do
        if [ -f "$HELPER_DIR/$helper" ]; then
            echo "🗑️  Eliminando $helper..."
            sudo rm -f "$HELPER_DIR/$helper"
        fi
    done

    # 2. Eliminar Políticas
    echo -e "\n--- Eliminando Políticas de $POLICY_DIR ---"
    for policy in "${POLICIES[@]}"; do
        if [ -f "$POLICY_DIR/$policy" ]; then
            echo "🗑️  Eliminando $policy..."
            sudo rm -f "$POLICY_DIR/$policy"
        fi
    done

    # 3. Eliminar Servicios
    echo -e "\n--- Eliminando Servicios de $SYSTEMD_DIR ---"
    for service in "${SERVICES[@]}"; do
        if [ -f "$SYSTEMD_DIR/$service" ]; then
            echo "🛑 Deteniendo y deshabilitando $service..."
            sudo systemctl stop "$service" 2>/dev/null
            sudo systemctl disable "$service" 2>/dev/null
            echo "🗑️  Eliminando $service..."
            sudo rm -f "$SYSTEMD_DIR/$service"
        fi
    done
    
    sudo systemctl daemon-reload

    echo -e "\n✅ Desinstalación completada correctamente"
    exit 0
}

# Verificar si se solicitó desinstalación
if [[ "$1" == "--uninstall" ]]; then
    uninstall
fi

echo "=== Instalador de componentes del sistema para Wakka ==="
echo "Ejecutando desde: $SCRIPT_DIR"
echo "Tip: Usa '$0 --uninstall' para eliminar los componentes del sistema."
echo

# 1. Instalar Helpers
echo "--- Instalando Helpers en $HELPER_DIR ---"
for helper in "${HELPERS[@]}"; do
    if [ -f "$helper" ]; then
        echo "📋 Instalando $helper..."
        sudo cp "$helper" "$HELPER_DIR/"
        sudo chmod +x "$HELPER_DIR/$helper"
        if [ $? -ne 0 ]; then
            echo "❌ Error al instalar $helper"
            exit 1
        fi
    else
        echo "❌ Error: No se encuentra $helper"
        exit 1
    fi
done

# 2. Instalar Políticas
echo -e "\n--- Instalando Políticas en $POLICY_DIR ---"
for policy in "${POLICIES[@]}"; do
    if [ -f "$policy" ]; then
        echo "📋 Instalando $policy..."
        sudo cp "$policy" "$POLICY_DIR/"
        if [ $? -ne 0 ]; then
            echo "❌ Error al instalar $policy"
            exit 1
        fi
    else
        echo "❌ Error: No se encuentra $policy"
        exit 1
    fi
done

# 3. Instalar Servicios
echo -e "\n--- Instalando Servicios en $SYSTEMD_DIR ---"
for service in "${SERVICES[@]}"; do
    if [ -f "$service" ]; then
        echo "📋 Instalando $service..."
        sudo cp "$service" "$SYSTEMD_DIR/"
        if [ $? -ne 0 ]; then
            echo "❌ Error al instalar $service"
            exit 1
        fi
    else
        echo "⚠️  Aviso: No se encuentra $service (opcional)"
    fi
done

echo -e "\n✅ Instalación completada correctamente"
echo
echo "Resumen de capacidades instaladas:"
echo "  - Gestión de paquetes: 'pkexec wakka-helper'"
echo "  - Limpieza de caché: 'pkexec wakka-cache-helper'"
echo "  - Gestión de servicios: 'pkexec wakka-service-helper'"
echo "  - Operaciones de fondo (sin contraseña): 'pkexec wakka-background-helper'"
echo "  - Actualización al apagar: 'wakka-shutdown.service' + 'wakka-shutdown-helper'"
echo
echo "Nota: El servicio de apagado se habilita/deshabilita desde la configuración de Wakka."
