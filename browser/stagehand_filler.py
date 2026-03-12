"""
Stagehand Form Filler -- Generic job application automation.
Uses Stagehand Python SDK v3 with act()/extract()/observe() primitives.
"""
import os
import sys
import asyncio
import threading
from datetime import datetime
from stagehand import AsyncStagehand
from profile.profile_manager import ProfileManager
from storage.logger import ApplicationLogger

sys.stdout.reconfigure(write_through=True)

MODEL_NAME = "google/gemini-2.5-flash"


def log(msg: str):
    print(f"[JAAA] {msg}", flush=True)


class StagehandFormFiller:
    def __init__(self, profile_manager: ProfileManager, logger: ApplicationLogger):
        self.pm = profile_manager
        self.profile = self.pm.profile_data
        self.logger = logger
        self.email = os.environ.get("ACCOUNT_EMAIL", self.profile.personal_info["email"])
        self.password = os.environ.get("ACCOUNT_PASSWORD", "")

    # === Client / session =====================================================

    def _build_client(self) -> AsyncStagehand:
        return AsyncStagehand(
            server="local",
            browserbase_api_key="local",
            browserbase_project_id="local",
            local_openai_api_key=(
                os.environ.get("MODEL_API_KEY")
                or os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
            ),
            local_chrome_path=os.environ.get("CHROME_PATH"),
            local_headless=False,
            local_ready_timeout_s=60.0,
        )

    async def _start_session(self, client: AsyncStagehand) -> str:
        session = await client.sessions.start(
            model_name=MODEL_NAME,
            self_heal=True,
            dom_settle_timeout_ms=3000,
            browser={"type": "local", "launchOptions": {"headless": False}},
        )
        return session.data.session_id

    # === Primitives ===========================================================

    async def _act(self, client, sid, instruction, retries=3) -> bool:
        for attempt in range(retries):
            try:
                await client.sessions.act(id=sid, input=instruction)
                return True
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    log(f"  act FAILED: {instruction[:80]} -- {e}")
                    return False
        return False

    async def _extract(self, client, sid, instruction, schema) -> dict:
        try:
            result = await client.sessions.extract(
                id=sid, instruction=instruction, schema=schema
            )
            return result.data.result or {}
        except Exception as e:
            log(f"  extract FAILED: {str(e)[:80]}")
            return {}

    async def _observe(self, client, sid, instruction) -> list:
        try:
            result = await client.sessions.observe(id=sid, instruction=instruction)
            return result.data.actions or []
        except Exception:
            return []

    # === Smart helpers ========================================================

    async def _page_context(self, client, sid) -> dict:
        """
        Ask the LLM to describe the current page state.
        Returns dict with 'page_type' and 'description'.
        """
        return await self._extract(client, sid,
            "Analyze this page. What type of page is it? Options: "
            "'job_posting' (job description with apply button), "
            "'sign_in' (login/sign-in form), "
            "'create_account' (registration form), "
            "'application_form' (job application with form fields to fill), "
            "'otp_verification' (asking for verification code or check email), "
            "'review_submit' (review/summary with submit button), "
            "'dashboard' (account dashboard or profile page), "
            "'other'. Also briefly describe what you see.",
            {"type": "object", "properties": {
                "page_type": {"type": "string"},
                "description": {"type": "string"}
            }, "required": ["page_type", "description"]}
        )

    async def _fill_field(self, client, sid, field_name, value) -> bool:
        """Fill a single text field. Tries the instruction directly via act()."""
        if not value:
            return False
        return await self._act(client, sid,
            f"click on the {field_name} input field, select all existing text, "
            f"then type the exact value {value} with no extra characters")

    # === OTP ==================================================================

    async def _prompt_otp(self, timeout_s: int = 180) -> str | None:
        log("=" * 50)
        log("  CHECK YOUR EMAIL FOR VERIFICATION")
        log(f"  Email: {self.email}")
        log("  Enter OTP code, or press Enter if you clicked a magic link.")
        log("=" * 50)
        result = [None]
        event = threading.Event()

        def _read():
            try:
                val = input("  Code (or Enter): ").strip()
                result[0] = val if val else None
            except Exception:
                pass
            finally:
                event.set()

        threading.Thread(target=_read, daemon=True).start()
        event.wait(timeout=timeout_s)
        return result[0]

    # === Auth =================================================================

    async def _do_sign_in(self, client, sid) -> bool:
        log("Signing in...")
        await self._fill_field(client, sid, "Email Address or Username", self.email)
        await asyncio.sleep(1)
        await self._fill_field(client, sid, "Password", self.password)
        await asyncio.sleep(1)
        await self._act(client, sid, "click the Sign In or Log In button")
        await asyncio.sleep(5)
        # Check result
        ctx = await self._page_context(client, sid)
        page_type = ctx.get("page_type", "")
        if page_type == "sign_in":
            log("  Sign-in seems to have failed (still on sign-in page)")
            return False
        log(f"  After sign-in: {page_type} -- {ctx.get('description', '')[:80]}")
        return True

    async def _do_create_account(self, client, sid) -> bool:
        log("Creating account...")
        # If there's a "Create Account" / "Register" link, click it first
        await self._act(client, sid,
            "click the Create Account or Register or Sign Up link or button")
        await asyncio.sleep(3)

        await self._fill_field(client, sid, "Email Address", self.email)
        await asyncio.sleep(1)
        await self._fill_field(client, sid, "Password", self.password)
        await asyncio.sleep(1)
        # Confirm password if present
        await self._act(client, sid,
            "if there is a Confirm Password or Verify Password field, "
            f"click it and type: {self.password}")
        await asyncio.sleep(1)
        # Accept terms if present
        await self._act(client, sid,
            "if there is a terms and conditions checkbox, check it")
        await asyncio.sleep(0.5)
        # Submit
        await self._act(client, sid,
            "click the Create Account or Register or Sign Up submit button")
        await asyncio.sleep(5)
        log(f"  Account creation submitted for {self.email}")
        return True

    # === Sub-form filling (experience, education) ============================

    def _format_date_for_workday(self, yyyy_mm: str) -> str:
        """Convert 'YYYY-MM' to 'MM/YYYY' (e.g. '2025-09' -> '09/2025')."""
        if not yyyy_mm:
            return ""
        parts = yyyy_mm.strip().split("-")
        if len(parts) == 2:
            return f"{parts[1]}/{parts[0]}"
        return yyyy_mm

    async def _fill_work_experience(self, client, sid):
        """Fill work experience sequentially: one field at a time, then save. Loops over ALL experiences."""
        exp_list = self.profile.experience
        if not exp_list:
            log("  No work experience in profile -- skipping")
            return
        for i, exp in enumerate(exp_list):
            if i > 0:
                await self._act(client, sid, "click the Add Work Experience button")
                await asyncio.sleep(3)
            desc_text = ". ".join(exp.description[:2]) if exp.description else ""
            start_val = self._format_date_for_workday(exp.start_date) if exp.start_date else ""
            end_val = "Present" if (exp.end_date and exp.end_date.lower() == "present") else (
                self._format_date_for_workday(exp.end_date) if exp.end_date else ""
            )
            log(f"  Filling work exp ({i+1}/{len(exp_list)}): {exp.role} @ {exp.company}")

            await self._fill_field(client, sid, "Job Title", exp.role)
            await asyncio.sleep(1)
            await self._fill_field(client, sid, "Company", exp.company)
            await asyncio.sleep(1)
            await self._fill_field(client, sid, "Location", exp.location)
            await asyncio.sleep(1)
            if start_val:
                await self._act(client, sid, f"Fill the start date or From field with {start_val}")
            await asyncio.sleep(1)
            await self._act(client, sid, f"Fill the end date or To field with {end_val}. If there is 'I currently work here', check it.")
            await asyncio.sleep(1)
            if desc_text:
                await self._act(client, sid, f"Fill the description or Role Description field with: {desc_text[:350]}")
                await asyncio.sleep(1)
            await self._act(client, sid, "Click the Save or Done or checkmark button to save and close this work experience form")
            await asyncio.sleep(4)

    def _normalize_gpa(self, gpa_str: str) -> str:
        """Strip '/4.00' suffix so '3.50/4.00' becomes '3.5'."""
        if not gpa_str:
            return ""
        s = gpa_str.strip()
        if s.endswith("/4.00"):
            s = s[:-5].strip()
        return s

    async def _fill_education(self, client, sid):
        """Fill education sequentially: one field at a time, then save. Loops over ALL education entries."""
        edu_list = self.profile.education
        if not edu_list:
            log("  No education in profile -- skipping")
            return
        for i, edu in enumerate(edu_list):
            if i > 0:
                await self._act(client, sid, "click the Add Education button")
                await asyncio.sleep(3)
            field_of_study = edu.degree.split(" in ")[-1] if " in " in edu.degree else edu.degree
            gpa = self._normalize_gpa(getattr(edu, "gpa", "") or "")
            grad_date = self._format_date_for_workday(edu.graduation_date) if edu.graduation_date else ""
            log(f"  Filling education ({i+1}/{len(edu_list)}): {edu.degree} @ {edu.institution}")

            # School/Institution is typeahead: click, type, wait, Enter to select
            await self._act(client, sid, f"click the School or Institution or College field")
            await asyncio.sleep(0.5)
            await self._act(client, sid, f"type {edu.institution} into the School or Institution field")
            await asyncio.sleep(2)
            await self._act(client, sid, "press Enter to select the first suggestion")
            await asyncio.sleep(1)
            await self._act(client, sid, f"Fill the Degree field with {edu.degree}")
            await asyncio.sleep(1)
            await self._act(client, sid, f"Fill the Field of Study or Major field with {field_of_study}")
            await asyncio.sleep(1)
            if grad_date:
                await self._act(client, sid, f"Fill the graduation date or End Date field with {grad_date}")
            await asyncio.sleep(1)
            if gpa:
                await self._act(client, sid, f"Fill the GPA field with {gpa}")
                await asyncio.sleep(1)
            await self._act(client, sid, "Click the Save or Done or checkmark button to save and close this education form")
            await asyncio.sleep(4)

    async def _upload_resume(self, client, sid, resume_path: str):
        """Click upload area - file picker will open. User must select file manually."""
        if not os.path.exists(resume_path):
            log(f"  Resume not found: {resume_path}")
            return
        log(f"  Clicking resume upload area...")
        await self._act(client, sid, "Click the resume upload area or 'Select files' or 'Upload' button")
        await asyncio.sleep(2)
        log(f"  >>> FILE PICKER OPENED - Please select: {resume_path}")
        log(f"  >>> Waiting 45 seconds for you to select the file...")
        await asyncio.sleep(45)

    # === Form filling =========================================================

    async def _fill_application_step(self, client, sid):
        """
        Use the LLM to identify visible fields, then fill them from profile.
        Generic -- works on any job application site.
        """
        p = self.profile.personal_info
        loc = p.get("location", {})
        links = p.get("links", {})
        work_auth = p.get("work_authorization", {})
        resume_path = os.path.abspath(self.profile.resume_paths["base"])

        # Build a comprehensive applicant profile string
        applicant_info = (
            f"First Name: {p['first_name']}\n"
            f"Last Name: {p['last_name']}\n"
            f"Email: {p['email']}\n"
            f"Phone: {p['phone']}\n"
            f"Address: {loc.get('address', '2111 Richmond Hwy')}\n"
            f"City: {loc.get('city', 'Arlington')}\n"
            f"State/Province: {loc.get('state', 'VA')}\n"
            f"Country: {loc.get('country', 'USA')}\n"
            f"Zip/Postal Code: {loc.get('zip', '22202')}\n"
            f"LinkedIn: {links.get('linkedin', '')}\n"
            f"GitHub: {links.get('github', '')}\n"
            f"Authorized to work in US: {'Yes' if work_auth.get('authorized_to_work_in_us', True) else 'No'}\n"
            f"Requires visa sponsorship: {'Yes' if work_auth.get('requires_sponsorship', False) else 'No'}\n"
            f"For 'How did you hear about us' or source questions: always select 'Career Site' or the closest match\n"
            f"Professional Summary: {self.profile.professional_summary[:200]}"
        )

        # Step 1: Ask the LLM what fields are visible
        fields_data = await self._extract(client, sid,
            "Look at this job application page. List every visible interactive element: "
            "text inputs, dropdowns, file uploads, radio buttons, checkboxes, "
            "and also 'Add' buttons for sections like Work Experience, Education, "
            "Languages, Skills, Websites. For each, provide its label/name, "
            "the section it belongs to (e.g. 'Add (Work Experience)'), "
            "its type (text, dropdown, file, button, etc), "
            "and whether it is empty or already filled/added.",
            {"type": "object", "properties": {
                "fields": {"type": "array", "items": {
                    "type": "object", "properties": {
                        "label": {"type": "string"},
                        "type": {"type": "string"},
                        "is_empty": {"type": "boolean"}
                    }
                }}
            }, "required": ["fields"]}
        )

        all_fields = fields_data.get("fields", [])
        # Filter out nav buttons and site chrome -- not fields to fill
        skip_labels = {"next", "continue", "save", "save and continue", "submit",
                       "back", "previous", "cancel", "english", "sign in",
                       "main menu", "search for jobs", "work with us",
                       "back to job posting", "select files"}
        skip_prefixes = ["careers at", "errors found", "error"]
        fields = []
        for f in all_fields:
            lbl = f.get("label", "").strip().lower()
            if lbl in skip_labels:
                continue
            if any(lbl.startswith(p) for p in skip_prefixes):
                continue
            fields.append(f)
        # Sort: Add Work Experience, Add Education, Resume/Upload, other Add, rest
        def _field_priority(f):
            lbl = f.get("label", "").lower()
            if "add" in lbl and any(w in lbl for w in ["work experience", "experience"]):
                return 0
            if "add" in lbl and "education" in lbl:
                return 1
            if "upload" in lbl or "resume" in lbl or "cv" in lbl:
                return 2
            if lbl.startswith("add"):
                return 3
            return 4
        fields.sort(key=_field_priority)

        field_labels = [f.get("label", "") for f in fields]
        log(f"Visible fields: {field_labels}")

        if not fields:
            # Fallback: just tell the LLM to fill whatever it sees
            log("  No fields extracted -- using blanket fill instruction")
            await self._act(client, sid,
                f"Fill in all visible empty form fields on this page with the "
                f"applicant's information. Here is the applicant's data:\n"
                f"{applicant_info}\n"
                f"For dropdowns, select the closest matching option. "
                f"For file uploads, use: {resume_path}")
            return

        # Step 2: For each empty field, fill it
        for field in fields:
            label = field.get("label", "")
            ftype = field.get("type", "text")
            is_empty = field.get("is_empty", True)

            if not label or not is_empty:
                continue

            label_lower = label.lower()

            # File upload
            if ftype in ("file", "upload") or any(w in label_lower for w in
                    ["resume", "cv", "upload a file", "select file"]):
                await self._upload_resume(client, sid, resume_path)
                continue

            # Add Work Experience button
            if "add" in label_lower and any(w in label_lower for w in
                    ["work experience", "experience"]):
                log(f"  Adding work experience...")
                await self._act(client, sid, f"click the '{label}' button")
                await asyncio.sleep(3)
                await self._fill_work_experience(client, sid)
                continue

            # Add Education button
            if "add" in label_lower and "education" in label_lower:
                log(f"  Adding education...")
                await self._act(client, sid, f"click the '{label}' button")
                await asyncio.sleep(3)
                await self._fill_education(client, sid)
                continue

            # Add Languages
            if "add" in label_lower and "language" in label_lower:
                log(f"  Adding language...")
                try:
                    await self._act(client, sid, f"click the '{label}' button")
                    await asyncio.sleep(2)
                    await self._act(client, sid, "type English and press Enter")
                    await asyncio.sleep(2)
                except Exception as e:
                    log(f"  Add language failed: {e}")
                continue

            # Add Websites
            if "add" in label_lower and "website" in label_lower:
                log(f"  Adding website...")
                try:
                    await self._act(client, sid, f"click the '{label}' button")
                    await asyncio.sleep(2)
                    linkedin = links.get("linkedin", "")
                    if linkedin:
                        await self._fill_field(client, sid, "URL", linkedin)
                    await asyncio.sleep(2)
                except Exception as e:
                    log(f"  Add website failed: {e}")
                continue

            # Generic "Add" button we don't recognize -- skip
            if label_lower.strip() == "add":
                continue

            # Skills field - one skill at a time: type, Enter, wait, next
            if any(w in label_lower for w in ["skill", "add skills"]):
                log(f"  Adding skills (one at a time)...")
                skills = self.profile.skills
                all_skills = (skills.languages[:3] + skills.frameworks[:3] +
                              skills.tools[:2] + skills.domains[:2])
                for skill in all_skills[:8]:
                    try:
                        log(f"    Adding skill: {skill}")
                        await self._act(client, sid,
                            f"Click the skills input, type {skill}, press Enter")
                        await asyncio.sleep(2)
                    except Exception as e:
                        log(f"    Skill '{skill}' failed: {e}")
                continue

            # Detect dropdowns by label name -- the LLM often misclassifies
            # these as "text" fields, so we can't rely on ftype alone
            is_dropdown = (
                ftype in ("dropdown", "select")
                or self._dropdown_search_term(label_lower) != ""
            )

            if is_dropdown:
                search_term = self._dropdown_search_term(label_lower)
                log(f"  Dropdown: {label} -> typing '{search_term}' + Enter")
                await self._act(client, sid,
                    f"click the '{label}' field")
                await asyncio.sleep(0.5)
                if search_term:
                    await self._act(client, sid,
                        f"type {search_term} into the '{label}' field")
                    await asyncio.sleep(1.5)
                    await self._act(client, sid, "press Enter")
                    await asyncio.sleep(1)
                continue

            # Radio / checkbox
            if ftype in ("radio", "checkbox"):
                log(f"  Answering: {label}")
                await self._act(client, sid,
                    f"For the '{label}' question, select the appropriate answer "
                    f"based on this applicant data:\n{applicant_info}")
                await asyncio.sleep(1)
                continue

            # Skip fields that shouldn't be filled with text
            if any(w in label_lower for w in ["phone extension", "extension"]):
                continue

            # Text input -- match to profile data
            value = self._match_field_to_profile(label_lower, p, loc, links)
            if value:
                log(f"  Filling: {label} = {value[:30]}")
                await self._fill_field(client, sid, label, value)
                await asyncio.sleep(0.5)
            else:
                log(f"  Filling (AI): {label}")
                await self._act(client, sid,
                    f"Fill the '{label}' field using this info: "
                    f"Name: {p['first_name']} {p['last_name']}, "
                    f"Email: {p['email']}, Phone: 7039280214, "
                    f"Address: {loc.get('address','')}, {loc.get('city','')}, "
                    f"{loc.get('state','')}, {loc.get('zip','')}")
                await asyncio.sleep(0.5)

    def _dropdown_search_term(self, label_lower: str) -> str:
        """Return the text to type into a dropdown/typeahead to trigger suggestions.
        Returning non-empty also signals that this field IS a dropdown."""
        if any(w in label_lower for w in ["hear about", "source", "how did you", "find this"]):
            return "Website"
        if any(w in label_lower for w in ["phone device", "device type"]):
            return "Mobile"
        if any(w in label_lower for w in ["country phone", "phone code"]):
            return "United States"
        if label_lower.strip() == "country":
            return "United States"
        if any(w in label_lower for w in ["state", "province"]):
            return "Virginia"
        return ""

    def _clean_phone(self, raw: str) -> str:
        """Strip country code and dashes, return digits only. +1-703-928-0214 -> 7039280214"""
        digits = "".join(c for c in raw if c.isdigit())
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        return digits

    def _match_field_to_profile(self, label: str, p: dict, loc: dict, links: dict) -> str:
        """Map a field label to the right profile value."""
        # Explicitly skip fields we should NOT fill with profile text
        if any(w in label for w in ["phone extension", "extension"]):
            return ""
        if any(w in label for w in ["phone device", "device type",
                                     "country phone", "phone code"]):
            return ""

        if any(w in label for w in ["first name", "given name"]):
            return p["first_name"]
        if any(w in label for w in ["last name", "family name", "surname"]):
            return p["last_name"]
        if "email" in label and "confirm" not in label:
            return p["email"]
        if any(w in label for w in ["phone number", "mobile number", "telephone number"]):
            return self._clean_phone(p["phone"])
        if any(w in label for w in ["address", "street"]) and "email" not in label:
            return loc.get("address", "2111 Richmond Hwy")
        if label.strip() == "city" or "city" in label:
            return loc.get("city", "Arlington")
        if any(w in label for w in ["state", "province"]) and "united" not in label:
            return loc.get("state", "VA")
        if label.strip() == "country" or label == "country":
            return loc.get("country", "USA")
        if any(w in label for w in ["zip", "postal"]):
            return loc.get("zip", "22202")
        if "linkedin" in label:
            return links.get("linkedin", "")
        if "github" in label:
            return links.get("github", "")
        if any(w in label for w in ["portfolio", "website"]):
            return links.get("portfolio", "")
        return ""

    # === Main loop ============================================================

    async def apply(self, job_url: str, company: str, job_title: str):
        app_id = f"{company.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.logger.log_event(app_id, company, job_title, "init", "success", job_url)

        client = self._build_client()
        session_id = None

        try:
            session_id = await self._start_session(client)
            log(f"Session: {session_id}")
            self.logger.log_event(app_id, company, job_title, "session", "started", session_id)

            # Navigate to job page
            log(f"Navigating to: {job_url}")
            await client.sessions.navigate(id=session_id, url=job_url)
            await asyncio.sleep(5)

            # Main state machine -- react to whatever page we're on
            max_iterations = 30
            last_step_desc = ""
            same_step_count = 0
            job_posting_tries = 0
            for iteration in range(max_iterations):
                ctx = await self._page_context(client, session_id)
                page_type = ctx.get("page_type", "other")
                desc = ctx.get("description", "")
                log(f"\n--- Iteration {iteration+1} | Page: {page_type} ---")
                log(f"  {desc[:120]}")

                if page_type == "job_posting":
                    job_posting_tries += 1
                    if job_posting_tries <= 2:
                        log(f"On job posting -- clicking Apply (attempt {job_posting_tries})...")
                        await self._act(client, session_id,
                            "click the Apply button or Apply Now button or "
                            "Apply Manually link to start the job application")
                    else:
                        log(f"Apply not working after {job_posting_tries-1} tries -- trying alternatives...")
                        await self._act(client, session_id, "scroll down on the page")
                        await asyncio.sleep(1)
                        await self._act(client, session_id,
                            "click any link or button that contains the word Apply")
                    await asyncio.sleep(5)

                elif page_type == "sign_in":
                    ok = await self._do_sign_in(client, session_id)
                    if not ok:
                        log("Sign-in failed, trying to create account...")
                        await self._do_create_account(client, session_id)
                        self.logger.log_event(app_id, company, job_title,
                            "auth", "account_created", self.email)
                    else:
                        self.logger.log_event(app_id, company, job_title,
                            "auth", "signed_in", self.email)
                    await asyncio.sleep(3)

                elif page_type == "create_account":
                    await self._do_create_account(client, session_id)
                    self.logger.log_event(app_id, company, job_title,
                        "auth", "account_created", self.email)
                    await asyncio.sleep(3)

                elif page_type == "otp_verification":
                    otp = await self._prompt_otp()
                    if otp:
                        await self._fill_field(client, session_id,
                            "verification code", otp)
                        await self._act(client, session_id,
                            "click the Verify or Submit or Continue button")
                    else:
                        log("Waiting for magic link...")
                    await asyncio.sleep(5)

                elif page_type == "dashboard":
                    log("On dashboard -- navigating back to job...")
                    await client.sessions.navigate(id=session_id, url=job_url)
                    await asyncio.sleep(5)

                elif page_type == "application_form":
                    step_desc = desc[:60]
                    if step_desc == last_step_desc:
                        same_step_count += 1
                        log(f"Same step as before (attempt {same_step_count})")
                        if same_step_count >= 3:
                            log("Stuck on same step 3 times -- checking for errors...")
                            errors = await self._extract(client, session_id,
                                "Are there any validation error messages or required field "
                                "warnings visible on this page? List them.",
                                {"type": "object", "properties": {
                                    "errors": {"type": "array", "items": {"type": "string"}}
                                }, "required": ["errors"]})
                            err_list = errors.get("errors", [])
                            if err_list:
                                log(f"  Validation errors: {err_list}")
                                for err in err_list:
                                    await self._act(client, session_id,
                                        f"Fix this error: {err}. "
                                        f"Select the appropriate value or fill the required field.")
                                    await asyncio.sleep(1)
                            else:
                                log("  No errors detected. Trying to click Next harder...")
                            same_step_count = 0
                    else:
                        same_step_count = 0
                        last_step_desc = step_desc

                    log("Filling application form...")
                    await self._fill_application_step(client, session_id)
                    self.logger.log_event(app_id, company, job_title,
                        "form_step", "filled", "")
                    await asyncio.sleep(1)
                    # Try to advance
                    await self._act(client, session_id,
                        "click the Next or Continue or Save and Continue button "
                        "to go to the next step of the application")
                    await asyncio.sleep(4)

                elif page_type == "review_submit":
                    log("\n=== REVIEW PAGE REACHED ===")
                    log("Application is ready for review. Check the browser.")
                    self.logger.log_event(app_id, company, job_title,
                        "complete", "ready_for_review", "")
                    break

                else:
                    log(f"Unknown page type: {page_type}")
                    log("Attempting to click any prominent button to proceed...")
                    await self._act(client, session_id,
                        "click the most prominent action button on this page")
                    await asyncio.sleep(3)

            log("\nMain loop completed")

        except Exception as e:
            self.logger.log_event(app_id, company, job_title, "error", "failed", str(e))
            log(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                input("\n[JAAA] Press Enter to close the browser...")
            except (EOFError, KeyboardInterrupt):
                pass
            if session_id:
                try:
                    await client.sessions.end(id=session_id)
                except Exception:
                    pass
            await client.close()
            log("Done.")
