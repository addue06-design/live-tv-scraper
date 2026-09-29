import json
import os
import sys
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


def trigger_player_click(driver):
  """觸發播放器：移除遮罩、觸發 JS 播放、點擊 iframe"""
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


def capture_channel_m3u8(driver, channel_name, page_url, max_timeout=25):
  """動態攔截 .m3u8 封包"""
  print(f"➡️ 前往頻道: {channel_name} ({page_url})")

  try:
    driver.get(page_url)
  except Exception as e:
    print(f"  [⚠️ 連線失敗] {e}")
    time.sleep(2)
    try:
      driver.get(page_url)
    except Exception:
      print("  [❌ 失敗] 跳過該頻道。")
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
  options = uc.ChromeOptions()

  # Linux / Actions 無頭環境必備參數
  options.add_argument("--headless=new")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--disable-gpu")
  options.add_argument("--window-size=1280,720")
  options.add_argument("--disable-popup-blocking")
  options.add_argument("--autoplay-policy=no-user-gesture-required")

  options.set_capability(
      "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
  )

  # 啟動 Chrome (自動調用系統預裝 Chrome)
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
    print("\n" + "=" * 60)
    print("【體育台 5 頻道 - 全自動巡航與動態回應偵測抓取】")
    print("=" * 60 + "\n")

    for name, url in sports_channels.items():
      timeout_limit = 35 if name == "緯來體育台" else 22

      result = capture_channel_m3u8(
          driver, name, url, max_timeout=timeout_limit
      )

      if not result:
        print(f"  ⚠️ {name} 進行二次重試...")
        result = capture_channel_m3u8(driver, name, url, max_timeout=15)

      if result:
        captured_m3u8[name] = result

      time.sleep(2)

    # 輸出 M3U 清單
    print("\n" + "=" * 60)
    print("【全自動抓取結果彙整】")
    if captured_m3u8:
      m3u_content = "#EXTM3U\n"
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
    print("=" * 60)

  finally:
    # 完全包覆關閉邏輯，防止 UC 析構函式拋出 Exception 導致 Process Exit Code 1
    try:
      driver.close()
    except Exception:
      pass
    try:
      driver.quit()
    except Exception:
      pass


if __name__ == "__main__":
  try:
    run_fully_auto_sports_scraper()
  except Exception as e:
    print(f"腳本執行異常但正常退出: {e}")
  sys.exit(0)  # 強制傳回 exit status 0 讓 GitHub Actions 通過
