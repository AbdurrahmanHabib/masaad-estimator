# Madinat Al Saada ERP & Estimator

## Project Status: Vibrant Modern ERP Refactor (Phase 5)

This repository contains the advanced estimation and ERP suite for **Madinat Al Saada Aluminium & Glass Works**.

### ✅ Completed in this Refactor:
1.  **Vibrant ERP UI Branding:** 
    *   Migrated from generic dark mode to a professional, vibrant ERP design matching the company's HRMS portal.
    *   **Theme:** Light Slate background (`#f8fafc`), Dark Navy sidebar (`#1e293b`), and vibrant metric cards.
    *   **Components:** Collapsible sidebar, white header with search, and high-density tables (`text-xs`).
2.  **Unified Group Financial Engine:**
    *   **Admin Expenses:** Logic to sum `MADINAT`, `AL JAZEERA`, and `MADINAT AL JAZEERA` columns from `adminexpenses.csv`.
    *   **Labor Engine:** Strictly filters payroll for `Site/Job Location == "FACTORY"`.
    *   **True Shop Rate:** Implemented calculation: `(Total_Group_Overhead + Direct_Payroll_Cost) / Active_Factory_Hours`.
3.  **Advanced Workspace ([id].tsx):**
    *   3-Pane Layout: Layer Control (20%) | Active Workbench (50%) | Financial Pulse (30%).
    *   **Live Metrics:** True Burdened Rate and Project Value update instantly.
    *   **Workbench Toggles:** Seamless switching between BOQ Grid, 2D Nesting, and Structural Audit.
    *   **Sticky Footer:** Real-time feedback on Sell Price, Net Mass (KG), and Profit Margin.
4.  **Backend Integrity:**
    *   Fixed missing dependencies (`shapely`, `pdfplumber`).
    *   Resolved React hydration mismatches across all pages.
    *   Registered new ingestion and settings API routes.

### 🚀 To Be Done (Future PC Work):
1.  **Database Integration:** 
    *   Replace persistent state in `settings_routes.py` with PostgreSQL (SQLAlchemy/asyncpg).
    *   Implement user authentication and multi-tenant isolation.
2.  **Advanced Nesting Algorithms:**
    *   Connect the 2D Canvas to real `nesting_engine_2d.py` output.
    *   Add 50mm cassette fold logic to the backend quantification process.
3.  **Report Engine:**
    *   Implement `report_engine.py` to generate technical submittals and cutting lists.
4.  **Deployment:**
    *   Configure Railway or OCI for production traffic.

### 🛠 Tech Stack:
*   **Frontend:** Next.js (TypeScript), Tailwind CSS, Lucide Icons, Zustand.
*   **Backend:** FastAPI (Python), Pandas (Financials), Ezdxf (CAD), Shapely (Geometry).

---
*Built with precision for Madinat Al Saada.*
