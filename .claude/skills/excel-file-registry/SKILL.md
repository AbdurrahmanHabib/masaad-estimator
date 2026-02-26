---
name: excel-file-registry
description: Registry of all ANC Proposal Engine test Excel files with expected results. Use when testing, debugging Excel parsing, or verifying PDF output. Reference this to know which file tests what and what "pass" looks like.
---

# ANC Excel File Registry

## Production Test Files

### Indiana Audit
- **Filename:** `Cost-Analysis---Indiana-Fever-audit (3).xlsx`
- **VPS path:** `/root/rag2/Cost-Analysis---Indiana-Fever-audit (3).xlsx`
- **Tests:** Fallback parser (left-shifted columns, no section headers)
- **Expected:** 1 table, 10 items, 3 alternates
- **Total:** $507,262.53
- **Mode:** Any (Budget/Proposal/LOI)

### Indiana LOI (Gold Standard)
- **Filename:** `ANC_Indiana Fever LED Displays LOI_1.26.2026.xlsx`
- **VPS path:** `/root/rag2/ANC_Indiana Fever LED Displays LOI_1.26.2026.xlsx`
- **Tests:** Standard parser, LOI mode, full legal header, payment terms, signatures
- **Expected:** 8 tables
- **Total:** $2,237,067.64
- **Mode:** LOI

### Scotia (CAD)
- **Filename:** `Copy of Cost Analysis - SBA PH4 - 2026-01-28.xlsx`
- **VPS path:** `/root/rag2/Copy of Cost Analysis - SBA PH4 - 2026-01-28 (2).xlsx`
- **Tests:** CAD currency, 13% tax, multiple sections, alternates
- **Expected:** 7 tables, 5 alternates, currency = CAD
- **Mode:** Budget

### Moody Center (Phase 2 — DO NOT TEST YET)
- **Filename:** `Copy_of_anc_x_LG_x_Moody_Center_02-03-26.xlsx`
- **Tests:** One-off format, no Margin Analysis sheet
- **Status:** Requires custom parser, deferred to Phase 2

## Testing Endpoints
- **Local dev:** `http://localhost:3003/api/proposals/import-excel` (POST, multipart/form-data, field: `file`)
- **Production:** `https://basheer-natalia.prd42b.easypanel.host/api/proposals/import-excel`

## Pass/Fail Criteria
- PASS = pricingDocument produced with correct table count + correct total + PDF generates
- FAIL = no pricingDocument, wrong total, missing alternates, or PDF generation error
