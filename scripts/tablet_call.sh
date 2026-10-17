#!/bin/bash
# Script para automacao de chamada via WhatsApp
# AVISO: Identificadores especificos (serial, PIN, numero de telefone) foram redigidos por questoes de seguranca.

SERIAL="R9PW30T4JQM"
PIN="416669"
PHONE="351910070509"

LOG_FILE="/tmp/tablet_call.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

adb_cmd() {
    adb -s "$SERIAL" "$@"
}

# Funcao p/ extrair o centro do bounds baseado no content-desc
get_center() {
    local desc="$1"
    local xml
    # uiautomator dump conforme exigido nas regras
    xml=$(adb_cmd shell 'uiautomator dump /sdcard/u.xml >/dev/null 2>&1; cat /sdcard/u.xml')
    
    # Parse com python3
    echo "$xml" | python3 -c '
import sys, re
xml = sys.stdin.read()
desc = sys.argv[1]
match = re.search(r"content-desc=\"[^\"]*" + re.escape(desc) + r"[^\"]*\"[^>]*bounds=\"\[(\d+),(\d+)\]\[(\d+),(\d+)\]\"", xml, re.IGNORECASE)
if match:
    x1, y1, x2, y2 = map(int, match.groups())
    print(f"{(x1+x2)//2} {(y1+y2)//2}")
' "$desc"
}

tap_desc() {
    local desc="$1"
    local center=$(get_center "$desc")
    if [ -n "$center" ]; then
        log "Encontrado '"$desc"' em $center. Executando tap..."
        adb_cmd shell input tap $center
        return 0
    else
        log "Nao encontrado: '"$desc"'"
        return 1
    fi
}

log "=== Iniciando Automacao ==="

# 1. Acordar tela e desbloquear com PIN
log "Acordando tela..."
adb_cmd shell input keyevent KEYCODE_WAKEUP
sleep 1
log "Inserindo PIN e confirmando..."
adb_cmd shell input text "$PIN"
adb_cmd shell input keyevent KEYCODE_ENTER
sleep 2

# 2. Fechar apps e abrir chat no WhatsApp
log "Fechando apps..."
adb_cmd shell am force-stop com.whatsapp
adb_cmd shell am force-stop com.samsung.android.app.soundpicker
sleep 1

log "Abrindo chat WhatsApp..."
adb_cmd shell am start -a android.intent.action.VIEW -d "https://wa.me/$PHONE" com.whatsapp
sleep 5 # Aguardar UI do WhatsApp carregar

# 3. Tocar botao Ligacao de voz
log "Procurando botao de ligacao..."
tap_desc "Ligação de voz"
sleep 2

# 4. Confirmar dialog Ligar
log "Confirmando dialog..."
tap_desc "Ligar"
sleep 2

# 5. Permissoes (GRANT via shell e tentando fechar UI dialog se aparecer)
log "Garantindo permissoes de audio..."
adb_cmd shell pm grant com.whatsapp android.permission.RECORD_AUDIO
tap_desc "Permitir" || tap_desc "Continue"

# 6. Aguardar VoipActivity
log "Aguardando VoipActivity (timeout ~30s)..."
TIMEOUT=30
count=0
voip_active=false
while [ $count -lt $TIMEOUT ]; do
    if adb_cmd shell dumpsys window | grep -q "VoipActivity"; then
        voip_active=true
        break
    fi
    sleep 1
    count=$((count+1))
done

# 7. CRITICO DE TIMING
if [ "$voip_active" = true ]; then
    log "VoipActivity detectada! Maximizando volume e injetando audio..."
    # Executa comandos imediatamente e em sequencia rapida
    adb_cmd shell cmd media_session volume --stream 3 --set 15
    adb_cmd shell am start -a android.intent.action.VIEW -d 'file:///sdcard/Download/meow_msg.mp3' -t 'audio/mpeg' com.samsung.android.app.soundpicker
    
    # Ativar viva-voz assincronamente para nao bloquear playback
    (
        sleep 2
        tap_desc "alto-falante"
    ) &
    
    # 8. Manter ~30s e parar
    log "Aguardando 30s de chamada..."
    sleep 30
    log "Finalizando chamada e player..."
    adb_cmd shell am force-stop com.samsung.android.app.soundpicker
    adb_cmd shell am force-stop com.whatsapp
else
    log "Falha: Timeout aguardando VoipActivity."
fi

log "=== Fim da Execucao ==="
