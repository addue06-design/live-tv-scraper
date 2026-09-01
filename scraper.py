import json
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains

# 關鍵：在虛擬顯示器(Xvfb)下，保持 False 即可讓網站以為是真實螢幕
HEADLESS_MODE = False


def trigger_play_click(driver):
  """精準觸發播放器與破除遮罩層"""
  try:
    driver.execute_script("""
            let overlays = document.querySelectorAll('div[class*="overlay"], div[class*="pop"], div[style*="z-index"]');
            overlays.forEach(el => {
                if (el.offsetWidth > 500 && el.offsetHeight > 300) {
                    el.click();
                }
            });
        """)
  except Exception:
    pass

  try:
    driver.execute_script("""
            let playerElements = document.querySelectorAll('video, .dplayer, .jwplayer, div[id*="player"], div[class*="player"]');
            playerElements.forEach(el => {
                el.click();
                let ev = new MouseEvent('click', { clientX: 640, clientY: 360, bubbles: true });
                el.dispatchEvent(ev);
            });
        """)
  except Exception:
    pass

  try:
    actions = ActionChains(driver)
    actions.move_by_offset(640, 360).click().perform()
    actions.reset_actions()
  except Exception:
    pass


def run_full_sports_scraper():
  options = uc.ChromeOptions()
  options.add_argument("--disable-popup-blocking")
  options.set_capability(
      "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
  )

  driver = uc.Chrome(options=options, use_subprocess=True)
  driver.execute_cdp_cmd("Network.enable", {})
  driver.set_window_size(1280, 720)

  sports_channels = {
      "緯來體育台": "https://livetvmax.com/channels/videoland-sports/",
      "ELTA體育1台": "https://livetvmax.com/channels/elta-sports1/",
      "ELTA體育2台": "https://livetvmax.com/channels/elta-sports2/",
      "DAZN 1": "https://livetvmax.com/channels/dazn1/",
      "DAZN 2": "https://livetvmax.com/channels/dazn2/",
  }

  captured_m3u8 = {}

  try:
    print("\n" + "=" * 60)
    print("【體育頻道 - 5頻道全自動巡航抓取】")
    print("=" * 60 + "\n")

    for name, url in sports_channels.items():
      print(f"➡️ 正在前往: {name} ({url})")

      for attempt in range(1, 3):
        driver.get(url)
        time.sleep(9)

        trigger_play_click(driver)
        time.sleep(7)

        logs = driver.get_log("performance")
        for entry in logs:
          try:
            log_data = json.loads(entry["message"])["message"]
            if log_data["method"] == "Network.responseReceived":
              res_url = log_data["params"]["response"]["url"]
              if ".m3u8" in res_url:
                captured_m3u8[name] = res_url
                break
          except Exception:
            pass

        if name in captured_m3u8:
          print(f"  [🎯 自動成功] -> {captured_m3u8[name][:65]}...")
          break
        else:
          if attempt == 1:
            print("  ⚠️ 第一次未抓到，正在進行二次嘗試重試...")
          else:
            print("  [❌ 自動失敗] 重試後仍未能觸發播放請求。")

    print("\n" + "=" * 60)
    if captured_m3u8:
      m3u_content = "#EXTM3U\n"
      for ch_name, stream_url in captured_m3u8.items():
        m3u_content += f"#EXTINF:-1,{ch_name}\n{stream_url}\n"

      with open("sports_channels.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)

      print(
          f"🎉 成功自動抓取 {len(captured_m3u8)}/{len(sports_channels)} 個頻道！"
      )
      print("已寫入 sports_channels.m3u")
    else:
      print("❌ 未能抓取任何頻道。")
    print("=" * 60)

  finally:
    try:
      driver.quit()
    except Exception:
      pass


if __name__ == "__main__":
  run_full_sports_scraper()