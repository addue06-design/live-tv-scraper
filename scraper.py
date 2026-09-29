import json
import os
import sys
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


def trigger_player_click(driver):
  """觸發播放器：嘗試點擊播放按鈕與 iframe"""
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


def capture_channel_m3u8(driver, channel_name, page_url, max_timeout=30):
  print(f"➡️ 前往頻道: {channel_name} ({page_url})")

  try:
    driver.get(page_url)
    time.sleep(3)
    title = driver.title
    print(f"  [📄 網頁標題] {title}")
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
                f" {res_url}"
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

  # Actions 無頭環境優化參數
  options.add_argument("--headless=new")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--disable-gpu")
  options.add_argument(
      "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
      " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0"
      " Safari/537.36"
  )

  options.set_capability(
      "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
  )

  driver = uc.Chrome(options=options, use_subprocess=True)

  try:
    driver.execute_cdp_cmd("Network.enable", {})
  except Exception:
    pass

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
    for name, url in sports_channels.items():
      result = capture_channel_m3u8(driver, name, url, max_timeout=30)
      if result:
        captured_m3u8[name] = result
      time.sleep(2)

    if captured_m3u8:
      m3u_content = "#EXTM3U\n"
      for ch_name, data in captured_m3u8.items():
        m3u_content += f"#EXTINF:-1,{ch_name}\n"
        m3u_content += f"#EXTVLCOPT:http-referrer={data['referer']}\n"
        m3u_content += f"#EXTVLCOPT:http-user-agent={user_agent}\n"
        m3u_content += f"{data['url']}\n"

      with open("sports_channels.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
      print(
          f"\n🎉 成功覆寫 sports_channels.m3u，共包含"
          f" {len(captured_m3u8)} 個頻道。"
      )
    else:
      print("\n⚠️ 依然未抓到任何頻道，維持原有檔案。")

  finally:
    try:
      driver.quit()
    except Exception:
      pass


if __name__ == "__main__":
  run_fully_auto_sports_scraper()
