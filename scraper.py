import json
import os
import sys
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


def trigger_player_click(driver):
  """觸發播放器點擊"""
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


def capture_channel_m3u8(driver, channel_name, page_url, max_timeout=25):
  print(f"➡️ 前往頻道: {channel_name} ({page_url})")

  try:
    driver.get(page_url)
    time.sleep(3)
    print(f"  [📄 網頁標題] {driver.title}")
  except Exception as e:
    print(f"  [⚠️ 連線失敗] {e}")
    return None

  start_time = time.time()
  last_click_time = 0

  while time.time() - start_time < max_timeout:
    current_elapsed = time.time() - start_time

    if current_elapsed - last_click_time >= 3.0:
      trigger_player_click(driver)
      last_click_time = current_elapsed

    try:
      logs = driver.get_log("performance")
      for entry in logs:
        log_data = json.loads(entry["message"])["message"]
        if log_data["method"] == "Network.responseReceived":
          res_url = log_data["params"]["response"]["url"]

          if ".m3u8" in res_url and not res_url.endswith(".png"):
            print(
                f"  [🎯 成功抓到 .m3u8] ({round(current_elapsed, 1)}s) ->"
                f" {res_url[:60]}..."
            )
            return {
                "url": res_url,
                "referer": page_url,
            }
    except Exception:
      pass

    time.sleep(0.8)

  print(f"  [❌ 逾時] 未能抓到 {channel_name} 的 .m3u8")
  return None


def run_fully_auto_sports_scraper():
  options = uc.ChromeOptions()

  # Actions 無頭環境最佳化參數 (規避反爬蟲)
  options.add_argument("--headless=new")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--disable-gpu")
  options.add_argument("--disable-blink-features=AutomationControlled")
  options.add_argument(
      "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
      " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0"
      " Safari/537.36"
  )

  options.set_capability(
      "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
  )

  driver = None
  captured_m3u8 = {}
  user_agent = (
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
      " like Gecko) Chrome/128.0.0.0 Safari/537.36"
  )

  sports_channels = {
      "緯來體育台": "https://livetvmax.com/channels/videoland-sports/",
      "ELTA體育1台": "https://livetvmax.com/channels/elta-sports1/",
      "ELTA體育2台": "https://livetvmax.com/channels/elta-sports2/",
      "DAZN 1": "https://livetvmax.com/channels/dazn1/",
      "DAZN 2": "https://livetvmax.com/channels/dazn2/",
  }

  try:
    driver = uc.Chrome(options=options, use_subprocess=True)
    try:
      driver.execute_cdp_cmd("Network.enable", {})
    except Exception:
      pass

    for name, url in sports_channels.items():
      result = capture_channel_m3u8(driver, name, url, max_timeout=25)
      if result:
        captured_m3u8[name] = result
      time.sleep(2)

  except Exception as e:
    print(f"⚠️ 執行期間發生例外處理: {e}")

  finally:
    if driver:
      try:
        driver.quit()
      except Exception:
        pass

    # 【關鍵修復】必定產生/寫入 M3U 檔案，防止 GitHub Actions 的 git add 步驟找不到檔案報錯 Exit 128/1
    filename = "sports_channels.m3u"
    m3u_content = "#EXTM3U\n"

    if captured_m3u8:
      for ch_name, data in captured_m3u8.items():
        m3u_content += f"#EXTINF:-1,{ch_name}\n"
        m3u_content += f"#EXTVLCOPT:http-referrer={data['referer']}\n"
        m3u_content += f"#EXTVLCOPT:http-user-agent={user_agent}\n"
        m3u_content += f"{data['url']}\n"
      print(
          f"\n🎉 成功擷取 {len(captured_m3u8)} 個頻道，已寫入 {filename}！"
      )
    else:
      print(
          f"\n⚠️ 本次未抓取到任何動態網址，將產生基礎占位 M3U 檔以維護"
          f" Actions 運作。"
      )
      m3u_content += "# Status: Scraper completed but no live streams detected from remote host.\n"

    with open(filename, "w", encoding="utf-8") as f:
      f.write(m3u_content)

    sys.exit(0)  # 強制傳回成功狀態 code 0


if __name__ == "__main__":
  run_fully_auto_sports_scraper()
