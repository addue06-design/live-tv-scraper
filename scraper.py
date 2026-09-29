import json
import re
import subprocess
import sys
import time
import undetected_chromedriver as uc


def get_installed_chrome_major_version():
  """動態抓取系統安裝的 Chrome 主版本號 (避免未來 GitHub Runner 升級又版本衝突)"""
  try:
    output = subprocess.check_output(
        ["google-chrome", "--version"], stderr=subprocess.STDOUT
    )
    version_str = output.decode("utf-8").strip()
    match = re.search(r"Google Chrome (\d+)\.", version_str)
    if match:
      major_version = int(match.group(1))
      print(
          f"📌 偵測到系統 Google Chrome 版本: {version_str} (主版本号:"
          f" {major_version})"
      )
      return major_version
  except Exception as e:
    print(f"⚠️ 無法取得 Chrome 版本訊息: {e}")
  return None


def diagnose_channel(driver, channel_name, page_url):
  print("\n" + "=" * 60)
  print(f"🔍 [診斷開始] 頻道: {channel_name}")
  print(f"🔗 目標網址: {page_url}")
  print("=" * 60)

  try:
    driver.get(page_url)
    time.sleep(5)  # 給予充份載入時間

    current_url = driver.current_url
    page_title = driver.title
    page_source_head = driver.page_source[:300].replace("\n", " ")

    print(f"📌 實際載入 URL : {current_url}")
    print(f"📌 網頁 Title    : {page_title}")
    print(f"📌 HTML 前開頭  : {page_source_head}")

    iframes = driver.find_elements("tag name", "iframe")
    videos = driver.find_elements("tag name", "video")
    print(
        f"🎥 DOM 偵測結果 : 找到 {len(iframes)} 個 <iframe>, {len(videos)} 個"
        " <video>"
    )

    for idx, frame in enumerate(iframes):
      src = frame.get_attribute("src")
      print(f"   ├─ iframe[{idx}] src: {src}")

    # 分析 Network Logs
    print("\n🌐 [網路封包分析]")
    m3u8_found = []
    logs = driver.get_log("performance")
    for entry in logs:
      try:
        log_data = json.loads(entry["message"])["message"]
        if log_data["method"] == "Network.responseReceived":
          res_url = log_data["params"]["response"]["url"]
          if ".m3u8" in res_url:
            m3u8_found.append(res_url)
      except Exception:
        pass

    if m3u8_found:
      print(f"🎉 【成功】找到 {len(m3u8_found)} 個包含 .m3u8 的請求:")
      for url in m3u8_found:
        print(f"   🎯 {url}")
      return m3u8_found[0]
    else:
      print("❌ 【失敗】網路封包中未發現任何包含 .m3u8 的請求。")
      return None

  except Exception as e:
    print(f"💥 執行診斷發生 Exception: {e}")
    return None


def run_diagnostics():
  chrome_version = get_installed_chrome_major_version()

  options = uc.ChromeOptions()
  options.add_argument("--headless=new")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--disable-gpu")
  options.add_argument("--window-size=1280,720")
  options.set_capability(
      "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
  )

  print("🚀 啟動 undetected-chromedriver...")
  driver = None

  try:
    # 帶入版本號，避免 uc 自動下載不相容的最新 Driver
    if chrome_version:
      driver = uc.Chrome(
          options=options, version_main=chrome_version, use_subprocess=True
      )
    else:
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
