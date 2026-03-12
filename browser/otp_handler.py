"""
OTP / Magic Link Handler

When the agent hits a verification screen it:
1. Prints a clear prompt to the terminal
2. Waits up to `timeout_s` seconds for you to type the OTP
3. If you don't type anything within the timeout, it continues anyway
   (useful for magic-link flows where you just click the link in your email)
"""
import sys
import asyncio
import threading


def _read_input_with_timeout(prompt: str, timeout_s: int) -> str | None:
    """
    Reads a line from stdin with a timeout.
    Returns the input string, or None if the timeout expired.
    """
    result = [None]
    event = threading.Event()

    def _reader():
        try:
            result[0] = input(prompt)
        except EOFError:
            pass
        finally:
            event.set()

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    event.wait(timeout=timeout_s)
    return result[0]


async def wait_for_otp(
    session_id: str,
    client,
    logger,
    app_id: str,
    company: str,
    job_title: str,
    timeout_s: int = 120,
) -> str | None:
    """
    Pauses the agent and waits for the user to provide an OTP.
    Also polls the page every 5 seconds to detect if a magic link was
    already clicked (page advances on its own).

    Returns the OTP string if entered, or None if magic-link flow detected.
    """
    print("\n" + "=" * 60)
    print("  VERIFICATION REQUIRED")
    print("=" * 60)
    print(f"  The job site sent a verification email to:")
    print(f"  {__import__('os').environ.get('ACCOUNT_EMAIL', 'your email')}")
    print()
    print("  Option A — OTP code:")
    print("    Type the code below and press Enter")
    print()
    print("  Option B — Magic link:")
    print("    Click the link in your email.")
    print(f"    The agent will auto-continue in {timeout_s}s.")
    print("=" * 60)

    logger.log_event(app_id, company, job_title, "otp_wait", "paused", f"Waiting up to {timeout_s}s for OTP or magic link")

    # Run the blocking input read in a thread so we can also poll the page
    loop = asyncio.get_event_loop()
    otp_future = loop.run_in_executor(
        None,
        _read_input_with_timeout,
        "  Enter OTP (or press Enter to skip): ",
        timeout_s,
    )

    # Poll every 5s to detect if the page advanced (magic link clicked)
    elapsed = 0
    while elapsed < timeout_s:
        if otp_future.done():
            break
        await asyncio.sleep(5)
        elapsed += 5
        try:
            # Check if we've moved past the verification screen
            result = await client.sessions.extract(
                id=session_id,
                instruction="Is there still a verification code input field visible on this page?",
                schema={
                    "type": "object",
                    "properties": {"verification_screen_visible": {"type": "boolean"}},
                    "required": ["verification_screen_visible"],
                },
            )
            still_on_verify = result.data.result.get("verification_screen_visible", True)
            if not still_on_verify:
                print("\n  Magic link detected — page advanced. Continuing...")
                logger.log_event(app_id, company, job_title, "otp_wait", "magic_link_detected", "Page advanced automatically")
                otp_future.cancel()
                return None
        except Exception:
            pass  # ignore polling errors

    otp = await otp_future if not otp_future.cancelled() else None
    if otp and otp.strip():
        logger.log_event(app_id, company, job_title, "otp_wait", "otp_received", f"OTP entered: {otp.strip()}")
        return otp.strip()

    logger.log_event(app_id, company, job_title, "otp_wait", "timeout", "No OTP entered — continuing")
    return None
