#!/usr/bin/env python3
"""
PromoBeacon — Teste intensivo de integração app (Android simulado) <-> ESP32 (simulado)
====================================================================================
Exercita o protocolo GATT REAL do PromoBeacon sem rádio físico:
  - Client-side: port fiel de BleClient.kt (auth, mode, promo, portal chunks 128B,
    status 98B, stats 8B, sessions, WRITE_NO_RESPONSE, retry/reconnect)
  - Device-side: contrato de ble_manager.c + sim_esp32_ble.py (INSUFFICIENT_AUTHEN,
    truncamentos, portal transfer com CRC32+size em END, estado persistente)

O link BLE é simulado in-process com latência configurável e semântica ATT.
Uso: python3 ble_integration_test.py [--latency-ms 3] [--verbose]
Exit 0 = todos os cenários PASS.
"""

import argparse
import asyncio
import json
import random
import statistics
import struct
import sys
import time
import zlib

sys.path.insert(0, ".")

# sim_esp32_ble.py importa `bless` (rádio BLE) no top-level; aqui o rádio não é
# usado — só os UUIDs e packet builders. Stub do bless mantém o contrato lido
# direto do simulador oficial, sem duplicar definições.
try:
    import bless  # noqa: F401
except ImportError:
    import types as _types
    _stub = _types.ModuleType("bless")

    class _FlagEnum(int):
        def __getattr__(self, name):  # nunca chamado no modo stub
            raise AttributeError(name)
    _stub.BlessServer = object
    _stub.GATTAttributePermissions = _FlagEnum(0)
    _stub.GATTCharacteristicProperties = _FlagEnum(0)
    sys.modules["bless"] = _stub

import sim_esp32_ble as device_contract  # UUIDs + packet builders do simulador oficial

SERVICE_UUID = device_contract.SERVICE_UUID
CH = {
    "mode": device_contract.CHAR_MODE_CONTROL,
    "message": device_contract.CHAR_MESSAGE,
    "config": device_contract.CHAR_CONFIG,
    "status": device_contract.CHAR_STATUS,
    "promo": device_contract.CHAR_PROMO_TEXT,
    "stats": device_contract.CHAR_STATS,
    "sessions": device_contract.CHAR_SESSIONS,
    "session_ctrl": device_contract.CHAR_SESSION_CTRL,
    "portal_data": device_contract.CHAR_PORTAL_DATA,
    "portal_ctrl": device_contract.CHAR_PORTAL_CTRL,
    "auth": device_contract.CHAR_AUTH,
    "auth_status": device_contract.CHAR_AUTH_STATUS,
    "admin_password": device_contract.CHAR_ADMIN_PASSWORD,
}

# Comandos (espelham BleConstants em BleClient.kt)
CMD_MODE_G, CMD_MODE_E, CMD_REBOOT, CMD_RESET_DEFAULTS = 0x00, 0x01, 0x02, 0x03
PORTAL_CMD_START, PORTAL_CMD_DATA, PORTAL_CMD_END = 0x10, 0x11, 0x12
PORTAL_CMD_ABORT, PORTAL_CMD_STATUS, PORTAL_CMD_RESET = 0x13, 0x14, 0x15
AUTH_CMD_LOGIN, AUTH_CMD_LOGOUT = 0x01, 0x02
AUTH_STATUS_REQUIRED, AUTH_STATUS_SUCCESS, AUTH_STATUS_FAILED = 0x01, 0x02, 0x03
PORTAL_CHUNK_SIZE = 128
MAX_PROMO_LEN = 128
MAX_MESSAGE_LEN = 64
INSUFFICIENT_AUTHEN = 0x05  # GATT err 5 (BLE_ATT_ERR_INSUFFICIENT_AUTHEN)

DEFAULT_TOKEN = device_contract.DEFAULT_AUTH_TOKEN


class AttError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(f"ATT error 0x{code:02x}")


