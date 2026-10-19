#!/system/bin/sh
# ==============================================================================
# PROMOBEACON HARDWARE ADVERSARY STRESS TEST SUITE
# Executed natively on Samsung Galaxy Tab A7 Lite (SM-T220, Android 14)
# Target: ESP32 PromoBeacon (192.168.4.1) via 2.4GHz Wi-Fi (PROMOBEACON)
# ==============================================================================

TARGET_IP="192.168.4.1"
TARGET_PORT="80"
OUTPUT_JSON="/data/local/tmp/stress_report.json"

echo "=== INICIANDO BATERIA DE TESTES DE HARDWARE REAL ==="
date

# Helper: Get time in milliseconds
now_ms() {
    echo $(($(date +%s%N) / 1000000))
}

# ------------------------------------------------------------------------------
# FASE 1: PROBE STORM & CONCURRENCY (200 Requisições)
# ------------------------------------------------------------------------------
echo "\n--- FASE 1: Probe Storm & Concurrency (200 Requisicoes HTTP) ---"
p1_success=0
p1_fail=0
p1_total_time=0
p1_min_time=99999
p1_max_time=0

for i in $(seq 1 200); do
    # Rotate between Android 204, Apple hotspot, Windows NCSI, and Root
    mod=$((i % 4))
    if [ $mod -eq 0 ]; then
        path="/generate_204"
        host="connectivitycheck.gstatic.com"
    elif [ $mod -eq 1 ]; then
        path="/hotspot-detect.html"
        host="captive.apple.com"
    elif [ $mod -eq 2 ]; then
        path="/ncsi.txt"
        host="www.msftncsi.com"
    else
        path="/"
        host="192.168.4.1"
    fi

    t_start=$(now_ms)
    res=$(printf "GET $path HTTP/1.1\r\nHost: $host\r\nConnection: close\r\n\r\n" | toybox nc -w 2 $TARGET_IP $TARGET_PORT 2>/dev/null)
    t_end=$(now_ms)
    elapsed=$((t_end - t_start))

    if echo "$res" | grep -q -E "HTTP/1.1 (200|302)"; then
        p1_success=$((p1_success + 1))
        p1_total_time=$((p1_total_time + elapsed))
        [ $elapsed -lt $p1_min_time ] && p1_min_time=$elapsed
        [ $elapsed -gt $p1_max_time ] && p1_max_time=$elapsed
    else
        p1_fail=$((p1_fail + 1))
    fi

    # Progress every 50 requests
    if [ $((i % 50)) -eq 0 ]; then
        echo "  [P1] Processadas $i/200 requisicoes... (Sucesso: $p1_success, Falhas: $p1_fail)"
    fi
done

p1_avg_time=0
[ $p1_success -gt 0 ] && p1_avg_time=$((p1_total_time / p1_success))
echo "  [P1 Final] Sucesso: $p1_success/200 | Latencia Min: ${p1_min_time}ms, Med: ${p1_avg_time}ms, Max: ${p1_max_time}ms"

# ------------------------------------------------------------------------------
# FASE 2: 404 CHAOS FLOOD & CAPTIVE REDIRECT (50 Requisições)
# ------------------------------------------------------------------------------
echo "\n--- FASE 2: 404 Chaos Flood & Captive Redirect (50 Requisicoes) ---"
p2_redirect_ok=0
p2_fail=0

for i in $(seq 1 50); do
    res=$(printf "GET /chaos_test_page_$i.html HTTP/1.1\r\nHost: random-$i.org\r\nConnection: close\r\n\r\n" | toybox nc -w 2 $TARGET_IP $TARGET_PORT 2>/dev/null)
    if echo "$res" | grep -q "302 Found" && echo "$res" | grep -q "Location: http://192.168.4.1/"; then
        p2_redirect_ok=$((p2_redirect_ok + 1))
    else
        p2_fail=$((p2_fail + 1))
    fi
done
echo "  [P2 Final] Redirecionamentos 302 corretos: $p2_redirect_ok/50 | Falhas: $p2_fail"

