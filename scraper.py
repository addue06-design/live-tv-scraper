import json
import re
import subprocess
import sys
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


def get_installed_chrome_major_version():
  """動態抓取 GitHub Runner 的 Chrome 版本，防止 v153/v154 不相容"""
  try:
    output = subprocess.check_output(
        ["google-chrome", "--version"], stderr=subprocess.STDOUT
    )
    version_str = output.decode("utf-8").strip()
    match = re.search(r"Google Chrome (\d+)\.", version_str)
    if match:
      return int(match.group(1))
  except Exception:
    pass
  return None


def bypass_cloudflare_turnstile(driver):
  """自動偵測並點擊 Cloudflare Turnstile 'Verify you are human' 勾選框"""
  # 檢查頁面標題或內容是否包含 Cloudflare 驗證
  if "Just a moment..." not in driver.title and "verification" not in driver.title.lower():
    return True

  print("  [🔍 偵測到 Cloudflare 驗證框] 嘗試自動穿透點擊...")

  for attempt in range(8):
    try:
      # 切換到 Cloudflare Turnstile 專屬的 iframe
      iframes = driver.find_elements("tag name", "iframe")
      for frame in iframes:
        src = frame.get_attribute("src") or ""
        if "challenges.cloudflare.com" in src or "turnstile" in src:
          driver.switch_to.frame(frame)

          # 透過 JS 尋找並點擊 checkbox
          clicked = driver.execute_script("""
                        let cb = document.querySelector('input[type="checkbox"]');
                        if (cb) { cb.click(); return true; }
                        let stage = document.querySelector('#challenge-stage') || document.querySelector('.mark');
                        if (stage) { stage.click(); return true; }
                        return false;
                    """)

          driver.switch_to.default_content()
          if clicked:
            print(f"  [🎯 成功點擊驗證框] 等待 4 秒通過驗證 (第 {attempt+1} 次)...")
            time.sleep(4)
            if "Just a moment..." not in driver.title:
              print("  [🎉 驗證通過！] 已進入頻道頁面")
              return True

      # 備用方案：穿透 Shadow DOM 尋找勾選框
      driver.execute_script("""
                document.querySelectorAll('div').forEach(div => {
                    if (div.shadowRoot) {
                        let cb = div.shadowRoot.querySelector('input[type="checkbox"]');
                        if (cb) cb.click();
                    }
                });
            """)

    except Exception:
      try:
        driver.switch_to.default_content()
      except Exception:
        pass

    time.sleep(1.5)

  print(f"  [📌 點擊結束] 目前網頁 Title: {driver.title}")
  return "Just a moment..." not in driver.title


def trigger_player_click(driver):
  """深層觸發播放器：清除遮罩、點擊主頁面與 iframe 內部的 video 元素"""
  try:
    driver.execute_script("""
            document.querySelectorAll('div[class*="overlay"], div[class*="pop"], div[style*="z-index"]').forEach(el => {
                if (el.offsetWidth > 300 && el.offsetHeight > 200) el.remove();
            });
        """)
  except Exception:
    pass

  try:
    driver.execute_script("""
            let players = document.querySelectorAll('video, .dplayer, .jwplayer, div[id*="player"], div[class*="player"]');
            players.forEach(p => {
                if (p.play) p.play().catch(()=>{});
                p.click();
            });
        """)
  except Exception:
    pass

  try:
    iframes = driver.find_elements("tag name", "iframe")
    for frame in iframes:
      try:
        driver.switch_to.frame(frame)
        driver.execute_script("""
                    let v = document.querySelector('video');
                    if (v) { if (v.play) v.play().catch(()=>{}); v.click(); }
                """)
        driver.switch_to.default_content()
      except Exception:
        driver.switch_to.default_content()
  except Exception:
    pass

  try:
    actions = ActionChains(driver)
    actions.move_by_offset(640, 360).click().send_keys(Keys.SPACE).perform()
    actions.reset_actions()
  except Exception:
    pass


