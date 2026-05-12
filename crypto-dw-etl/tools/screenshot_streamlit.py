"""
Auto-capture screenshots of Streamlit dashboard via Playwright.

Assumes:  streamlit run streamlit_crypto_csv.py  is already running on port 8501.

Saves 5 screenshots (one per tab) to:
    _Data_Warehouse/_Data_Warehouse__Báo_cáo/Images/Demo/
        Main interface.png             (Tab 1 – Overview)
        Visualize.png                  (Tab 2 – Price & Volume)
        Detection.png                  (Tab 3 – Anomaly Detection)
        Individual ticker analysis.png (Tab 4 – OLAP Views)
        Upload.png                     (Tab 5 – Data Explorer)
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "_Data_Warehouse" / "_Data_Warehouse__Báo_cáo" / "Images" / "Demo"
OUT.mkdir(parents=True, exist_ok=True)

TABS = [
    ("Overview",          "Main interface.png"),
    ("Price & Volume",    "Visualize.png"),
    ("Anomaly Detection", "Detection.png"),
    ("OLAP Views",        "Individual ticker analysis.png"),
    ("Data Explorer",     "Upload.png"),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()

        print(f"Opening {URL} ...")
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_selector("text=CryptoDW Analytics", timeout=60_000)
        page.wait_for_timeout(8_000)  # extra wait for plotly to draw

        for label, fname in TABS:
            print(f"Tab: {label}")
            if label != "Overview":
                page.locator("button[role='tab']", has_text=label).click()
                page.wait_for_timeout(5_000)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1_500)
            target = OUT / fname
            page.screenshot(path=str(target), full_page=True)
            print(f"  -> {target}")

        browser.close()
        print("\nALL DONE.")


if __name__ == "__main__":
    main()