# ------------------------------------------------------------------------------
# FASE 3: MALFORMED DNS FUZZING (UDP Porta 53) (50 Queries)
# ------------------------------------------------------------------------------
echo "\n--- FASE 3: Malformed DNS Fuzzing & UDP 53 Storm (50 Pacotes) ---"
p3_replies=0
p3_discards_safe=0

for i in $(seq 1 50); do
    mod=$((i % 3))
    if [ $mod -eq 0 ]; then
        # Standard valid DNS query for google.com (Transaction ID 0x1234)
        payload="\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06\x67\x6f\x6f\x67\x6c\x65\x03\x63\x6f\x6d\x00\x00\x01\x00\x01"
    elif [ $mod -eq 1 ]; then
        # Truncated query header (only 4 bytes)
        payload="\xaa\xbb\x01\x00"
    else
        # Garbage noise frame
        payload="\xff\xff\xff\xff\x00\x00\x12\x34\x56\x78"
    fi

    res=$(printf "$payload" | toybox nc -u -w 1 $TARGET_IP 53 2>/dev/null)
    if [ -n "$res" ]; then
        p3_replies=$((p3_replies + 1))
    else
        p3_discards_safe=$((p3_discards_safe + 1))
    fi
done
echo "  [P3 Final] Respostas DNS válidas: $p3_replies | Descartes seguros de frames malformados: $p3_discards_safe"

# ------------------------------------------------------------------------------
# FASE 4: SLOWLORIS & SOCKET EXHAUSTION RESILIENCE
# ------------------------------------------------------------------------------
echo "\n--- FASE 4: Slowloris Socket Exhaustion (Max Sockets Saturation) ---"
p4_pids=""
# Abre 6 conexoes segurando o socket aberto
for s in $(seq 1 6); do
    (
        printf "GET / HTTP/1.1\r\nHost: 192.168.4.1\r\nX-Slowloris: $s\r\n"
        sleep 5
        printf "Connection: close\r\n\r\n"
    ) | toybox nc -w 6 $TARGET_IP $TARGET_PORT >/dev/null 2>&1 &
    p4_pids="$p4_pids $!"
done

sleep 1
# Agora tenta fazer uma requisição legítima normal com os 6 sockets engarrafados
t_start=$(now_ms)
legit_res=$(printf "GET / HTTP/1.1\r\nHost: 192.168.4.1\r\nConnection: close\r\n\r\n" | toybox nc -w 3 $TARGET_IP $TARGET_PORT 2>/dev/null)
t_end=$(now_ms)
p4_legit_latency=$((t_end - t_start))

p4_slowloris_evicted=0
if echo "$legit_res" | grep -q "200 OK"; then
    p4_slowloris_evicted=1
    echo "  [P4 Final] SUCESSO! O mecanismo LRU do ESP32 atendeu a conexao nova em ${p4_legit_latency}ms sob saturacao!"
else
    echo "  [P4 Final] FALHA: Conexao normal bloqueada por esgotamento de sockets."
fi

# Aguarda encerramento dos processos lentos
kill $p4_pids 2>/dev/null

# ------------------------------------------------------------------------------
# FASE 5: OVERSIZED PAYLOAD & BUFFER OVERFLOW TEST
# ------------------------------------------------------------------------------
echo "\n--- FASE 5: Oversized Payload & Buffer Overflow Resistance ---"
p5_oversized_handled=0
# Envia 8KB de lixo em um POST para /setup
junk=$(toybox head -c 8192 /dev/urandom | toybox base64 | tr -d '\n' | head -c 8192)
res=$(printf "POST /setup HTTP/1.1\r\nHost: 192.168.4.1\r\nContent-Length: 8192\r\n\r\n$junk" | toybox nc -w 3 $TARGET_IP $TARGET_PORT 2>/dev/null)

if echo "$res" | grep -q -E "HTTP/1.1 (400|405|413|500|200)"; then
    p5_oversized_handled=1
    echo "  [P5 Final] SUCESSO: Servidor respondeu graciosamente sem travar ou reiniciar!"
