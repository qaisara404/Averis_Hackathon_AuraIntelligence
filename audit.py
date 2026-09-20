# =================================================================
# AUTOMATED BATCH AUDIT SCANNER (ZERO MISSING IMPORTS)
# AuraIntelligence - Averis Hackathon 2026
# =================================================================

import os
import json
import glob
import re

INBOX_DIR = 'inbox'
ATTACHMENTS_DIR = 'attachments'
OUTPUT_GT = 'ground_truth.json'

def read_text_safe(file_path):
    if not file_path or not os.path.exists(file_path):
        return ""
    ext = os.path.splitext(file_path)[1].lower()
    
    # 1. Plain Text & CSV
    if ext in ['.txt', '.csv']:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""
            
    # 2. Microsoft Excel (.xlsx / .xls)
    elif ext in ['.xlsx', '.xls']:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            lines = []
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    row_vals = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                    if row_vals:
                        lines.append(" : ".join(row_vals))
            return "\n".join(lines)
        except Exception:
            return ""
            
    # 3. Microsoft Word (.docx)
    elif ext == '.docx':
        try:
            from docx import Document
            doc = Document(file_path)
            lines = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_vals = [c.text.strip() for c in row.cells if c.text.strip()]
                    if row_vals:
                        lines.append(" | ".join(row_vals))
            return "\n".join(lines)
        except Exception:
            return ""
            
    # 4. PDF (.pdf) - Ekstrak selamat tanpa memerlukan pdfminer
    elif ext == '.pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages)
            if text.strip():
                return text
        except Exception:
            pass
            
        # Pengekstrak sandaran bait binari (tiada library luar diperlukan)
        try:
            with open(file_path, 'rb') as f:
                raw = f.read()
            matches = re.findall(rb'\(([^\(\)\\\r\n]{3,100})\)', raw)
            decoded = [m.decode('latin1', errors='ignore').strip() for m in matches if len(m.strip()) > 3]
            return " ".join(decoded)
        except Exception:
            return ""
            
    return ""

def parse_document_fields(text):
    if not text or not text.strip():
        return {}
    
    raw_dict = {}  # Dibetulkan daripada 'raw dict'
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = re.split(r'[:,\t|]', line, maxsplit=1)
        if len(parts) == 2:
            k_clean = re.sub(r'[^a-zA-Z0-9]', '', parts[0]).lower()
            if k_clean and parts[1].strip():
                raw_dict[k_clean] = parts[1].strip().strip('"\'')
    
    patterns = {
        "pol": [r"portofloading", r"pol", r"loadingport", r"loadport"],
        "pod": [r"portofdischarge", r"pod", r"dischargeport", r"destinationport", r"destination"],
        "consignee": [r"consigneenonnegotiable", r"consignee", r"buyer", r"soldto", r"importer"],
        "container": [r"noofcontainersorpackages", r"noofcontainers", r"containercount", r"containers", r"containerunits"],
        "weight": [r"grossweightkgs", r"grossweightkg", r"grossweight", r"totalgrossweight", r"gw"]
    }
    
    mapped = {}
    for standard_name, regex_keys in patterns.items():
        found = None
        for rk in regex_keys:
            for k in raw_dict:
                if re.fullmatch(rk, k) or k == rk:
                    found = raw_dict[k]
                    break
            if found:
                break
        if found:
            found = re.sub(r'^[^\w\s]+', '', found).strip(' "\'')
            mapped[standard_name] = found
            
    return mapped

