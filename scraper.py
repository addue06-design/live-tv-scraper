import json
import time
import undetected_chromedriver as uc

HEADLESS_MODE = False


def force_play_all_contexts(driver):
  """穿透所有 iframe 並強制播放 DOM 中的 HTML5 Video/Audio 元素"""
  # 1. 在主頁面清除擋路遮罩
  try:
    driver.execute_script("""
            let overlays = document.querySelectorAll('div[class*="overlay"], div[class*="pop"], div[style*="z-index"]');
            overlays.forEach(el => {
                if (el.offsetWidth > 200 && el.offsetHeight > 150) {
                    el.remove();
                }
            });
        """)
  except Exception:
    pass

  # 2. 搜集主頁面及所有 iframe 進行點擊與 HTML5 video.play()
  try:
    # 針對主層
    driver.execute_script("""
            document.querySelectorAll('video, audio, .dplayer, .jwplayer').forEach(v => {
                if (v.play) v.play().catch(()=>{});
                v.click();
            });
        """)
  except Exception:
    pass

  # 3. 穿透至子層 iframe 內觸發點擊與播放
  iframes = driver.find_elements("tag name", "iframe")
  for index, frame in enumerate(iframes):
    try:
      driver.switch_to.frame(frame)
      driver.execute_script("""
                document.querySelectorAll('video, audio, div, body').forEach(el => {
                    if (el.play) el.play().catch(()=>{});
                    el.click();
                });
            """)
      driver.switch_to.default_content()
    except Exception:
      driver.switch_to.default_content()


def run_full_sports_scraper():
  options = uc.ChromeOptions()
  options.add_argument("--disable-popup-blocking")

  # 關鍵：開啟 Linux 多媒體自動播放授權與偽裝
  options.add_argument(
      "--autoplay-policy=no-user-gesture-required"
  )  # 免手勢自動播放
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--window-size=1920,1080")

  options.set_capability(
      "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
  )

  driver = uc.Chrome(options=options, use_subprocess=True)
  driver.execute_cdp_cmd("Network.enable", {})

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
    print("【體育頻道 - 雲端 iframe 穿透巡航抓取】")
    print("=" * 60 + "\n")

    for name, url in sports_channels.items():
      print(f"➡️ 正在前往: {name} ({url})")

      for attempt in range(1, 3):
        driver.get(url)
        time.sleep(8)

        # 穿透 iframe 強制播放
        force_play_all_contexts(driver)
        time.sleep(8)

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
