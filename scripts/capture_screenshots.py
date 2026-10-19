"""
TechSift AI - Automated Showcase Screenshot Capture.
Uses Playwright with headless Chromium to capture high-fidelity 1440x900 screenshots
for the public portfolio repository directly from the verified isolated demo environment.
"""

import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(os.environ.get("SCREENSHOT_OUTPUT_DIR", Path(__file__).resolve().parent.parent / "docs" / "screenshots"))
DOC_ID = "bf7640b1-11ec-4cdb-b78c-6ecaa09afda9"
BASE_URL = "http://127.0.0.1:5173"

QUIZ_ATTEMPT_ID = "2816c8b2-4016-479c-99c4-e99782465ec9"
FINAL_EXAM_ATTEMPT_ID = "e7420627-6554-4049-ac72-656a56da956a"


async def setup_page_env(page, dark: bool = True, rtl: bool = False):
    """Configures theme and language context cleanly."""
    theme = "dark" if dark else "light"
    lang = "ar" if rtl else "en"
    
    await page.add_init_script(f"""
        localStorage.setItem('techsift_theme', '{theme}');
        localStorage.setItem('techsift_language', '{lang}');
    """)


async def wait_and_stabilize(page, ms: int = 1200):
    """Waits for animations, fonts, and data queries to settle."""
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(ms / 1000.0)


