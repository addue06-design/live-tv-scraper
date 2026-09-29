import json
import sys
import time
import undetected_chromedriver as uc


def diagnose_channel(driver, channel_name, page_url):
  print("\n" + "=" * 60)
  print(f"🔍 [診斷開始] 頻道: {channel_name}")
  print(f"🔗 目標網址: {page_url}")
  print("=" * 60)

  try:
    start_fetch = time.time()
    driver.get(page_url)
    time.sleep(5)  # 給予充份載入時間

    current_url = driver.current_url
    page_title = driver.title
    page_source_head = driver.page_source[:300].replace("\n", " ")

    print(f"📌 實際載入 URL : {current_url}")
    print(f"📌 網頁 Title    : {page_title}")
    print(f"📌 HTML 前開頭  : {page_source_head}")

    # 檢查 DOM 內的媒體元素
    iframes = driver.find_elements("tag name", "iframe")
    videos = driver.find_elements("tag name", "video")
    print(f"🎥 DOM 偵測結果 : 找到 {len(iframes)} 個 <iframe>, {len(videos)} 個 <video>")

    for idx, frame in enumerate(iframes):
      src = frame.get_attribute("src")
      print(f"   ├─ iframe[{idx}] src: {src}")

    # 分析 Performance Network Logs
    print("\n🌐 [網路封包分析 (Performance Logs)]")
    m3u8_found = []
    all_network_urls = []

    logs = driver.get_log("performance")
    for entry in logs:
      try:
        log_data = json.loads(entry["message"])["message"]
        if log_data["method"] == "Network.responseReceived":
          res_url = log_data["params"]["response"]["url"]
          all_network_urls.append(res_url)
          if ".m3u8" in res_url:
            m3u8_found.append(res_url)
      except Exception:
        pass

    print(f"📊 總共捕捉到的 Network Response 數量: {len(all_network_urls)}")

    if m3u8_found:
      print(f"🎉 【成功】找到 {len(m3u8_found)} 個包含 .m3u8 的請求:")
      for url in m3u8_found:
        print(f"   🎯 {url}")
      return m3u8_found[0]
    else:
      print("❌ 【失敗】網路封包中未發現任何包含 .m3u8 的請求。")
      # 印出可疑的 API 請求輔助分析
      print("🔍 印出前 10 個與多媒體/API 相關的請求供排查:")
      media_related = [
          u
          for u in all_network_urls
          if any(k in u for k in ["api", "stream", "live", "hls", "player"])
      ]
      for u in media_related[:10]:
        print(f"   🔹 {u}")
      return None

  except Exception as e:
    print(f"💥 執行時發生 Exception: {e}")
    return None


def run_diagnostics():
  options = uc.ChromeOptions()
  options.add_argument("--headless=new")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--disable-gpu")
  options.add_argument("--window-size=1280,720")
  options.set_capability(
      "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
  )

  print("🚀 啟動 undetected-chromedriver 診斷模式...")
  driver = None

  try:
    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.execute_cdp_cmd("Network.enable", {})

    test_channels = {
        "緯來體育台": "https://livetvmax.com/channels/videoland-sports/",
        "ELTA體育1台": "https://livetvmax.com/channels/elta-sports1/",
    }

    results = {}
    for name, url in test_channels.items():
      res = diagnose_channel(driver, name, url)
      if res:
        results[name] = res

    # 確保寫入檔案以滿足工作流程
    with open("sports_channels.m3u", "w", encoding="utf-8") as f:
      f.write("#EXTM3U\n")
      for k, v in results.items():
        f.write(f"#EXTINF:-1,{k}\n{v}\n")

  except Exception as e:
    print(f"💥 主程序異常: {e}")
  finally:
    if driver:
      try:
        driver.quit()
      except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
  run_diagnostics()
