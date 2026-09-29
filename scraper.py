import json
import re
import subprocess
import sys
import time
import os
import undetected_chromedriver as uc


def get_installed_chrome_major_version():
  """動態抓取系統安裝的 Chrome 主版本號"""
  try:
    output = subprocess.check_output(
        ["google-chrome", "--version"],
        stderr=subprocess.STDOUT
    )
    version_str = output.decode("utf-8").strip()

    match = re.search(r"Google Chrome (\d+)\.", version_str)

    if match:
      major_version = int(match.group(1))

      print(
          f"📌 偵測到系統 Google Chrome 版本: "
          f"{version_str} (主版本號: {major_version})"
      )

      return major_version

  except Exception as e:
    print(f"⚠️ 無法取得 Chrome 版本訊息: {e}")

  return None


def is_cloudflare_challenge(driver):
  """判斷目前是否仍停留在 Cloudflare Challenge"""

  try:
    title = (driver.title or "").strip().lower()
    html = (driver.page_source or "")[:5000].lower()

    if "just a moment" in title:
      return True

    if "/cdn-cgi/challenge-platform" in html:
      return True

    if "cf-chl-" in html:
      return True

    if "cloudflare" in html and "challenge" in html:
      return True

  except Exception:
    pass

  return False


def wait_for_page_ready(driver, max_wait=30):
  """
  等待 Cloudflare Challenge 結束。
  不嘗試繞過 Challenge，只等待瀏覽器自己完成驗證。
  """

  print(f"⏳ 等待頁面載入 / Challenge 完成，最多 {max_wait} 秒...")

  start_time = time.time()

  last_status = None

  while time.time() - start_time < max_wait:
    try:
      title = driver.title or ""
      current_url = driver.current_url or ""

      challenge = is_cloudflare_challenge(driver)

      if challenge:
        status = "⚠️ Cloudflare Challenge 尚未完成"

        if status != last_status:
          print(status)

        last_status = status
        time.sleep(2)
        continue

      status = f"✅ 已離開 Challenge | Title: {title}"

      if status != last_status:
        print(status)

      print(f"📌 目前 URL: {current_url}")

      return True

    except Exception as e:
      print(f"⚠️ 等待頁面時發生問題: {e}")

    time.sleep(1)

  print("❌ 等待逾時，Cloudflare Challenge 仍未完成。")

  return False


def save_debug_files(driver, channel_name):
  """失敗時保存畫面與 HTML"""

  safe_name = re.sub(r'[\\/:*?"<>| ]+', "_", channel_name)

  png_file = f"debug_{safe_name}.png"
  html_file = f"debug_{safe_name}.html"

  try:
    driver.save_screenshot(png_file)
    print(f"🖼️ 已保存畫面: {png_file}")
  except Exception as e:
    print(f"⚠️ screenshot 保存失敗: {e}")

  try:
    with open(html_file, "w", encoding="utf-8") as f:
      f.write(driver.page_source)

    print(f"📄 已保存 HTML: {html_file}")

  except Exception as e:
    print(f"⚠️ HTML 保存失敗: {e}")


def extract_m3u8_from_logs(driver):
  """從 Chrome Performance Log 找出 m3u8"""

  m3u8_found = []

  try:
    logs = driver.get_log("performance")
  except Exception as e:
    print(f"⚠️ 無法取得 Performance Log: {e}")
    return []

  for entry in logs:
    try:
      log_data = json.loads(entry["message"])["message"]
      method = log_data.get("method")
      params = log_data.get("params", {})

      # Network.requestWillBeSent
      if method == "Network.requestWillBeSent":
        request = params.get("request", {})
        res_url = request.get("url", "")

        if ".m3u8" in res_url.lower():
          if res_url not in m3u8_found:
            m3u8_found.append(res_url)

      # Network.responseReceived
      elif method == "Network.responseReceived":
        response = params.get("response", {})
        res_url = response.get("url", "")

        if ".m3u8" in res_url.lower():
          if res_url not in m3u8_found:
            m3u8_found.append(res_url)

    except Exception:
      pass

  return m3u8_found