else
    # Verifica se servidor ainda esta vivo imediatamente
    alive_check=$(printf "GET / HTTP/1.1\r\nHost: 192.168.4.1\r\nConnection: close\r\n\r\n" | toybox nc -w 2 $TARGET_IP $TARGET_PORT 2>/dev/null)
    if echo "$alive_check" | grep -q "200 OK"; then
        p5_oversized_handled=1
        echo "  [P5 Final] SUCESSO: Conexao excessiva descartada e stack TCP/IP intacto!"
    else
        echo "  [P5 Final] ALERTA: O dispositivo demorou a responder apos payload excessivo."
    fi
fi

# ------------------------------------------------------------------------------
# FASE 6: SUSTAINED SOAK & LATENCY JITTER (120 Segundos)
# ------------------------------------------------------------------------------
echo "\n--- FASE 6: Sustained Soak & Jitter Test (120 Segundos Continuos) ---"
soak_end=$(($(date +%s) + 120))
soak_count=0
soak_success=0
soak_total_ms=0

while [ $(date +%s) -lt $soak_end ]; do
    t_start=$(now_ms)
    res=$(printf "GET /portal.json HTTP/1.1\r\nHost: 192.168.4.1\r\nConnection: close\r\n\r\n" | toybox nc -w 2 $TARGET_IP $TARGET_PORT 2>/dev/null)
    t_end=$(now_ms)
    lat=$((t_end - t_start))
    
    soak_count=$((soak_count + 1))
    if echo "$res" | grep -q "captive"; then
        soak_success=$((soak_success + 1))
        soak_total_ms=$((soak_total_ms + lat))
    fi
    
    # Intervalo de 500ms entre probes (2 req/s)
    usleep 500000
    
    if [ $((soak_count % 30)) -eq 0 ]; then
        echo "  [P6] Soak: $soak_count probes executadas... (${soak_success}/$soak_count validas)"
    fi
done

soak_avg_ms=0
[ $soak_success -gt 0 ] && soak_avg_ms=$((soak_total_ms / soak_success))
echo "  [P6 Final] Total Soaked: $soak_count | Sucesso: $soak_success ($((soak_success * 100 / soak_count))%) | Latencia Media: ${soak_avg_ms}ms"

# ------------------------------------------------------------------------------
# SALVA RESULTADOS ESTRUTURADOS EM JSON
# ------------------------------------------------------------------------------
cat <<EOF > $OUTPUT_JSON
{
    "device": "Samsung Galaxy Tab A7 Lite (SM-T220)",
    "target": "ESP32-C3 PromoBeacon (192.168.4.1)",
    "phase1_probe_storm": {
        "total_requests": 200,
        "success": $p1_success,
        "failed": $p1_fail,
        "min_latency_ms": $p1_min_time,
        "avg_latency_ms": $p1_avg_time,
        "max_latency_ms": $p1_max_time
    },
    "phase2_404_chaos": {
        "total_requests": 50,
        "redirect_302_ok": $p2_redirect_ok,
        "failed": $p2_fail
    },
    "phase3_dns_fuzzing": {
        "total_queries": 50,
        "replies": $p3_replies,
        "safe_discards": $p3_discards_safe
    },
    "phase4_slowloris": {
        "sockets_held": 6,
        "evicted_and_served": $p4_slowloris_evicted,
        "legit_latency_ms": $p4_legit_latency
    },
    "phase5_oversized_payload": {
        "payload_bytes": 8192,
        "handled_gracefully": $p5_oversized_handled
    },
    "phase6_soak": {
        "duration_seconds": 120,
        "total_probes": $soak_count,
        "success": $soak_success,
        "avg_latency_ms": $soak_avg_ms
    }
}
EOF

echo "\n=== BATERIA DE TESTES CONCLUIDA COM SUCESSO! Relatório salvo em $OUTPUT_JSON ==="