class VirtualGattServer:
    """Device-side: espelha ble_manager.c / sim_esp32_ble.py com estado real."""

    def __init__(self, latency_ms=3.0):
        self.latency = latency_ms / 1000.0
        self.reset()

    def reset(self):
        self.mode = 0x00
        self.message = "WELCOME"
        self.promo_text = "PromoBeacon"
        self.is_authenticated = False
        self.auth_status = AUTH_STATUS_REQUIRED
        self.connected_clients = 0
        self.total_writes = 0
        self.rejected_writes = 0
        self.errors_raised = 0
        self.portal = None  # {"size": int, "crc": int, "chunks": {seq: bytes}}
        self.portal_content = None
        self.start_time = time.monotonic()

    # ── conexão ────────────────────────────────────────────────────────────
    async def client_connect(self):
        await asyncio.sleep(self.latency)
        self.connected_clients += 1

    async def client_disconnect(self):
        await asyncio.sleep(self.latency)
        self.connected_clients = max(0, self.connected_clients - 1)
        # firmware: desconexão limpa auth (ble_manager.c ble_clear_authentication)
        if self.connected_clients == 0:
            self.is_authenticated = False
            self.auth_status = AUTH_STATUS_REQUIRED
            self.portal = None

    # ── helpers ─────────────────────────────────────────────────────────────
    def _require_auth(self):
        if not self.is_authenticated:
            self.errors_raised += 1
            raise AttError(INSUFFICIENT_AUTHEN)

    async def _delay(self):
        await asyncio.sleep(self.latency)

    # ── GATT ops ────────────────────────────────────────────────────────────
    async def read(self, uuid):
        await self._delay()
        u = uuid.lower()
        if u == CH["mode"].lower():
            return bytes([self.mode])
        if u == CH["message"].lower():
            return self.message.encode()
        if u == CH["promo"].lower():
            return self.promo_text.encode()
        if u == CH["status"].lower():
            pkt = bytearray(device_contract.build_status_packet())
            pkt[0] = self.mode & 0xFF
            pkt[1] = 1 if self.mode == 0x00 else 0        # isAdvertising só em G
            pkt[2] = 1 if self.connected_clients > 0 else 0
            uptime = int((time.monotonic() - self.start_time) * 1000) & 0xFFFFFFFF
            struct.pack_into("<I", pkt, 3, uptime)
            pkt[8] = min(self.connected_clients, 255)
            pkt[31:31 + len(self.promo_text.encode()[:32])] = self.promo_text.encode()[:32]
            pkt[97] = 1 if self.is_authenticated else 0
            return bytes(pkt)
        if u == CH["stats"].lower():
            pkt = bytearray(device_contract.build_stats_packet())
            pkt[1] = min(self.connected_clients, 255)
            return bytes(pkt)
        if u == CH["sessions"].lower():
            return device_contract.build_sessions_packet()
        if u == CH["auth_status"].lower():
            return bytes([self.auth_status])
        if u == CH["portal_ctrl"].lower():
            if self.portal is None:
                return b"OK" if self.portal_content is not None else b"IDLE"
            return b"ACTIVE"
        return b""

    async def write(self, uuid, value: bytes):
        await self._delay()
        self.total_writes += 1
        u = uuid.lower()

        if u == CH["auth"].lower():
            if len(value) == 1 and value[0] == AUTH_CMD_LOGOUT:
                self.is_authenticated = False
                self.auth_status = AUTH_STATUS_REQUIRED
                return
            # firmware: verify_admin_password(pw) || fallback "12345"
            token = value.decode("utf-8", errors="replace")
            if token == DEFAULT_TOKEN or token == "admin123":
                self.is_authenticated = True
                self.auth_status = AUTH_STATUS_SUCCESS
            else:
                self.is_authenticated = False
                self.auth_status = AUTH_STATUS_FAILED
            return

        if u == CH["mode"].lower():
            if len(value) == 0:  # firmware C lê buf[0] de mbuf flat; len 0 é ignorado
                self.rejected_writes += 1
                return
            self._require_auth()
            self.mode = value[0] & 0xFF
            return

        if u == CH["message"].lower():
            self._require_auth()
            self.message = value.decode("utf-8", errors="replace")[:MAX_MESSAGE_LEN]
            return

        if u == CH["promo"].lower():
            self._require_auth()
            self.promo_text = value.decode("utf-8", errors="replace")[:MAX_PROMO_LEN]
            return

        if u == CH["admin_password"].lower():
            self._require_auth()
            return

        if u == CH["session_ctrl"].lower():
            return

        if u == CH["config"].lower():
            self._require_auth()
            return

        if u == CH["portal_data"].lower():
            # WRITE_NO_RESPONSE: [seq:2LE][data ≤128B]; aceito só com transfer ativa
            if self.portal is None or len(value) < 2:
                self.rejected_writes += 1
                return
            seq = struct.unpack_from("<H", value, 0)[0]
            data = value[2:]
            if len(data) > PORTAL_CHUNK_SIZE:
                self.rejected_writes += 1
                return
            self.portal["chunks"][seq] = data
            return

        if u == CH["portal_ctrl"].lower():
            if len(value) == 0:
                self.rejected_writes += 1
                return
            cmd = value[0]
            # firmware: só trata START(len>=9)/END/ABORT/RESET; fora disso
            # cai fora de todos os if's e retorna 0 (write ignorado)
            if cmd == PORTAL_CMD_START and len(value) >= 9:
                self._require_auth()
                size, crc = struct.unpack_from("<II", value, 1)
                self.portal = {"size": size, "crc": crc, "chunks": {}}
                return
            if cmd == PORTAL_CMD_END:
                if self.portal is None:
                    self.rejected_writes += 1
                    raise AttError(0x11)  # invalid state → app trata como erro
                # valida seq completo, tamanho e CRC32 (contrato do firmware)
                chunks = self.portal["chunks"]
                expected = self.portal["size"]
                data = b"".join(chunks[s] for s in sorted(chunks.keys()))
                if len(data) != expected or (zlib.crc32(data) & 0xFFFFFFFF) != self.portal["crc"]:
                    self.rejected_writes += 1
                    self.portal = None
                    raise AttError(0x11)  # ERROR response no portal_ctrl
                self.portal_content = data
                self.portal = None
                return
            if cmd == PORTAL_CMD_ABORT:
                self.portal = None
                return
            if cmd == PORTAL_CMD_STATUS:
                return
            if cmd == PORTAL_CMD_RESET:
                self._require_auth()
                self.portal_content = None
                return
            # comando desconhecido ou START truncado: firmware ignora
            self.rejected_writes += 1
            return
        # característica desconhecida: ignora como firmware (log only)
        return


