# JAAA - Build Roadmap (v1.0)

## Phase 1: Core Utilities & Data Processing
1. [ ] **Resume Parser**: Load PDF resume into structured JSON (LandingAI/PyPDF2).
2. [ ] **Database Setup**: PostgreSQL schema for `applications`, `accounts`, `resumes`, and `logs`.
3. [ ] **Email Handler**: Real-time polling for magic links and OTP codes (Gmail API/IMAP).

## Phase 2: Browser & Automation Infrastructure
1. [ ] **Browserbase Integration**: Connect Playwright to managed cloud browsers.
2. [ ] **Stagehand (AI Vision) Layer**: Implement `act()`, `extract()`, and `observe()` for form analysis.
3. [ ] **CAPTCHA Layer**: Integrate CapSolver/2Captcha for automatic token injection.

## Phase 3: Orchestration & Application Flow
1. [ ] **Orchestrator Agent**: Implement Claude-based task planning (Job analysis -> Account -> Form filling).
2. [ ] **Form Interaction**: Build field-to-profile mapping logic for complex ATS platforms (Workday/Greenhouse).
3. [ ] **Proof of Work**: Capture submission screenshots and log results.

## Phase 4: Scaling & Reliability
1. [ ] **ATS Specializations**: Add specific support for Workday custom components.
2. [ ] **Async Queue**: Implement Celery + Redis for parallel job processing.
3. [ ] **Reporting Dashboard**: Simple UI/API to monitor application status and artifacts.