async def capture_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        # 1. Screenshot 01: Library Multi-format
        print("\n--- Capturing 01_library_multiformat.png ---")
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1
        )
        page = await context.new_page()
        await setup_page_env(page, dark=True, rtl=False)
        await page.goto(f"{BASE_URL}/documents")
        await wait_and_stabilize(page)
        
        # Click upload button to show dropzone banner alongside documents table
        upload_btn = page.locator("button:has-text('Upload Document'), button:has-text('Upload')").first
        if await upload_btn.is_visible():
            await upload_btn.click()
            await asyncio.sleep(0.5)
            
        await wait_and_stabilize(page, 800)
        out_01 = OUTPUT_DIR / "01_library_multiformat.png"
        await page.screenshot(path=str(out_01))
        print(f"Captured: {out_01} ({out_01.stat().st_size} bytes)")
        await context.close()

        # 2. Screenshot 02: Processing Pipeline
        print("\n--- Capturing 02_processing_pipeline.png ---")
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1
        )
        page = await context.new_page()
        await setup_page_env(page, dark=True, rtl=False)
        
        # Route interceptor to simulate live processing status on document
        async def handle_doc(route):
            res = await route.fetch()
            data = await res.json()
            data["status"] = "processing"
            await route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=__import__("json").dumps(data)
            )
        
        await page.route(f"**/api/v1/documents/{DOC_ID}", handle_doc)
        await page.goto(f"{BASE_URL}/workspace/{DOC_ID}?tab=summary")
        await wait_and_stabilize(page)
        
        out_02 = OUTPUT_DIR / "02_processing_pipeline.png"
        await page.screenshot(path=str(out_02))
        print(f"Captured: {out_02} ({out_02.stat().st_size} bytes)")
        await context.close()

        # 3. Screenshot 03: Executive Summary
        print("\n--- Capturing 03_executive_summary.png ---")
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1
        )
        page = await context.new_page()
        await setup_page_env(page, dark=True, rtl=False)
        await page.goto(f"{BASE_URL}/workspace/{DOC_ID}?tab=summary")
        await wait_and_stabilize(page, 1500)
        
        out_03 = OUTPUT_DIR / "03_executive_summary.png"
        await page.screenshot(path=str(out_03))
        print(f"Captured: {out_03} ({out_03.stat().st_size} bytes)")
        await context.close()

        # 4. Screenshot 04: Bilingual Audio Studio (Arabic RTL)
        print("\n--- Capturing 04_bilingual_audio_studio.png ---")
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1
        )
        page = await context.new_page()
        await setup_page_env(page, dark=True, rtl=True)
        await page.goto(f"{BASE_URL}/workspace/{DOC_ID}?tab=audio&mode=narration")
        await wait_and_stabilize(page, 1500)
        
        await page.evaluate("window.scrollTo(0, 0)")
        await wait_and_stabilize(page, 800)
        out_04 = OUTPUT_DIR / "04_bilingual_audio_studio.png"
        await page.screenshot(path=str(out_04))
        print(f"Captured: {out_04} ({out_04.stat().st_size} bytes)")
        await context.close()

        # 5. Screenshot 05: Educational Podcast (English LTR)
        print("\n--- Capturing 05_educational_podcast.png ---")
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1
        )
        page = await context.new_page()
        await setup_page_env(page, dark=True, rtl=False)
        await page.goto(f"{BASE_URL}/workspace/{DOC_ID}?tab=audio&mode=podcast")
        await wait_and_stabilize(page, 1500)
        
        await page.evaluate("window.scrollTo(0, 0)")
        await wait_and_stabilize(page, 800)
        out_05 = OUTPUT_DIR / "05_educational_podcast.png"
        await page.screenshot(path=str(out_05))
        print(f"Captured: {out_05} ({out_05.stat().st_size} bytes)")
        await context.close()

        # 6. Screenshot 06: Learning Path Curriculum
        print("\n--- Capturing 06_learning_path_curriculum.png ---")
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1
        )
        page = await context.new_page()
        await setup_page_env(page, dark=True, rtl=False)
        await page.goto(f"{BASE_URL}/workspace/{DOC_ID}?tab=learning&studioTab=curriculum")
        await wait_and_stabilize(page, 1500)
        
        await page.evaluate("window.scrollTo(0, 0)")
        await wait_and_stabilize(page, 800)
        out_06 = OUTPUT_DIR / "06_learning_path_curriculum.png"
        await page.screenshot(path=str(out_06))
        print(f"Captured: {out_06} ({out_06.stat().st_size} bytes)")
        await context.close()

        # 7. Screenshot 07: Interactive Quiz Feedback (Dark Mode)
        print("\n--- Capturing 07_interactive_quiz_feedback.png ---")
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1
        )
        page = await context.new_page()
        await setup_page_env(page, dark=True, rtl=False)
        await page.goto(
            f"{BASE_URL}/workspace/{DOC_ID}?tab=learning&assessment=lesson_quiz&attempt={QUIZ_ATTEMPT_ID}"
        )
        await wait_and_stabilize(page, 1800)
        
        out_07 = OUTPUT_DIR / "07_interactive_quiz_feedback.png"
        await page.screenshot(path=str(out_07))
        print(f"Captured: {out_07} ({out_07.stat().st_size} bytes)")
        await context.close()

        # 8. Screenshot 08: Comprehensive Exam (Light Mode)
        print("\n--- Capturing 08_comprehensive_exam.png ---")
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1
        )
        page = await context.new_page()
        await setup_page_env(page, dark=False, rtl=False)
        await page.goto(
            f"{BASE_URL}/workspace/{DOC_ID}?tab=learning&assessment=final_assessment&attempt={FINAL_EXAM_ATTEMPT_ID}"
        )
        await wait_and_stabilize(page, 1800)
        
        out_08 = OUTPUT_DIR / "08_comprehensive_exam.png"
        await page.screenshot(path=str(out_08))
        print(f"Captured: {out_08} ({out_08.stat().st_size} bytes)")
        await context.close()

        # 9. Screenshot 09: Progress Dashboard
        print("\n--- Capturing 09_progress_dashboard.png ---")
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1
        )
        page = await context.new_page()
        await setup_page_env(page, dark=True, rtl=False)
        await page.goto(f"{BASE_URL}/workspace/{DOC_ID}?tab=learning&studioTab=dashboard")
        await wait_and_stabilize(page, 1500)
        
        out_09 = OUTPUT_DIR / "09_progress_dashboard.png"
        await page.screenshot(path=str(out_09))
        print(f"Captured: {out_09} ({out_09.stat().st_size} bytes)")
        await context.close()

        await browser.close()
    print("\n[SUCCESS] All 9 showcase screenshots captured successfully.")


if __name__ == "__main__":
    asyncio.run(capture_all())