def scan_all_emails():
    print("🚀 Sedang mengimbas kesemua fail emel dan dokumen Averis secara automatik...")
    email_files = sorted(glob.glob(os.path.join(INBOX_DIR, 'email_*.json')))
    print(f"📦 Dijumpai {len(email_files)} fail emel.")
    
    gt_results = {}
    counts = {"OK": 0, "MISMATCH": 0, "NEEDS_REVIEW": 0}

    for path in email_files:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            raw_id = data.get('email_id', os.path.splitext(os.path.basename(path))[0])
            email_id = raw_id.strip()
            subject = data.get('subject', '')
            body = data.get('body', '')
            attachments = data.get('attachments', [])
            
            full_meta = f"{subject} {body}".upper()
            if any(k in full_meta for k in ['SPAM', 'PROMO', 'OFFER', 'DISCOUNT']):
                category = 'SPAM'
            elif any(k in full_meta for k in ['INVOICE', 'PAYMENT', 'BILLING', 'CHARGE']):
                category = 'INVOICE_QUERY'
            elif any(k in full_meta for k in ['REQUEST SI', 'NEW SI', 'TEMPLATE']):
                category = 'SI_REQUEST'
            elif any(k in full_meta for k in ['GENERAL', 'INQUIRY']):
                category = 'GENERAL'
            else:
                category = 'BL_COMPARISON'

            # 1. Kategori bukan perbandingan dokumen
            if category != 'BL_COMPARISON':
                status = 'NEEDS_REVIEW' if category == 'SPAM' else 'OK'
                gt_results[email_id] = {
                    "category": category,
                    "status": status,
                    "has_defect": False,
                    "defect_fields": [],
                    "review_reason": "Spam filtered" if category == 'SPAM' else None
                }
                counts[status] += 1
                continue

            # 2. Cari fail SI dan BL sebenar
            si_file = None
            bl_file = None
            for att in attachments:
                base = os.path.basename(att)
                if '_SI.' in base or 'SI_' in base or '_SI_' in base:
                    si_file = os.path.join(ATTACHMENTS_DIR, base)
                elif '_BL.' in base or 'BL_' in base or '_BL_' in base:
                    bl_file = os.path.join(ATTACHMENTS_DIR, base)

            if not si_file:
                m = glob.glob(os.path.join(ATTACHMENTS_DIR, f"*{email_id}*SI*.*"))
                if m: si_file = m[0]
            if not bl_file:
                m = glob.glob(os.path.join(ATTACHMENTS_DIR, f"*{email_id}*BL*.*"))
                if m: bl_file = m[0]

            # 3. Semak kewujudan fail fizikal di folder
            if not si_file or not bl_file or not os.path.exists(si_file) or not os.path.exists(bl_file):
                gt_results[email_id] = {
                    "category": category,
                    "status": "NEEDS_REVIEW",
                    "has_defect": False,
                    "defect_fields": [],
                    "review_reason": "missing_attachment"
                }
                counts["NEEDS_REVIEW"] += 1
                continue

            # 4. Baca teks dokumen sebenar
            si_text = read_text_safe(si_file)
            bl_text = read_text_safe(bl_file)

            if not si_text.strip() or not bl_text.strip():
                gt_results[email_id] = {
                    "category": category,
                    "status": "NEEDS_REVIEW",
                    "has_defect": False,
                    "defect_fields": [],
                    "review_reason": "unreadable"
                }
                counts["NEEDS_REVIEW"] += 1
                continue

            # 5. Ekstrak dan bandingkan medan sebenar
            si_data = parse_document_fields(si_text)
            bl_data = parse_document_fields(bl_text)
            
            defects = []
            for k in ["pol", "pod", "consignee", "container", "weight"]:
                v_si = si_data.get(k, "")
                v_bl = bl_data.get(k, "")
                if v_si and v_bl:
                    clean_si = re.sub(r'[^A-Z0-9]', '', v_si.upper())
                    clean_bl = re.sub(r'[^A-Z0-9]', '', v_bl.upper())
                    if clean_si != clean_bl and clean_si not in clean_bl and clean_bl not in clean_si:
                        defects.append(k)

            status = "MISMATCH" if defects else "OK"

            gt_results[email_id] = {
                "category": category,
                "status": status,
                "has_defect": len(defects) > 0,
                "defect_fields": defects,
                "review_reason": None
            }
            counts[status] += 1

        except Exception:
            continue

    with open(OUTPUT_GT, 'w', encoding='utf-8') as f:
        json.dump(gt_results, f, indent=2)

    print("\n✅ SELESAI! Hasil Imbasan Automatik Sebenar:")
    print(f"   🟢 Verified (OK): {counts['OK']}")
    print(f"   🔴 Mismatches:    {counts['MISMATCH']}")
    print(f"   🟣 Needs Review:  {counts['NEEDS_REVIEW']}")
    print(f"   📁 Disimpan ke:   {OUTPUT_GT}\n")

if __name__ == '__main__':
    scan_all_emails()