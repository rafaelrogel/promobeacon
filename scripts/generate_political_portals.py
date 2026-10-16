#!/usr/bin/env python3
"""
PromoBeacon Political Campaigns Generator
Generates 20 distinct political captive portal templates across Brazilian history and politics.
All templates are self-contained (<5KB), responsive, offline-ready, with unique styling and interactive DOM toasts.
"""

import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PORTALS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "political_portals")
os.makedirs(PORTALS_DIR, exist_ok=True)

CANDIDATES = [
    {
        "id": "lula",
        "name": "Lula • O Brasil do Futuro",
        "badge": "⭐ Coligação Esperança Brasil",
        "avatar": "⭐",
        "title": "Lula da Silva",
        "slogan": "O Brasil Feliz de Novo • Trabalho, Picanha & Oportunidade",
        "theme": {"bg": "#140505", "card": "#260b0b", "primary": "#dc2626", "accent": "#fca5a5", "text": "#ffffff"},
        "points": ["🥩 Fim da inflação e picanha na mesa", "📚 Isenção de IR até R$ 5.000", "💊 Farmácia Popular ampliada"],
        "btn_text": "🥖 Resgatar Vale Picanha Simbólico",
        "toast_title": "🎉 VALE PICANHA SIMBÓLICO ATIVADO!",
        "toast_sub": "O Brasil voltou a sorrir. Baixe o plano de governo completo no link abaixo."
    },
    {
        "id": "bolsonaro",
        "name": "Jair Bolsonaro • Brasil Acima de Tudo",
        "badge": "🇧🇷 Pátria Amada • Liberdade",
        "avatar": "🇧🇷",
        "title": "Jair Messias Bolsonaro",
        "slogan": "Brasil Acima de Tudo, Deus Acima de Todos",
        "theme": {"bg": "#061309", "card": "#0e2915", "primary": "#16a34a", "accent": "#facc15", "text": "#ffffff"},
        "points": ["🔫 Direito à legítima defesa e porte rural", "📉 Redução de impostos e desregulamentação", "✝️ Valores da família e soberania"],
        "btn_text": "🇧🇷 Baixar Santinho Patriota Oficial",
        "toast_title": "🫡 SANTINHO PATRIOTICO COPIADO!",
        "toast_sub": "A verdade vos libertará. Compartilhe o lema no seu WhatsApp."
    },
    {
        "id": "eneas",
        "name": "Dr. Enéas Carneiro • PRONA 56",
        "badge": "⚛️ PRONA 56 • Soberania Absoluta",
        "avatar": "🧔",
        "title": "Dr. Enéas Carneiro",
        "slogan": "MEU NOME É ENÉAS! 56!",
        "theme": {"bg": "#081008", "card": "#132314", "primary": "#15803d", "accent": "#eab308", "text": "#ffffff"},
        "points": ["⚛️ Programa Nuclear Brasileiro dissuasório", "💎 Monopólio nacional de Nióbio e Grafeno", "🏭 Reindustrialização pesada em 4 anos"],
        "btn_text": "⚡ Discurso Histórico de 15 Segundos",
        "toast_title": "📢 MEU NOME É ENÉAS! CINQUENTA E SEIS!",
        "toast_sub": "O Brasil não está à venda. Soberania nuclear e tecnológica já."
    },
    {
        "id": "dom_pedro_ii",
        "name": "Dom Pedro II • Império do Brasil",
        "badge": "👑 Coroa Imperial Brasileira",
        "avatar": "👑",
        "title": "S.M. Dom Pedro II",
        "slogan": "Pela Honra da Pátria e o Progresso da Ciência",
        "theme": {"bg": "#061711", "card": "#0d2e22", "primary": "#047857", "accent": "#d4af37", "text": "#ffffff"},
        "points": ["🔭 Financiamento à astronomia e institutos", "📜 Diplomacia e respeito nas cortes mundiais", "⚖️ Poder Moderador em defesa da estabilidade"],
        "btn_text": "📜 Baixar Carta Régia do Império",
        "toast_title": "👑 DECRETO IMPERIAL OUTORGADO!",
        "toast_sub": "Viva o Império do Brasil! Que a instrução e a virtude iluminem o povo."
    },
    {
        "id": "marcal",
        "name": "Pablo Marçal • Desbloqueie sua Mente",
        "badge": "🧠 O Código do Milhão",
        "avatar": "🚀",
        "title": "Pablo Marçal",
        "slogan": "Chega de Governantes Fracos • Ative o Seu Pior Ano",
        "theme": {"bg": "#09090b", "card": "#18181b", "primary": "#7c3aed", "accent": "#06b6d4", "text": "#ffffff"},
        "points": ["🧠 Instalação de drives mentais de riqueza", "🚁 Cidade inteligente com helipontos populares", "💼 Fim do CLT: Seja dono do seu próprio destino"],
        "btn_text": "🔓 Destravar Código Mental 2026",
        "toast_title": "🚀 DRIVE MENTAL DESBLOQUEADO!",
        "toast_sub": "Você não nasceu para ser funcionário. Assuma o governo da sua própria vida!"
    },
    {
        "id": "renan_santos",
        "name": "Renan Santos • Missão MBL",
        "badge": "📒 Livro Amarelo • Refundação",
        "avatar": "⚔️",
        "title": "Renan Santos • Missão",
        "slogan": "Construir uma Nova Direita • O Futuro do Brasil",
        "theme": {"bg": "#0f0f12", "card": "#1c1c24", "primary": "#eab308", "accent": "#fde047", "text": "#ffffff"},
        "points": ["📒 Aplicação imediata do Livro Amarelo", "⚖️ Corte radical de regalias no Judiciário", "🎓 Meritocracia pura e vouchers de educação"],
        "btn_text": "📖 Baixar Livro Amarelo (PDF)",
        "toast_title": "⚔️ ALISTAMENTO NA MISSÃO CONFIRMADO!",
        "toast_sub": "O Livro Amarelo foi baixado para o dispositivo. Junte-se à bancada."
    },
    {
        "id": "maluf",
        "name": "Paulo Maluf • Maluf Faz!",
        "badge": "🏗️ São Paulo em Obras",
        "avatar": "🏗️",
        "title": "Paulo Maluf",
        "slogan": "Maluf Faz! As Obras que o Povo Pode Ver",
        "theme": {"bg": "#08101e", "card": "#101f3b", "primary": "#2563eb", "accent": "#f59e0b", "text": "#ffffff"},
        "points": ["🛣️ Túneis Ayrton Senna e grandes viadutos", "🚔 Tropa de Choque e ROTA patrulhando a rua", "🏥 Hospital de Primeiro Mundo para o trabalhador"],
        "btn_text": "🏗️ Ver Mapa de Túneis e Viadutos",
        "toast_title": "✅ ATESTADO DE OBRA CONCLUÍDA!",
        "toast_sub": "Falem o que quiserem, mas Maluf faz! Obra entregue no prazo."
    },
    {
        "id": "ciro_gomes",
        "name": "Ciro Gomes • Projeto Nacional (PND)",
        "badge": "📊 PND • Rebeldia com Causa",
        "avatar": "📈",
        "title": "Ciro Gomes",
        "slogan": "O Brasil Tem Saída • Projeto Nacional de Desenvolvimento",
        "theme": {"bg": "#140a10", "card": "#26131f", "primary": "#e11d48", "accent": "#2dd4bf", "text": "#ffffff"},
        "points": ["🧹 SPC Limpo: Refinanciamento popular em massa", "📊 Taxação de lucros, dividendos e fortunas", "🏭 Reindustrialização ecológica verde e portos"],
        "btn_text": "📈 Simular Meu Nome Fora do SPC",
        "toast_title": "📋 SIMULAÇÃO DO SPC CONCLUÍDA!",
        "toast_sub": "Dívida renegociada pelo PND. Baixe a íntegra do projeto econômico."
    },
    {
        "id": "getulio_vargas",
        "name": "Getúlio Vargas • Pai dos Pobres",
        "badge": "🏭 Trabalhismo • O Petróleo é Nosso",
        "avatar": "🎙️",
        "title": "Getúlio Dornelles Vargas",
        "slogan": "Trabalhadores do Brasil! A Força da Nossa Indústria",
        "theme": {"bg": "#0a140d", "card": "#14291a", "primary": "#15803d", "accent": "#d97706", "text": "#ffffff"},
        "points": ["💼 Criação da CLT, 13º e Férias Remuneradas", "🛢️ Fundação da Petrobras e da CSN", "📻 Voz do Brasil unindo a nação"],
        "btn_text": "📜 Baixar Cartilha da CLT 1943",
        "toast_title": "📻 TRABALHADORES DO BRASIL!",
        "toast_sub": "A legislação social está garantida. Nenhuma força deterá o povo trabalhador."
    },
    {
        "id": "jk",
        "name": "Juscelino Kubitschek • 50 Anos em 5",
        "badge": "🏛️ Meta-Síntese • Brasília",
        "avatar": "🚗",
        "title": "Juscelino Kubitschek",
        "slogan": "50 Anos de Progresso em 5 Anos de Governo",
        "theme": {"bg": "#06131c", "card": "#0d2538", "primary": "#0284c7", "accent": "#38bdf8", "text": "#ffffff"},
        "points": ["🏛️ Construção de Brasília no coração do país", "🚗 Fábricas de automóveis nacionais e estradas", "⚡ Centrais elétricas de Furnas e Três Marias"],
        "btn_text": "🗺️ Ver Maquete 3D do Plano Piloto",
        "toast_title": "🏛️ PLANO PILOTO CONECTADO!",
        "toast_sub": "Brasília erguida em tempo recorde! O Brasil do Centro-Oeste acordou."
    },
    {
        "id": "marina_silva",
        "name": "Marina Silva • Justiça Climática",
        "badge": "🌱 Sustentabilidade & Floresta",
        "avatar": "🌳",
        "title": "Marina Silva",
        "slogan": "Desenvolvimento com Proteção e Respeito à Vida",
        "theme": {"bg": "#06140a", "card": "#0e2916", "primary": "#16a34a", "accent": "#ca8a04", "text": "#ffffff"},
        "points": ["🌳 Desmatamento Zero e Guardiões da Floresta", "☀️ Transição energética solar e eólica rápida", "🏹 Demarcação e respeito aos povos originários"],
        "btn_text": "🌱 Plantar Árvore Digital no Beacon",
        "toast_title": "🍃 ÁRVORE DIGITAL REGISTRADA!",
        "toast_sub": "Sua ação foi catalogada no Cadastro Florestal Criptográfico do Beacon."
    },
    {
        "id": "daciolo",
        "name": "Cabo Daciolo • Glória a Deus",
        "badge": "⛰️ Monte das Oliveiras • Clamor",
        "avatar": "✝️",
        "title": "Cabo Benevenuto Daciolo",
        "slogan": "Glória a Deuxxx! A URSAL Não Vai Passar",
        "theme": {"bg": "#12081c", "card": "#241038", "primary": "#9333ea", "accent": "#eab308", "text": "#ffffff"},
        "points": ["✝️ Clamor nacional de joelhos pelo Brasil", "🛡️ Extinção de blocos secretos e plano URSAL", "🚨 Valorização máxima de policiais e bombeiros"],
        "btn_text": "⛰️ Subir ao Monte em Oração",
        "toast_title": "🕊️ GLÓRIA A DEUXXX NAS ALTURAS!",
        "toast_sub": "Oração recebida nos céus da nação! O plano do inimigo foi desarticulado."
    },
    {
        "id": "eduardo_jorge",
        "name": "Eduardo Jorge • Vida & Bicicleta",
        "badge": "🚲 Paz, Ecologia e Desarmamento",
        "avatar": "🚲",
        "title": "Dr. Eduardo Jorge",
        "slogan": "Não Tenho Nada a Ver com Isso • Mais Bike, Menos Stress",
        "theme": {"bg": "#06130b", "card": "#0e2617", "primary": "#22c55e", "accent": "#38bdf8", "text": "#ffffff"},
        "points": ["🚲 Ciclovias intermunicipais e transporte limpo", "🥦 Merenda 100% orgânica sem agrotóxicos", "🌿 Política humana de redução de danos"],
        "btn_text": "🚲 Calcular Minha Rota Pedalável",
        "toast_title": "🚴 ROTA SUSTENTÁVEL GERADA!",
        "toast_sub": "Deixe o carro na garagem e vá de pedal. Menos poluição, mais serotonina!"
    },
    {
        "id": "fhc",
        "name": "Fernando Henrique • Estabilidade Real",
        "badge": "💵 Plano Real • Moeda Forte",
        "avatar": "💵",
        "title": "Fernando Henrique Cardoso",
        "slogan": "A Estabilidade que Mudou a História Econômica",
        "theme": {"bg": "#09121f", "card": "#13233d", "primary": "#2563eb", "accent": "#fde047", "text": "#ffffff"},
        "points": ["💵 Fim da hiperinflação com o Real", "⚖️ Lei de Responsabilidade Fiscal permanente", "🎓 Fundo da Educação (FUNDEF) universalizado"],
        "btn_text": "💵 Ver Conversão URV para Real",
        "toast_title": "📊 ESTABILIDADE MONETÁRIA CHECADA!",
        "toast_sub": "Inflação sob controle e juros ancorados. Baixe o ensaio de governo."
    },
    {
        "id": "brizola",
        "name": "Leonel Brizola • CIEPs e Legalidade",
        "badge": "🎒 CIEPs em Tempo Integral • PDT",
        "avatar": "🎒",
        "title": "Leonel de Moura Brizola",
        "slogan": "Escola em Tempo Integral ou Cadeia no Futuro!",
        "theme": {"bg": "#170606", "card": "#2e0e0e", "primary": "#b91c1c", "accent": "#f59e0b", "text": "#ffffff"},
        "points": ["🎒 CIEPs com 4 refeições, banho e biblioteca", "🛡️ Cadeia para especuladores financeiros", "📻 Rede da Legalidade em defesa do povo"],
        "btn_text": "🏫 Conhecer Projeto dos Brizolões",
        "toast_title": "✊ REDE DA LEGALIDADE ATIVADA!",
        "toast_sub": "Educação em tempo integral é o único caminho contra a injustiça social."
    },
    {
        "id": "mamefalei",
        "name": "Arthur do Val • Cortando Privilégios",
        "badge": "✂️ Fim do Fundão Eleitoral",
        "avatar": "🎥",
        "title": "Arthur do Val • Mamãe Falei",
        "slogan": "Fiscalização sem Medo • Menos Político, Mais Cidadão",
        "theme": {"bg": "#121214", "card": "#212126", "primary": "#eab308", "accent": "#ef4444", "text": "#ffffff"},
        "points": ["✂️ Renúncia total a verbas e mordomias de gabinete", "📹 Fiscalização surpresa com câmera em hospitais e obras", "🚀 Desburocratização rápida para quem gera emprego"],
        "btn_text": "✂️ Cortar Mordomia Simbólica",
        "toast_title": "🔥 MORDOMIA DEPUTACIAL CORTADA!",
        "toast_sub": "Mais R$ 50.000 economizados aos cofres públicos. Assista ao vídeo da blitz."
    },
    {
        "id": "tancredo_neves",
        "name": "Tancredo Neves • Nova República",
        "badge": "🕊️ Diretas Já • Democracia",
        "avatar": "🕊️",
        "title": "Tancredo de Almeida Neves",
        "slogan": "Não Vamos nos Dispersar • A Pátria Reconciliada",
        "theme": {"bg": "#09121c", "card": "#132338", "primary": "#0369a1", "accent": "#38bdf8", "text": "#ffffff"},
        "points": ["🕊️ Transição pacífica e restabelecimento do voto", "📜 Nova Assembleia Constituinte Cidadã", "🤝 Grande Pacto de Reconstrução Nacional"],
        "btn_text": "📜 Assinar Livro da Democracia",
        "toast_title": "🕊️ VOTO CIDADÃO REGISTRADO!",
        "toast_sub": "A aurora democrática renasceu. Que ninguém impeça a vontade do povo!"
    },
    {
        "id": "plinio",
        "name": "Plínio de Arruda Sampaio • Sem Medo",
        "badge": "🌾 Reforma Agrária Radical",
        "avatar": "🌾",
        "title": "Plínio de Arruda Sampaio",
        "slogan": "Sem Medo de Ser Socialista • Contra o Latifúndio",
        "theme": {"bg": "#170606", "card": "#2e0d0d", "primary": "#b91c1c", "accent": "#facc15", "text": "#ffffff"},
        "points": ["🌾 Desapropriação imediata de latifúndios improdutivos", "🏥 Fim dos planos privados: SUS de excelência para todos", "🏦 Estatização do sistema bancário especulativo"],
        "btn_text": "🌾 Apoiar Assentamento Agroecológico",
        "toast_title": "✊ APOIO REGISTRADO NA REFORMA AGRÁRIA!",
        "toast_sub": "Terra para quem nela trabalha! O latifúndio improdutivo chegou ao fim."
    },
    {
        "id": "alckmin",
        "name": "Geraldo Alckmin • Picolé de Chuchu",
        "badge": "🚇 Gestão Equilibrada • PPPs",
        "avatar": "🚇",
        "title": "Dr. Geraldo Alckmin",
        "slogan": "Trabalho Sério, Sem Pirotecnia • O Rodoanel Funciona",
        "theme": {"bg": "#08101a", "card": "#122033", "primary": "#1d4ed8", "accent": "#94a3b8", "text": "#ffffff"},
        "points": ["🛣️ Conclusão de todos os trechos do Rodoanel", "🎓 Ampliação das ETECs e FATECs gratuitas", "☕ Café com pão de queijo e orçamento austero"],
        "btn_text": "🚇 Ver Mapa de Expansão Metroviária",
        "toast_title": "☕ CAFÉ COM MERENDA LIBERADO!",
        "toast_sub": "Gestão austera e contas em dia. Sem déficit fiscal e com obras no chão."
    },
    {
        "id": "padre_kelmon",
        "name": "Padre Kelmon • Candidato Padre",
        "badge": "✝️ Fé, Pátria e Família Tradicional",
        "avatar": "✝️",
        "title": "Padre Kelmon da Silva",
        "slogan": "Em Nome do Pai • A Voz dos Cristãos no Debate",
        "theme": {"bg": "#171206", "card": "#2b220d", "primary": "#b45309", "accent": "#fde047", "text": "#ffffff"},
        "points": ["✝️ Oração e leitura bíblica nas escolas", "🏛️ Isenção de impostos total a entidades religiosas", "🕊️ Combate intransigente ao materialismo e relativismo"],
        "btn_text": "✝️ Receber Bênção Virtual de Campanha",
        "toast_title": "🕊️ BÊNÇÃO APOSTÓLICA ENVIADA!",
        "toast_sub": "A paz esteja com você e sua família. O debate foi abençoado!"
    }
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>{title} — Campanha Oficial PromoBeacon</title>
<style>
  :root {{
    --bg: {bg};
    --card: {card};
    --primary: {primary};
    --accent: {accent};
    --text: {text};
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-user-select: none; user-select: none; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  body {{ background-color: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 20px 14px; }}
  .container {{ max-width: 440px; width: 100%; display: flex; flex-direction: column; gap: 14px; }}
  .badge {{ align-self: center; background: rgba(255,255,255,0.08); border: 1px solid var(--accent); color: var(--accent); font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 999px; text-transform: uppercase; letter-spacing: 0.8px; }}
  .header {{ text-align: center; }}
  .avatar-box {{ font-size: 44px; margin-bottom: 4px; }}
  .header h1 {{ font-size: 24px; font-weight: 900; letter-spacing: -0.5px; color: #fff; }}
  .header p {{ color: var(--accent); font-size: 13.5px; margin-top: 4px; font-weight: 600; opacity: 0.9; }}
  .card {{ background: var(--card); border: 1px solid rgba(255,255,255,0.12); border-radius: 16px; padding: 18px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }}
  .proposals-title {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: var(--accent); margin-bottom: 10px; font-weight: 700; }}
  .proposals-list {{ display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }}
  .prop-item {{ background: rgba(0,0,0,0.25); padding: 10px 12px; border-radius: 10px; font-size: 13px; border-left: 3px solid var(--primary); }}
  .btn-action {{ width: 100%; background: linear-gradient(135deg, var(--primary), var(--accent)); color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.5); border: none; padding: 14px; border-radius: 12px; font-weight: 800; font-size: 14.5px; cursor: pointer; transition: transform 0.1s; display: flex; align-items: center; justify-content: center; gap: 8px; }}
  .btn-action:active {{ transform: scale(0.97); }}
  .toast-box {{ display: none; margin-top: 14px; background: rgba(0,0,0,0.4); border: 1px solid var(--accent); color: var(--accent); padding: 14px; border-radius: 12px; text-align: center; font-weight: 700; }}
  .footer {{ text-align: center; color: rgba(255,255,255,0.4); font-size: 11px; margin-top: 6px; }}
</style>
</head>
<body>
<div class="container">
  <div class="badge">{badge}</div>
  <div class="header">
    <div class="avatar-box">{avatar}</div>
    <h1>{title}</h1>
    <p>{slogan}</p>
  </div>
  <div class="card">
    <div class="proposals-title">⭐ Principais Compromissos:</div>
    <div class="proposals-list">
      {proposals_html}
    </div>
    <button class="btn-action" onclick="execAction()">
      <span>📢</span> {btn_text}
    </button>
    <div class="toast-box" id="toastMsg">
      {toast_title}<br>
      <span style="font-size:12px; font-weight:400; color:#fff; opacity:0.9;">{toast_sub}</span>
    </div>
  </div>
  <div class="footer">Rede Wi-Fi Oficial de Campanha • PromoBeacon C3 Offline</div>
</div>
<script>
function execAction() {{
  document.getElementById('toastMsg').style.display = 'block';
}}
</script>
</body>
</html>"""

generated = []

for c in CANDIDATES:
    props_html = "\n      ".join([f'<div class="prop-item">{p}</div>' for p in c["points"]])
    html_content = HTML_TEMPLATE.format(
        title=c["title"],
        badge=c["badge"],
        avatar=c["avatar"],
        slogan=c["slogan"],
        bg=c["theme"]["bg"],
        card=c["theme"]["card"],
        primary=c["theme"]["primary"],
        accent=c["theme"]["accent"],
        text=c["theme"]["text"],
        proposals_html=props_html,
        btn_text=c["btn_text"],
        toast_title=c["toast_title"],
        toast_sub=c["toast_sub"]
    )
    
    file_path = os.path.join(PORTALS_DIR, f"{c['id']}.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    generated.append({
        "id": c["id"],
        "name": c["name"],
        "file": f"data/political_portals/{c['id']}.html",
        "size_bytes": len(html_content.encode("utf-8"))
    })

manifest_path = os.path.join(PORTALS_DIR, "manifest.json")
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(generated, f, indent=2, ensure_ascii=False)

print(f"✅ 20 PORTAIS POLÍTICOS GERADOS COM SUCESSO EM: {PORTALS_DIR}")
for g in generated:
    print(f" - {g['name']}: {g['file']} ({g['size_bytes']} bytes)")