def capture_channel_m3u8(driver, channel_name, page_url, max_timeout=30):
  """動態輪詢攔截 .m3u8 封包 (整合 Cloudflare 穿透)"""
  print(f"\n➡️ 前往頻道: {channel_name} ({page_url})")

  try:
    driver.get(page_url)
    time.sleep(2)

    # 關鍵插入：先檢查並自動點擊 Cloudflare "Verify you are human" 方塊
    bypass_cloudflare_turnstile(driver)

  except Exception as e:
    print(f"  [⚠️ 連線失敗] 前往頁面時發生異常: {e}")
    return None

  start_time = time.time()
  last_click_time = 0

  while time.time() - start_time < max_timeout:
    current_elapsed = time.time() - start_time

    if current_elapsed - last_click_time >= 2.5:
      trigger_player_click(driver)
      last_click_time = current_elapsed

    try:
      logs = driver.get_log("performance")
      for entry in logs:
        log_data = json.loads(entry["message"])["message"]
        if log_data["method"] == "Network.responseReceived":
          res_url = log_data["params"]["response"]["url"]

          if ".m3u8" in res_url and any(
              kw in res_url.lower()
              for kw in ["api", "live", "stream", "yeslivetv"]
          ):
            print(
                f"  [🎯 動態獲取成功] 用時 {round(current_elapsed, 1)} 秒 ->"
                f" {res_url[:65]}..."
            )
            return {
                "url": res_url,
                "referer": page_url,
            }
    except Exception:
      pass

    time.sleep(0.8)

  print(f"  [❌ 逾時終止] 超過 {max_timeout} 秒未偵測到 .m3u8 封包。")
  return None


def run_fully_auto_sports_scraper():
  chrome_version = get_installed_chrome_major_version()

  options = uc.ChromeOptions()
  options.add_argument("--headless=new")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--disable-gpu")
  options.add_argument("--disable-popup-blocking")
  options.add_argument("--autoplay-policy=no-user-gesture-required")
  options.add_argument("--window-size=1280,720")
  options.set_capability(
      "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
  )

  driver = None
  sports_channels = {
      "緯來體育台": "https://livetvmax.com/channels/videoland-sports/",
      "ELTA體育1台": "https://livetvmax.com/channels/elta-sports1/",
      "ELTA體育2台": "https://livetvmax.com/channels/elta-sports2/",
      "DAZN 1": "https://livetvmax.com/channels/dazn1/",
      "DAZN 2": "https://livetvmax.com/channels/dazn2/",
  }

  captured_m3u8 = {}
  user_agent = (
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
      " like Gecko) Chrome/128.0.0.0 Safari/537.36"
  )

  try:
    print("\n" + "=" * 60)
    print("【體育台 5 頻道 - 自動 Cloudflare 穿透與 M3U8 抓取】")
    print("=" * 60)

    if chrome_version:
      driver = uc.Chrome(
          options=options, version_main=chrome_version, use_subprocess=True
      )
    else:
      driver = uc.Chrome(options=options, use_subprocess=True)

    driver.execute_cdp_cmd("Network.enable", {})

    for name, url in sports_channels.items():
      timeout_limit = 35 if name == "緯來體育台" else 22
      result = capture_channel_m3u8(
          driver, name, url, max_timeout=timeout_limit
      )

      if not result:
        print(f"  ⚠️ {name} 進行二次重試...")
        result = capture_channel_m3u8(driver, name, url, max_timeout=18)

      if result:
        captured_m3u8[name] = result

      time.sleep(2)

    print("\n" + "=" * 60)
    print("【全自動抓取結果彙整】")
    m3u_content = "#EXTM3U\n"

    if captured_m3u8:
      for ch_name, data in captured_m3u8.items():
        print(f"🎯 {ch_name} -> {data['url']}")
        m3u_content += f"#EXTINF:-1,{ch_name}\n"
        m3u_content += f"#EXTVLCOPT:http-referrer={data['referer']}\n"
        m3u_content += f"#EXTVLCOPT:http-user-agent={user_agent}\n"
        m3u_content += f"{data['url']}\n"

      filename = "sports_channels.m3u"
      with open(filename, "w", encoding="utf-8") as f:
        f.write(m3u_content)

      print(
          f"\n🎉 成功匯出 {len(captured_m3u8)}/{len(sports_channels)} 個頻道至"
          f" {filename}"
      )
    else:
      print("❌ 未能抓取到任何頻道的 .m3u8 網址。")
      with open("sports_channels.m3u", "w", encoding="utf-8") as f:
        f.write("# EXTM3U\n# No streams detected\n")

    print("=" * 60)

  except Exception as e:
    print(f"💥 主程序執行異常: {e}")
  finally:
    if driver:
      try:
        driver.close()
        driver.quit()
      except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
  run_fully_auto_sports_scraper()
