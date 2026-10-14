"""
PromoBeacon SWE vs LQA Deep Audit & Debate Simulator (Powered by JEV)
Analyzes codebase, web suite, mobile app parity, and localization.
"""

import os
import re
import json
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def run_swe_lqa_debate():
    index_path = os.path.join(os.path.dirname(__file__), "..", "web_installer", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    findings_swe = []
    findings_lqa = []

    # -------------------------------------------------------------
    # 1. SWE AUDIT: Code Injection & JS Syntax Breaking in OnClick
    # -------------------------------------------------------------
    has_esc_js = "function escJs(" in html and "safeTitle" in html
    if not has_esc_js:
        findings_swe.append({
            "id": "SWE-BUG-001",
            "severity": "HIGH",
            "title": "Unescaped String Literal Injection in OnClick Handlers",
            "evidence": "Raw unescaped variable injected into inline onclick single-quoted string.",
            "impact": "If a user inputs an apostrophe or single quote (e.g., 'O\\'Connor for Congress' or 'Chef\\'s Special'), the generated onclick code throws a JavaScript Uncaught SyntaxError and completely breaks button execution in the captive portal.",
            "recommendation": "Sanitize and escape single quotes using escJs() helper."
        })

    # -------------------------------------------------------------
    # 2. SWE AUDIT: Image Upload Lifecycle & Template Memory Leak
    # -------------------------------------------------------------
    # Check if loadTemplate resets currentUploadedImageBase64
    load_tpl_match = re.search(r"function\s+loadTemplate\([^)]*\)\s*\{([^}]+)\}", html)
    load_tpl_body = load_tpl_match.group(1) if load_tpl_match else ""
    resets_in_tpl = "clearUploadedImage" in load_tpl_body or "currentUploadedImageBase64" in load_tpl_body
    has_clear_btn = "cfg-img-clear" in html
    if not resets_in_tpl or not has_clear_btn:
        findings_swe.append({
            "id": "SWE-BUG-002",
            "severity": "MEDIUM",
            "title": "Sticky Image State Across Template Switching & No Clear Button",
            "evidence": "currentUploadedImageBase64 is never cleared in loadTemplate(key) and no UI button exists to remove an uploaded banner photo.",
            "impact": "If a user uploads a restaurant food photo, then switches to the Church or Campaign Flyer template, the food photo remains permanently attached to the new template. The user has no way to remove the photo without reloading the page and losing all entered text.",
            "recommendation": "Add a '🗑️ Remove Photo' button in the builder UI and clear image state when switching templates."
        })

    # -------------------------------------------------------------
    # 3. SWE AUDIT: Linter Parity with Mobile App (UploadPortalUseCase.kt)
    # -------------------------------------------------------------
    catches_import = "@import" in html
    checks_link = "<link\\b" in html or "<link" in html
    has_parity = catches_import and checks_link
    if not has_parity:
        findings_swe.append({
            "id": "SWE-BUG-003",
            "severity": "MEDIUM",
            "title": "Web Linter Parity Mismatch: Flags Harmless External <a> Links, Misses CSS @import",
            "evidence": "Web Linter uses generic regex without checking CSS @import or differentiating <link rel='stylesheet'>.",
            "impact": "Users trying to include contact links (WhatsApp, Instagram) get a false-positive 'OFFLINE FAIL' warning, while portals with CSS @import url('https://fonts...') pass undetected and break silently.",
            "recommendation": "Align Web Linter regex with Kotlin UploadPortalUseCase: detect <link rel='stylesheet' href='...'>, @import url('...'), and src='...', while allowing <a href='...'> social links."
        })

    # -------------------------------------------------------------
    # 4. SWE AUDIT: Auto-Fix Viewport Injection Without <head>
    # -------------------------------------------------------------
    has_robust_autofix = "else if (/<html" in html or "else if (/<html[^>]*>/i.test(code))" in html or "'<meta name=\"viewport\"" in html
    if not has_robust_autofix:
        findings_swe.append({
            "id": "SWE-BUG-004",
            "severity": "LOW",
            "title": "Auto-Fix Silently Fails on HTML Snippets Without <head> Tag",
            "evidence": "autoFixHtml() only handles documents with explicit <head> tags.",
            "impact": "If the user pastes a raw HTML snippet without an explicit <head> tag (e.g., starting directly with <body> or <div>), the viewport meta tag is silently dropped and never inserted.",
            "recommendation": "If <head> is missing, prepend the meta tag or wrap the document with standard head/body tags."
        })

    # -------------------------------------------------------------
    # 5. LQA AUDIT: Brazilian Electoral Jargon in English UI
    # -------------------------------------------------------------
    if "e-Santinho" in html:
        findings_lqa.append({
            "id": "LQA-ISSUE-001",
            "severity": "MEDIUM",
            "title": "Brazilian Portuguese Terminology in English UI: 'e-Santinho'",
            "evidence": "Chip label contains Brazilian jargon: 'e-Santinho'",
            "impact": "English-speaking users in the US, UK, Australia, or global markets do not know what 'santinho' means. In Brazil it refers to small printed candidate cards, but in English it is called a 'Digital Campaign Flyer' or 'Candidate Handout'.",
            "recommendation": "Rename chip to '🗳️ Political Campaign Flyer' or '🗳️ Candidate Flyer (Digital Handout)'."
        })

    # -------------------------------------------------------------
    # 6. LQA AUDIT: Brazilian Dot Ballot Number Formatting
    # -------------------------------------------------------------
    if "#15.123" in html:
        findings_lqa.append({
            "id": "LQA-ISSUE-002",
            "severity": "LOW",
            "title": "Brazilian Electoral Number Dot Notation (#15.123) in English Template",
            "evidence": "Candidate title contains Brazilian electoral dot notation: '#15.123'",
            "impact": "The dot separator in 5-digit candidate numbers is specific to Brazil's Superior Electoral Court (TSE). In Anglo/International campaigns, numbers are written as '#15123' or candidates run by district/office (e.g., 'Marcus Silva for City Council • District 4').",
            "recommendation": "Update to international format: 'Dr. Marcus Silva • District 4 (#15123)' or 'Marcus Vance for Senate'."
        })

    # -------------------------------------------------------------
    # 7. LQA AUDIT: Placeholder Token Leak ('DONATION_KEY')
    # -------------------------------------------------------------
    if "DONATION_KEY" in html:
        findings_lqa.append({
            "id": "LQA-ISSUE-003",
            "severity": "MEDIUM",
            "title": "Unlocalized Placeholder Token 'DONATION_KEY' in Church Template",
            "evidence": "secondaryBtnHtml = navigator.clipboard.writeText('DONATION_KEY')",
            "impact": "Clicking '🕊️ Copy Donation Details' copies the literal developer placeholder string 'DONATION_KEY' to the user's clipboard! In English church portals, this should provide a real payment handle or address (e.g., 'giving@stjosephcommunity.org (Zelle / PayPal)').",
            "recommendation": "Replace 'DONATION_KEY' with realistic English community giving details: 'giving@stjoseph.org (Zelle / PayPal)'."
        })

    # -------------------------------------------------------------
    # 8. LQA AUDIT: Candidate Detection Heuristic Relies on Brazilian Surname
    # -------------------------------------------------------------
    has_broad_political = "ballot" in html and "council" in html and "senator" in html
    if not has_broad_political:
        findings_lqa.append({
            "id": "LQA-ISSUE-004",
            "severity": "LOW",
            "title": "Contextual Badge Regex Contains Hardcoded Portuguese Identifiers",
            "evidence": "Regex lacks broad international political keywords.",
            "impact": "The regex lacks broad international keywords. If an international user enters 'Senator Alex Turner', none of the keywords match unless 'campaign' or 'vote' is explicitly written.",
            "recommendation": "Broaden international political keywords: /campaign|candidate|election|vote|ballot|senator|mayor|council|office|party/i."
        })

    # Output Summary
    print("=" * 70)
    print("PROMOBEACON DEEP SWE vs LQA AUDIT — JEV EVALUATION")
    print("=" * 70)
    print(f"\n[SWE FINDINGS: {len(findings_swe)} Items]")
    for item in findings_swe:
        print(f"\n* [{item['severity']}] {item['id']}: {item['title']}")
        print(f"  Evidence: {item['evidence']}")
        print(f"  Impact:   {item['impact']}")
        print(f"  Fix:      {item['recommendation']}")

    print(f"\n[LQA FINDINGS: {len(findings_lqa)} Items]")
    for item in findings_lqa:
        print(f"\n* [{item['severity']}] {item['id']}: {item['title']}")
        print(f"  Evidence: {item['evidence']}")
        print(f"  Impact:   {item['impact']}")
        print(f"  Fix:      {item['recommendation']}")

    report = {
        "swe_findings": findings_swe,
        "lqa_findings": findings_lqa,
        "total_bugs": len(findings_swe) + len(findings_lqa)
    }

    report_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "swe_lqa_audit_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nAudit complete. JSON saved to {report_path}")

if __name__ == "__main__":
    run_swe_lqa_debate()