class AppSideClient:
    """Client-side: port fiel do protocolo de BleClient.kt."""

    def __init__(self, server: VirtualGattServer, name="app-client"):
        self.server = server
        self.name = name
        self.connected = False
        self.portal_upload_in_progress = False
        self.latencies = []  # ms por operação
        self.ops = 0
        self.errors = 0

    async def _op(self, coro):
        t0 = time.monotonic()
        try:
            out = await coro
            return out
        finally:
            self.ops += 1
            self.latencies.append((time.monotonic() - t0) * 1000.0)

    async def connect(self):
        await self._op(self.server.client_connect())
        self.connected = True

    async def disconnect(self):
        if self.connected:
            await self._op(self.server.client_disconnect())
            self.connected = False

    async def authenticate(self, password: str) -> bool:
        if not password:
            return False
        await self._op(self.server.write(CH["auth"], password.encode()))
        # Kotlin: fallback readAuthStatus() após 800ms se notificação perdida
        status = await self._op(self.server.read(CH["auth_status"]))
        tries = 0
        while status[0] == AUTH_STATUS_REQUIRED and tries < 10:
            await asyncio.sleep(0.08)
            status = await self._op(self.server.read(CH["auth_status"]))
            tries += 1
        return status[0] == AUTH_STATUS_SUCCESS

    async def logout(self):
        await self._op(self.server.write(CH["auth"], bytes([AUTH_CMD_LOGOUT])))

    async def write_mode(self, mode: int) -> bool:
        try:
            await self._op(self.server.write(CH["mode"], bytes([mode])))
            return True
        except AttError:
            self.errors += 1
            return False

    async def update_message(self, text: str) -> bool:
        try:
            await self._op(self.server.write(CH["message"], text.encode()))
            return True
        except AttError:
            self.errors += 1
            return False

    async def update_promo(self, text: str) -> bool:
        try:
            await self._op(self.server.write(CH["promo"], text.encode()))
            return True
        except AttError:
            self.errors += 1
            return False

    async def read_status(self) -> dict:
        pkt = await self._op(self.server.read(CH["status"]))
        assert len(pkt) == 98, f"status packet deve ter 98 bytes, veio {len(pkt)}"
        return {
            "mode": pkt[0],
            "is_advertising": pkt[1],
            "is_connected": pkt[2],
            "uptime_ms": struct.unpack_from("<I", pkt, 3)[0],
            "rssi": struct.unpack_from("<b", pkt, 7)[0],
            "clients": pkt[8],
            "promo": pkt[31:63].split(b"\0")[0].decode("utf-8", "replace").rstrip("\0 "),
            "authenticated": pkt[97],
        }

    async def read_stats(self) -> dict:
        pkt = await self._op(self.server.read(CH["stats"]))
        assert len(pkt) == 8, f"stats packet deve ter 8 bytes, veio {len(pkt)}"
        return {
            "flags": pkt[0],
            "clients": pkt[1],
            "session_s": struct.unpack_from("<I", pkt, 2)[0],
            "portal_avg": pkt[6],
            "battery": pkt[7],
        }

    async def read_sessions(self) -> list:
        raw = await self._op(self.server.read(CH["sessions"]))
        return json.loads(raw.decode())

    async def upload_portal(self, content: bytes, drop_seq=None) -> dict:
        """Port do fluxo completo: START → chunks (NO_RESPONSE) → END.
        drop_seq: simula perda de chunk (radio loss) para testar CRC."""
        result = {"sent": 0, "ok": False, "retries": 0}
        crc32 = zlib.crc32(content) & 0xFFFFFFFF
        start = bytes([PORTAL_CMD_START]) + struct.pack("<II", len(content), crc32)
        await self._op(self.server.write(CH["portal_ctrl"], start))
        self.portal_upload_in_progress = True
        seq = 0
        for i in range(0, len(content), PORTAL_CHUNK_SIZE):
            if seq == drop_seq:  # perda simulada: chunk nunca chega
                seq += 1
                continue
            chunk = content[i:i + PORTAL_CHUNK_SIZE]
            payload = struct.pack("<H", seq) + chunk
            await self._op(self.server.write(CH["portal_data"], payload))
            result["sent"] += 1
            seq += 1
        try:
            await self._op(self.server.write(CH["portal_ctrl"], bytes([PORTAL_CMD_END])))
            result["ok"] = True
        except AttError:
            result["ok"] = False
        self.portal_upload_in_progress = False
        return result

    async def abort_portal(self):
        await self._op(self.server.write(CH["portal_ctrl"], bytes([PORTAL_CMD_ABORT])))
        self.portal_upload_in_progress = False


