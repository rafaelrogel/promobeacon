#!/system/bin/sh
# 📱 Optimize Samsung Galaxy Tab A7 Lite
# Execute as root or via "adb shell"

# -------------------------------------------------
# 1️⃣  Limpar caches de aplicativos (bloatware)
# -------------------------------------------------
packages=(
    com.android.browser               # Navegador padrão – pode ser substituído
    com.android.calendar              # Calendário
    com.android.messaging             # Mensagens padrão
    com.facebook.katana                # Facebook
    com.instagram.android              # Instagram
    com.whatsapp                       # WhatsApp (se usar outra conta, ignore)
    com.tiktok.android                 # TikTok
    com.netflix.mediaclient            # Netflix
    com.amazon.ags                     # Amazon Games
    com.samsung.android.app.tips       # Dicas Samsung
    com.samsung.android.app.spage      # Stories Samsung
    com.samsung.android.app.cards      # Cartões Samsung
    com.samsung.android.app.associated # Associated apps
    com.samsung.android.app.multiwindow # Multi‑window
    com.samsung.android.app.softwareupdate # Software Update
)

for pkg in "${packages[@]}"; do
    pm clear "$pkg"
done

# -------------------------------------------------
# 2️⃣  Parar serviços desnecessários
# -------------------------------------------------
svc power stop backup          # Serviço de backup
svc power stop idle            # Modo idle desnecessário
svc power stop mediaserver     # Media server (se não usar músicas)

# -------------------------------------------------
# 3️⃣  Remover animações (tornam a UI mais "instantânea")
# -------------------------------------------------
settings put global window_animation_scale 0.0
settings put global transition_animation_scale 0.0
settings put global animator_scale 0.0

# -------------------------------------------------
# 4️⃣  Desinstalar (uninstall) bloatware que não é crítico
# -------------------------------------------------
packages_to_uninstall=(
    com.samsung.android.app.tips
    com.samsung.android.app.spage
    com.samsung.android.app.cards
    com.samsung.android.app.associated
    com.samsung.android.app.multiwindow
    com.samsung.android.app.softwareupdate
)

for pkg in "${packages_to_uninstall[@]}"; do
    pm uninstall --user 0 "$pkg"
done

# -------------------------------------------------
# 5️⃣  Limpar resíduos de cache / lixo do sistema
# -------------------------------------------------
rm -rf /data/.trash /data/cache/* /data/tmp/*

# -------------------------------------------------
# 6️⃣  Ajuste final de performance (se o kernel permitir)
# -------------------------------------------------
# echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
# echo 1 > /proc/sys/vm/swappiness

echo "✅ Otimização concluída! Reinicie o tablet para aplicar todas as mudanças."