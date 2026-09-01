import json
import time
import undetected_chromedriver as uc


def run_batch_sports_scraper():
  print("正在啟動不受監控的 Chrome 瀏覽器核心...")

  options = uc.ChromeOptions()
  options.add_argument("--disable-popup-blocking")
  options.set_capability(
      "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
  )

  driver = uc.Chrome(options=options, use_subprocess=True)
  driver.execute_cdp_cmd("Network.enable", {})

  # 設定要抓取的 5 個體育頻道
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
    print("【體育台 5 頻道全抓取 - 採用穩定版核心】")
    print("目標頻道：緯來、ELTA 1、ELTA 2、DAZN 1、DAZN 2")
    print("1. 第一個頁面預留 30 秒，請完成 Cloudflare 驗證並點擊播放。")
    print("2. 後續頻道每個預留 15 秒，切換後請直接點擊播放按鈕。")
    print("=" * 60 + "\n")

    # 1. 處理第一個頻道 (緯來體育台) - 包含過驗證時間
    first_name = "緯來體育台"
    first_url = sports_channels[first_name]

    print(f"➡️ 正在前往第一個頻道: {first_name}...")
    driver.get(first_url)
    print("預留 30 秒：請完成 Cloudflare 驗證並手動點擊播放...")
    time.sleep(30)

    # 撈取第一個頻道的 m3u8
    logs = driver.get_log("performance")
    for entry in logs:
      try:
        log_data = json.loads(entry["message"])["message"]
        if log_data["method"] == "Network.responseReceived":
          url = log_data["params"]["response"]["url"]
          if any(
              kw in url.lower()
              for kw in ["api", "m3u8", "stream", "yeslivetv", "playlist"]
          ):
            if ".m3u8" in url:
              captured_m3u8[first_name] = url  # 蓋寫至最新的一條
      except Exception:
        pass

    if first_name in captured_m3u8:
      print(f"  [成功抓取] -> {captured_m3u8[first_name][:60]}...")
    else:
      print("  [未抓到] 請確認是否有點擊播放。")

    # 2. 處理後續的 4 個頻道
    other_channels = {k: v for k, v in sports_channels.items() if k != first_name}

    for name, url in other_channels.items():
      print(f"\n➡️ 正在切換至: {name} ({url})")
      driver.get(url)
      print("預留 15 秒：請直接點擊播放按鈕...")
      time.sleep(15)

      logs = driver.get_log("performance")
      for entry in logs:
        try:
          log_data = json.loads(entry["message"])["message"]
          if log_data["method"] == "Network.responseReceived":
            res_url = log_data["params"]["response"]["url"]
            if any(
                kw in res_url.lower()
                for kw in ["api", "m3u8", "stream", "yeslivetv", "playlist"]
            ):
              if ".m3u8" in res_url:
                captured_m3u8[name] = res_url  # 保留最新出現的 m3u8
        except Exception:
          pass

      if name in captured_m3u8:
        print(f"  [成功抓取] -> {captured_m3u8[name][:60]}...")
      else:
        print("  [未抓到] 請確認是否有點擊播放。")

    # 3. 輸出 M3U 播放清單
    print("\n" + "=" * 60)
    print("【抓取結果彙整】")
    if captured_m3u8:
      m3u_content = "#EXTM3U\n"
      for ch_name, stream_url in captured_m3u8.items():
        print(f"🎯 {ch_name} -> {stream_url}")
        m3u_content += f"#EXTINF:-1,{ch_name}\n{stream_url}\n"

      filename = "sports_channels.m3u"
      with open(filename, "w", encoding="utf-8") as f:
        f.write(m3u_content)

      print(f"\n🎉 5 大體育頻道已成功匯出至: {filename}")
    else:
      print("未能在日誌中撈到任何 .m3u8 網址。")
    print("=" * 60)

  except Exception as e:
    print(f"發生錯誤：{e}")

  finally:
    try:
      driver.quit()
    except:
      pass


if __name__ == "__main__":
  run_batch_sports_scraper()