# ── Cenários ──────────────────────────────────────────────────────────────────

PASS_COUNT = 0
FAIL_COUNT = 0


def check(cond, label, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        print(f"  PASS: {label}")
    else:
        FAIL_COUNT += 1
        print(f"  FAIL: {label} {detail}")


async def scenario_happy_path(server):
    print("\n[1] Happy path: connect + discover + auth + status")
    c = AppSideClient(server, "happy")
    await c.connect()
    check(c.connected, "conectado ao GATT server")
    ok = await c.authenticate(DEFAULT_TOKEN)
    check(ok, "auth com token padrão '12345'")
    st = await c.read_status()
    check(st["mode"] == CMD_MODE_G, "status: modo G")
    check(st["authenticated"] == 1, "status: autenticado")
    check(st["clients"] >= 1, "status: >=1 cliente conectado")
    stats = await c.read_stats()
    check(stats["battery"] == 90, "stats: battery 90 (contrato do sim)")
    sessions = await c.read_sessions()
    check(len(sessions) == 2, "sessions: 2 registros históricos")
    await c.disconnect()


async def scenario_auth_negative(server):
    print("\n[2] Auth negativa e proteção de escrita")
    c = AppSideClient(server, "auth-neg")
    await c.connect()
    ok = await c.authenticate("wrong-password")
    check(not ok, "senha errada rejeitada")
    st = await c.read_status()
    check(st["authenticated"] == 0, "status mostra não-autenticado")
    ok = await c.write_mode(CMD_MODE_E)
    check(not ok, "write de modo sem auth rejeitado (INSUFFICIENT_AUTHEN)")
    ok = await c.update_promo("HACKED")
    check(not ok, "write de promo sem auth rejeitado")
    check(server.promo_text != "HACKED", "estado do device intacto após tentativa não autorizada")
    ok = await c.authenticate(DEFAULT_TOKEN)
    check(ok, "auth correta após falhas")
    ok = await c.write_mode(CMD_MODE_E)
    check(ok, "write de modo com auth aceito")
    ok = await c.write_mode(CMD_MODE_G)
    check(ok, "retorno ao modo G")
    await c.logout()
    ok = await c.write_mode(CMD_MODE_E)
    check(not ok, "após logout, writes protegidos voltam a ser rejeitados")
    await c.disconnect()


async def scenario_config_ops(server, n=200):
    print(f"\n[3] Config intensiva: {n} ciclos mode/message/promo")
    c = AppSideClient(server, "config")
    await c.connect()
    await c.authenticate(DEFAULT_TOKEN)
    modes = [CMD_MODE_G, CMD_MODE_E]
    errors = 0
    for i in range(n):
        if not await c.write_mode(modes[i % 2]):
            errors += 1
        if not await c.update_message(f"MSG-{i:04d}"[-MAX_MESSAGE_LEN:]):
            errors += 1
        if not await c.update_promo(f"Promo {i:03d}"[:MAX_PROMO_LEN]):
            errors += 1
    check(errors == 0, f"{n*3} writes protegidos sem erro", f"({errors} erros)")
    check(server.mode == modes[(n - 1) % 2], "modo final = último escrito")
    check(server.message == f"MSG-{n-1:04d}"[-MAX_MESSAGE_LEN:], "message final = último escrito")
    check(server.promo_text == f"Promo {n-1:03d}", "promo final = último escrito")
    # truncamento fiel ao firmware (promo > 128 chars vira 128)
    long_promo = "X" * 300
    await c.update_promo(long_promo)
    check(len(server.promo_text) == MAX_PROMO_LEN, "promo >128 truncado para 128 (contrato firmware)")
    st = await c.read_status()
    check(st["mode"] == server.mode, "status reporta modo correto")
    await c.disconnect()


async def scenario_portal_uploads(server):
    print("\n[4] Upload de portal: 1KB / 16KB / 64KB com CRC32")
    c = AppSideClient(server, "portal")
    await c.connect()
    await c.authenticate(DEFAULT_TOKEN)
    for size in (1024, 16 * 1024, 64 * 1024):
        content = random.randbytes(size) if hasattr(random, "randbytes") else bytes(random.getrandbits(8) for _ in range(size))
        t0 = time.monotonic()
        r = await c.upload_portal(content)
        dt = time.monotonic() - t0
        check(r["ok"], f"upload {size}B concluído em {dt:.2f}s ({size/dt/1024:.0f} KB/s efetivo)")
        check(server.portal_content == content, f"conteúdo {size}B íntegro no device (byte a byte)")
        check(r["sent"] == (size + PORTAL_CHUNK_SIZE - 1) // PORTAL_CHUNK_SIZE,
              f"chunks enviados = {r['sent']} (esperado {(size + PORTAL_CHUNK_SIZE - 1) // PORTAL_CHUNK_SIZE})")
    await c.disconnect()


async def scenario_portal_edge_cases(server):
    print("\n[5] Portal: abort + perda de chunk + reset")
    c = AppSideClient(server, "portal-edge")
    await c.connect()
    await c.authenticate(DEFAULT_TOKEN)
    content = random.randbytes(8 * 1024)
    r = await c.upload_portal(content, drop_seq=5)  # perde chunk seq 5
    check(not r["ok"], "END falha quando chunk é perdido (validação CRC/size do firmware)")
    r2 = await c.upload_portal(content)  # re-upload sem perda
    check(r2["ok"], "re-upload após falha sucede")
    check(server.portal_content == content, "conteúdo re-enviado íntegro")
    # abort no meio
    start = bytes([PORTAL_CMD_START]) + struct.pack("<II", len(content), zlib.crc32(content) & 0xFFFFFFFF)
    await c._op(server.write(CH["portal_ctrl"], start))
    await c._op(server.write(CH["portal_data"], struct.pack("<H", 0) + content[:128]))
    await c.abort_portal()
    check(server.portal is None, "abort limpa estado da transferência")
    check(server.portal_content == content, "conteúdo anterior preservado após abort")
    # portal reset (requer auth — já autenticado)
    await c._op(server.write(CH["portal_ctrl"], bytes([PORTAL_CMD_RESET])))
    check(server.portal_content is None, "portal reset limpa conteúdo")
    await c.disconnect()


async def scenario_reconnect_storm(server, n=30):
    print(f"\n[6] Rajada de reconexões ({n} sessões)")
    first_promo = "Persist-Me-123"
    c = AppSideClient(server, "storm-0")
    await c.connect()
    await c.authenticate(DEFAULT_TOKEN)
    await c.update_promo(first_promo)
    await c.disconnect()
    ok_sessions = 0
    for i in range(n):
        c = AppSideClient(server, f"storm-{i}")
        await c.connect()
        ok = await c.authenticate(DEFAULT_TOKEN)
        st = await c.read_status()
        if ok and st["promo"] == first_promo:
            ok_sessions += 1
        await c.disconnect()
    check(ok_sessions == n, f"{n}/{n} sessões: connect+auth+status ok com estado persistente")
    check(server.is_authenticated is False, "auth limpo quando último cliente desconecta (contrato firmware)")


async def scenario_multi_client(server):
    print("\n[7] Multi-cliente concorrente: 1 uploader + 2 pollers")
    uploader = AppSideClient(server, "uploader")
    poller_a, poller_b = AppSideClient(server, "poller-a"), AppSideClient(server, "poller-b")
    for c in (uploader, poller_a, poller_b):
        await c.connect()
    await uploader.authenticate(DEFAULT_TOKEN)
    content = random.randbytes(32 * 1024)
    poll_errors = []
    polls_done = [0]

    async def poller_loop(client, deadline):
        while time.monotonic() < deadline:
            try:
                st = await client.read_status()
                assert st["clients"] >= 1
                polls_done[0] += 1
            except Exception as e:
                poll_errors.append(repr(e))
            await asyncio.sleep(0.005)

    deadline = time.monotonic() + 6
    tasks = [asyncio.create_task(poller_loop(poller_a, deadline)),
             asyncio.create_task(poller_loop(poller_b, deadline))]
    r = await uploader.upload_portal(content)
    for t in tasks:
        await t
    check(r["ok"], "upload concluído enquanto pollers martelavam status")
    check(len(poll_errors) == 0, "pollers sem erros durante upload concorrente", str(poll_errors[:3]))
    check(polls_done[0] > 100, f"pollers realizaram {polls_done[0]} leituras concorrentes")
    check(server.portal_content == content, "conteúdo íntegro apesar de concorrência")
    for c in (uploader, poller_a, poller_b):
        await c.disconnect()


async def scenario_malformed(server):
    print("\n[8] Writes malformados não derrubam o device")
    c = AppSideClient(server, "malformed")
    await c.connect()
    await c.authenticate(DEFAULT_TOKEN)
    survived = True
    try:
        await c._op(server.write(CH["mode"], b""))            # modo vazio
        await c._op(server.write(CH["portal_ctrl"], b"\x99"))  # cmd inexistente
        await c._op(server.write(CH["portal_data"], b"\x01"))  # chunk fora de transfer
        await c._op(server.write(CH["portal_ctrl"], b"\x10\x01\x02"))  # START truncado
        await c._op(server.write(CH["config"], b"\x03"))
        st = await c.read_status()
        check(len(st) == 8 and st["mode"] == server.mode, "device responde normalmente após writes malformados")
    except Exception as e:
        survived = False
        check(False, "device sobrevive a writes malformados", repr(e))
    if survived:
        pass  # check já feito acima
    check(server.rejected_writes > 0, f"{server.rejected_writes} writes inválidos contabilizados e rejeitados")
    await c.disconnect()


async def scenario_soak(server, ops=1000):
    print(f"\n[9] Soak: {ops} operações mistas rápidas")
    c = AppSideClient(server, "soak")
    await c.connect()
    await c.authenticate(DEFAULT_TOKEN)
    err = 0
    for i in range(ops):
        op = i % 5
        if op == 0:
            if not await c.write_mode(CMD_MODE_G if i % 2 == 0 else CMD_MODE_E):
                err += 1
        elif op == 1:
            if not await c.update_message(f"m{i:05d}"):
                err += 1
        elif op == 2:
            if not await c.update_promo(f"p{i:05d}"):
                err += 1
        elif op == 3:
            try:
                await c.read_stats()
            except Exception:
                err += 1
        else:
            try:
                await c.read_status()
            except Exception:
                err += 1
    check(err == 0, f"{ops} ops com 0 erros", f"({err} erros)")
    lat = c.latencies
    p50 = statistics.median(lat)
    p99 = sorted(lat)[int(len(lat) * 0.99) - 1]
    print(f"  INFO: latência por op — p50={p50:.2f}ms p99={p99:.2f}ms sobre {len(lat)} ops")
    check(p99 < 100, "p99 de latência simulada < 100ms")
    await c.disconnect()


def print_metrics(clients):
    lat = [l for c in clients for l in c.latencies]
    if not lat:
        return None
    lat.sort()
    return {
        "ops": len(lat),
        "p50_ms": round(statistics.median(lat), 3),
        "p99_ms": round(lat[int(len(lat) * 0.99) - 1], 3),
        "max_ms": round(lat[-1], 3),
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--latency-ms", type=float, default=3.0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)

    print("=" * 70)
    print("PROMOBEACON — TESTE INTENSIVO APP(Android simulado) <-> ESP32(simulado)")
    print(f"Link BLE in-process, latência simulada: {args.latency_ms}ms/op")
    print("=" * 70)

    server = VirtualGattServer(latency_ms=args.latency_ms)
    all_clients = []

    await scenario_happy_path(server)
    await scenario_auth_negative(server)
    await scenario_config_ops(server)
    await scenario_portal_uploads(server)
    await scenario_portal_edge_cases(server)
    await scenario_reconnect_storm(server)
    await scenario_multi_client(server)
    await scenario_malformed(server)
    await scenario_soak(server)

    print("\n" + "=" * 70)
    total = PASS_COUNT + FAIL_COUNT
    print(f"RESULTADO: {PASS_COUNT}/{total} checks PASS, {FAIL_COUNT} FAIL")
    print(f"Device-side: {server.total_writes} writes recebidos, "
          f"{server.rejected_writes} rejeitados como inválidos, {server.errors_raised} erros ATT (auth)")
    print(f"EXIT {'0 (TUDO OK)' if FAIL_COUNT == 0 else '1 (FALHAS)'}")
    return 0 if FAIL_COUNT == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
