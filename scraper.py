# pip install -U selenium webdriver-manager pandas numpy
"""
Google Trends scraper — Switzerland curiosity radar
===================================================
Built on the proven pattern from webdriver_manage.py:
  - webdriver-manager (auto chromedriver)         -> no version mismatch
  - VISIBLE browser, --start-maximized            -> Google renders the chart
  - consent handled incl. shadow DOM              -> the bug that ate your run

Scrapes ONLY what you need: "Interest over time" for each keyword, for
Switzerland (CH) plus one leading market (US) to compute the transfer gap.
Saves  trends_raw/<keyword>__<GEO>.csv  -> feeds process_trends.py.

Run:
    python scraper.py
Then process:
    python process_trends.py
"""

import os
import time
import glob
import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ───────────────────────────── CONFIG ─────────────────────────────
KEYWORDS = [
    "Alpha Direct",
    "recycled down",
    "ultralight sleeping bag",
    "bikepacking",
    "Klettersteig",        # via ferrata (DE)
    "Skitour",             # ski touring (DE)
    "Trailrunning",
]
GEOS      = ["CH", "US"]        # CH = decision market, US = leading indicator
TIMEFRAME = "today 5-y"        # 5y so the analyzer can separate seasonality
HL        = "en-US"
RAW_DIR   = os.path.abspath("trends_raw")

# ───────────────────────────── DRIVER ─────────────────────────────
def build_driver():
    os.makedirs(RAW_DIR, exist_ok=True)
    options = Options()
    options.add_argument("--start-maximized")                       # from your script
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("prefs", {
        "download.default_directory": RAW_DIR,
        "download.prompt_for_download": False,
        "profile.default_content_setting_values.automatic_downloads": 1,
    })
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    return driver

# ──────────────────────────── CONSENT ─────────────────────────────
# Google shows a consent wall on EU/CH IPs. It can be a plain button, an
# iframe, OR a shadow DOM (your Wallapop trick). Try all three.
ACCEPT_LABELS = ["Accept all", "Alle akzeptieren", "Tout accepter",
                 "Accetta tutto", "I agree", "Ich stimme zu",
                 "Reject all", "Alle ablehnen"]

def _click_by_text(scope):
    for t in ACCEPT_LABELS:
        xp = (f"//button[normalize-space()='{t}'] | //*[@aria-label='{t}'] "
              f"| //div[@role='button'][normalize-space()='{t}']")
        for e in scope.find_elements(By.XPATH, xp):
            try:
                if e.is_displayed():
                    e.click()
                    time.sleep(1.5)
                    return True
            except Exception:
                continue
    return False

def accept_consent(driver):
    time.sleep(2)
    # 1) plain buttons
    if _click_by_text(driver):
        return True
    # 2) inside iframes
    for fr in driver.find_elements(By.TAG_NAME, "iframe"):
        try:
            driver.switch_to.frame(fr)
            if _click_by_text(driver):
                driver.switch_to.default_content()
                return True
        except Exception:
            pass
        finally:
            driver.switch_to.default_content()
    # 3) shadow DOM (exactly your Wallapop pattern)
    for host_sel in ["[id*='cmp']", "[class*='consent']", "tp-yt-paper-dialog"]:
        try:
            host = driver.find_element(By.CSS_SELECTOR, host_sel)
            root = driver.execute_script("return arguments[0].shadowRoot", host)
            if root:
                for sel in ["#cmpwelcomebtnyes a",
                            "button[aria-label*='Accept']", "button"]:
                    els = root.find_elements(By.CSS_SELECTOR, sel)
                    if els:
                        els[0].click()
                        time.sleep(1.5)
                        return True
        except Exception:
            continue
    return False

# ──────────────────────────── SCRAPE ──────────────────────────────
def fetch(driver, wait, keyword, geo):
    q = keyword.replace(" ", "%20")
    date = TIMEFRAME.replace(" ", "%20")
    url = (f"https://trends.google.com/trends/explore"
           f"?date={date}&geo={geo}&q={q}&hl={HL}")

    driver.get(url)
    accept_consent(driver)
    driver.get(url)            # second load after consent → chart renders

    # wait for the line-chart widget to actually exist (THIS was missing before)
    chart = None
    for sel in ["widget[type='fe_line_chart']", ".fe-line-chart",
                ".line-chart-directive", "div.fe-atoms-generic-content-container"]:
        try:
            chart = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            break
        except Exception:
            continue
    if chart is None:
        _dump(driver, keyword, geo, "no_chart")
        return False

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", chart)
    time.sleep(1.5)

    # find the CSV export control (several selectors; DOM drifts)
    export = None
    for sel in ["button.widget-actions-item.export",
                ".widget-actions-item.export",
                "button[title='CSV']", ".export"]:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        els = [e for e in els if e.is_displayed()]
        if els:
            export = els[0]
            break
    if export is None:
        _dump(driver, keyword, geo, "no_export")
        return False

    before = set(glob.glob(os.path.join(RAW_DIR, "*.csv")))
    try:
        export.click()
    except Exception:
        driver.execute_script("arguments[0].click();", export)   # JS fallback

    # wait for the download to land, then rename to analyzer's convention
    for _ in range(20):
        time.sleep(0.5)
        new = [f for f in set(glob.glob(os.path.join(RAW_DIR, "*.csv"))) - before
               if not f.endswith(".crdownload")]
        if new:
            dst = os.path.join(RAW_DIR, f"{keyword}__{geo}.csv".replace(" ", "_"))
            os.replace(new[0], dst)
            print(f"   ✓ {os.path.basename(dst)}")
            return True
    _dump(driver, keyword, geo, "no_download")
    return False

def _dump(driver, keyword, geo, why):
    """On failure, save a screenshot + HTML so you can see what blocked it."""
    tag = f"FAIL_{keyword}_{geo}_{why}".replace(" ", "_")
    try:
        driver.save_screenshot(os.path.join(RAW_DIR, tag + ".png"))
        with open(os.path.join(RAW_DIR, tag + ".html"), "w") as f:
            f.write(driver.page_source)
        print(f"   ✗ {why} — saved {tag}.png / .html for inspection")
    except Exception:
        print(f"   ✗ {why}")

# ───────────────────────────── MAIN ───────────────────────────────
def main():
    driver = build_driver()
    wait = WebDriverWait(driver, 20)
    try:
        for kw in KEYWORDS:
            print(f"[scrape] {kw}")
            for geo in GEOS:
                ok = fetch(driver, wait, kw, geo)
                if not ok:
                    print(f"   (manual fallback: export {kw}/{geo} from the open "
                          f"browser into trends_raw/ as {kw}__{geo}.csv)")
                time.sleep(4 + random.random() * 5)   # polite; dodges 429
    finally:
        input("Done. Press ENTER to close the browser...")
        driver.quit()

if __name__ == "__main__":
    main()