def diagnose_channel(driver, channel_name, page_url):

  print("\n" + "=" * 60)
  print(f"🔍 [診斷開始] 頻道: {channel_name}")
  print(f"🔗 目標網址: {page_url}")
  print("=" * 60)

  try:

    # ---------------------------------------------------------
    # 1. 開啟頁面
    # ---------------------------------------------------------

    print("🌐 開始載入頁面...")

    driver.get(page_url)

    # ---------------------------------------------------------
    # 2. 等待 Cloudflare / 頁面真正載入
    # ---------------------------------------------------------

    page_ready = wait_for_page_ready(driver, max_wait=30)

    if not page_ready:

      print("🛑 頁面沒有通過 Cloudflare Challenge。")
      save_debug_files(driver, channel_name)

      return None

    # ---------------------------------------------------------
    # 3. 額外等待播放器初始化
    # ---------------------------------------------------------

    print("⏳ 等待播放器與網路請求初始化...")

    time.sleep(8)

    # ---------------------------------------------------------
    # 4. 基本頁面資訊
    # ---------------------------------------------------------

    current_url = driver.current_url
    page_title = driver.title
    page_source_head = (
        driver.page_source[:500]
        .replace("\n", " ")
        .replace("\r", " ")
    )

    print(f"📌 實際載入 URL : {current_url}")
    print(f"📌 網頁 Title    : {page_title}")
    print(f"📌 HTML 前開頭  : {page_source_head}")

    # ---------------------------------------------------------
    # 5. DOM 偵測
    # ---------------------------------------------------------

    iframes = driver.find_elements("tag name", "iframe")
    videos = driver.find_elements("tag name", "video")

    print(
        f"🎥 DOM 偵測結果 : "
        f"找到 {len(iframes)} 個 <iframe>, "
        f"{len(videos)} 個 <video>"
    )

    for idx, frame in enumerate(iframes):

      try:
        src = frame.get_attribute("src")
      except Exception:
        src = None

      print(f"   ├─ iframe[{idx}] src: {src}")

    # ---------------------------------------------------------
    # 6. Network Log
    # ---------------------------------------------------------

    print("\n🌐 [網路封包分析]")

    m3u8_found = extract_m3u8_from_logs(driver)

    if m3u8_found:

      print(
          f"🎉 【成功】找到 "
          f"{len(m3u8_found)} 個包含 .m3u8 的請求:"
      )

      for url in m3u8_found:
        print(f"   🎯 {url}")

      return m3u8_found[0]

    # ---------------------------------------------------------
    # 7. 沒找到 m3u8
    # ---------------------------------------------------------

    print("❌ 【失敗】網路封包中未發現任何包含 .m3u8 的請求。")

    print("\n🔎 [進一步診斷]")

    if len(iframes) == 0 and len(videos) == 0:
      print("⚠️ 頁面沒有 iframe / video。")
      print("⚠️ 可能播放器仍未初始化，或播放器使用其他方式載入。")

    elif len(iframes) > 0:
      print("ℹ️ 有 iframe，下一步應檢查 iframe 內部播放器。")

    elif len(videos) > 0:
      print("ℹ️ 已找到 video，但目前沒有抓到 m3u8。")

    save_debug_files(driver, channel_name)

    return None

  except Exception as e:

    print(f"💥 執行診斷發生 Exception: {e}")

    try:
      save_debug_files(driver, channel_name)
    except Exception:
      pass

    return None


def run_diagnostics():

  chrome_version = get_installed_chrome_major_version()

  options = uc.ChromeOptions()

  # =========================================================
  # 注意：
  # 這裡故意「不使用 --headless」
  #
  # 因為你外部已經使用：
  #
  # xvfb-run ...
  #
  # 所以 Chrome 可以正常以有視窗模式執行，
  # 但畫面會由 Xvfb 提供，不會真的顯示在實體螢幕。
  # =========================================================

  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--disable-gpu")
  options.add_argument("--window-size=1280,720")

  options.set_capability(
      "goog:loggingPrefs",
      {
          "performance": "ALL",
          "browser": "ALL"
      }
  )

  print("🚀 啟動 undetected-chromedriver...")

  driver = None

  try:

    if chrome_version:

      driver = uc.Chrome(
          options=options,
          version_main=chrome_version,
          use_subprocess=True
      )

    else:

      driver = uc.Chrome(
          options=options,
          use_subprocess=True
      )

    # ---------------------------------------------------------
    # 開啟 Network logging
    # ---------------------------------------------------------

    driver.execute_cdp_cmd(
        "Network.enable",
        {}
    )

    test_channels = {
        "緯來體育台":
            "https://livetvmax.com/channels/videoland-sports/",

        "ELTA體育1台":
            "https://livetvmax.com/channels/elta-sports1/",
    }

    results = {}

    for name, url in test_channels.items():

      res = diagnose_channel(
          driver,
          name,
          url
      )

      if res:
        results[name] = res

    # ---------------------------------------------------------
    # 輸出 M3U
    # ---------------------------------------------------------

    with open(
        "sports_channels.m3u",
        "w",
        encoding="utf-8"
    ) as f:

      f.write("#EXTM3U\n")

      for channel_name, stream_url in results.items():

        f.write(
            f"#EXTINF:-1,{channel_name}\n"
            f"{stream_url}\n"
        )

    print("\n" + "=" * 60)
    print("📺 最終結果")
    print("=" * 60)

    if results:

      for name, url in results.items():
        print(f"✅ {name}")
        print(f"   {url}")

    else:

      print("❌ 沒有成功取得任何 m3u8")

    print("\n📁 已輸出: sports_channels.m3u")

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
