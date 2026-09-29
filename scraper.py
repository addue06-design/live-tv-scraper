import json
import re
import subprocess
import sys
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


def get_installed_chrome_major_version():
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


def print_environment_info(driver):
  print()
  print("=" * 60)
  print("【Browser Environment Diagnostics】")
  print("=" * 60)

  try:
    print("🌐 navigator.userAgent:")
    print(driver.execute_script(
        "return navigator.userAgent;"
    ))
  except Exception as e:
    print(f"❌ userAgent 讀取失敗: {e}")

  try:
    print("🖥️ navigator.platform:")
    print(driver.execute_script(
        "return navigator.platform;"
    ))
  except Exception as e:
    print(f"❌ platform 讀取失敗: {e}")

  try:
    print("🌍 navigator.language:")
    print(driver.execute_script(
        "return navigator.language;"
    ))
  except Exception as e:
    print(f"❌ language 讀取失敗: {e}")

  try:
    print("🌍 navigator.languages:")
    print(driver.execute_script(
        "return navigator.languages;"
    ))
  except Exception as e:
    print(f"❌ languages 讀取失敗: {e}")

  try:
    print("🔧 navigator.webdriver:")
    print(driver.execute_script(
        "return navigator.webdriver;"
    ))
  except Exception as e:
    print(f"❌ webdriver 讀取失敗: {e}")

  try:
    print("📐 Window size:")
    print(driver.get_window_size())
  except Exception as e:
    print(f"❌ Window size 讀取失敗: {e}")

  print("🌐 Public IPv4:")

  try:
    result = subprocess.run(
        ["curl", "-4", "-s", "--max-time", "10", "https://api.ipify.org"],
        capture_output=True,
        text=True,
        check=False
    )

    ip = result.stdout.strip()

    if ip:
      print(ip)
    else:
      print("❌ 無法取得 IPv4")

  except Exception as e:
    print(f"❌ Public IP 讀取失敗: {e}")

  print("=" * 60)
  print()


def is_cloudflare_challenge(driver):
  try:
    title = (driver.title or "").lower()
    html = (driver.page_source or "")[:10000].lower()

    if "just a moment" in title:
      return True

    if "challenge-platform" in html:
      return True

    if "cf-chl-" in html:
      return True

    if "cloudflare" in html and "challenge" in html:
      return True

  except Exception:
    pass

  return False


def wait_for_real_page(driver, max_wait=10):
  start = time.time()

  while time.time() - start < max_wait:
    try:
      if not is_cloudflare_challenge(driver):
        print("✅ 已離開 Cloudflare Challenge 頁面")
        print(f"📌 Title: {driver.title}")
        print(f"📌 URL: {driver.current_url}")
        return True

      print(
          f"⚠️ 目前仍為 Cloudflare Challenge "
          f"({round(time.time() - start, 1)}s)"
      )

    except Exception:
      pass

    time.sleep(1)

  print("❌ Cloudflare Challenge 尚未完成")
  return False


def save_debug(driver, channel_name):
  safe_name = re.sub(
      r'[\\/:*?"<>| ]+',
      "_",
      channel_name
  )

  png_file = f"debug_{safe_name}.png"
  html_file = f"debug_{safe_name}.html"

  try:
    driver.save_screenshot(png_file)
    print(f"🖼️ 已保存: {png_file}")
  except Exception as e:
    print(f"⚠️ screenshot 保存失敗: {e}")

  try:
    with open(
        html_file,
        "w",
        encoding="utf-8"
    ) as f:
      f.write(driver.page_source)

    print(f"📄 已保存: {html_file}")

  except Exception as e:
    print(f"⚠️ HTML 保存失敗: {e}")


def trigger_player_click(driver):
  """
  只有在已進入真正頻道頁面後才呼叫。
  """

  try:
    driver.execute_script("""
      document.querySelectorAll(
        'div[class*="overlay"], div[class*="pop"]'
      ).forEach(el => {
        if (
          el.offsetWidth > 300 &&
          el.offsetHeight > 200
        ) {
          el.remove();
        }
      });
    """)
  except Exception:
    pass

  try:
    driver.execute_script("""
      let players = document.querySelectorAll(
        'video, .dplayer, .jwplayer, ' +
        'div[id*="player"], div[class*="player"]'
      );

      players.forEach(p => {
        try {
          if (p.play) {
            p.play().catch(() => {});
          }

          p.click();
        } catch (e) {}
      });
    """)
  except Exception:
    pass

  try:
    iframes = driver.find_elements(
        "tag name",
        "iframe"
    )

    for frame in iframes:

      try:
        driver.switch_to.frame(frame)

        driver.execute_script("""
          let v = document.querySelector('video');

          if (v) {
            try {
              if (v.play) {
                v.play().catch(() => {});
              }

              v.click();
            } catch (e) {}
          }
        """)

        driver.switch_to.default_content()

      except Exception:
        driver.switch_to.default_content()

  except Exception:
    driver.switch_to.default_content()

  try:
    actions = ActionChains(driver)

    actions.move_to_element_with_offset(
        driver.find_element("tag name", "body"),
        640,
        360
    ).click().send_keys(Keys.SPACE).perform()

    actions.reset_actions()

  except Exception:
    pass


def get_m3u8_from_logs(driver):
  found = []

  try:
    logs = driver.get_log("performance")
  except Exception:
    return found

  for entry in logs:

    try:
      log_data = json.loads(
          entry["message"]
      )["message"]

      if log_data["method"] != "Network.responseReceived":
        continue

      res_url = log_data["params"][
          "response"
      ]["url"]

      lower_url = res_url.lower()

      if ".m3u8" not in lower_url:
        continue

      if any(
          kw in lower_url
          for kw in [
              "api",
              "live",
              "stream",
              "yeslivetv"
          ]
      ):
        if res_url not in found:
          found.append(res_url)

    except Exception:
      pass

  return found


def capture_channel_m3u8(
    driver,
    channel_name,
    page_url,
    max_timeout=35
):
  print()
  print("=" * 60)
  print(f"➡️ 前往頻道: {channel_name}")
  print(f"🔗 {page_url}")
  print("=" * 60)

  try:
    driver.get(page_url)

  except Exception as e:

    print(f"⚠️ driver.get() 失敗: {e}")

    time.sleep(2)

    try:
      driver.get(page_url)
    except Exception:
      print("❌ 第二次載入仍失敗")
      return None

  print("✅ driver.get() 完成")

  # -----------------------------------------------------------
  # 先確認是否卡在 Cloudflare
  # -----------------------------------------------------------

  try:
    print(f"📌 初始 Title: {driver.title}")
    print(f"📌 初始 URL: {driver.current_url}")
  except Exception:
    pass

  if is_cloudflare_challenge(driver):

    print(
        "⚠️ 偵測到 Cloudflare Challenge。"
    )

    if not wait_for_real_page(
        driver,
        max_wait=10
    ):
      print(
          "🛑 尚未進入真正頻道頁，"
          "停止播放器與 m3u8 掃描。"
      )

      save_debug(
          driver,
          channel_name
      )

      return None

  # -----------------------------------------------------------
  # 真正頻道頁面
  # -----------------------------------------------------------

  print("✅ 開始播放器 / Network 診斷")

  start_time = time.time()
  last_click_time = -2.5

  while time.time() - start_time < max_timeout:

    current_elapsed = time.time() - start_time

    # 如果途中重新跳回 Challenge，立即停止
    if is_cloudflare_challenge(driver):

      print(
          "⚠️ 執行期間重新出現 Cloudflare Challenge"
      )

      save_debug(
          driver,
          channel_name
      )

      return None

    # 每 2.5 秒觸發播放器
    if current_elapsed - last_click_time >= 2.5:

      print(
          f"🖱️ [{round(current_elapsed, 1)}s] "
          f"觸發播放器互動"
      )

      trigger_player_click(driver)

      last_click_time = current_elapsed

    # ---------------------------------------------------------
    # m3u8
    # ---------------------------------------------------------

    m3u8_list = get_m3u8_from_logs(driver)

    if m3u8_list:

      url = m3u8_list[0]

      print()
      print(
          f"🎯 【成功】{channel_name}"
      )
      print(
          f"⏱️ 用時: "
          f"{round(current_elapsed, 1)} 秒"
      )
      print(
          f"🔗 {url}"
      )

      return {
          "url": url,
          "referer": page_url
      }

    if int(current_elapsed) % 5 == 0:

      try:
        print(
            f"📌 Title: {driver.title}"
        )
      except Exception:
        pass

      time.sleep(0.2)

    time.sleep(0.8)

  print()
  print(
      f"❌ 【逾時】{channel_name} "
      f"超過 {max_timeout} 秒"
  )

  save_debug(
      driver,
      channel_name
  )

  return None


def run_fully_auto_sports_scraper():

  chrome_version = (
      get_installed_chrome_major_version()
  )

  options = uc.ChromeOptions()

  # -----------------------------------------------------------
  # GitHub + Xvfb
  # 不使用 headless
  # -----------------------------------------------------------

  options.add_argument(
      "--disable-popup-blocking"
  )

  options.add_argument(
      "--autoplay-policy=no-user-gesture-required"
  )

  options.add_argument(
      "--window-size=1280,720"
  )

  options.add_argument(
      "--no-sandbox"
  )

  options.add_argument(
      "--disable-dev-shm-usage"
  )

  options.add_argument(
      "--disable-gpu"
  )

  options.set_capability(
      "goog:loggingPrefs",
      {
          "performance": "ALL",
          "browser": "ALL"
      }
  )

  driver = None

  try:

    print()
    print("=" * 60)
    print("🚀 啟動 undetected-chromedriver")
    print("=" * 60)

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

    driver.execute_cdp_cmd(
        "Network.enable",
        {}
    )

    driver.set_window_size(
        1280,
        720
    )

    # ---------------------------------------------------------
    # 環境資訊
    # ---------------------------------------------------------

    print_environment_info(driver)

    sports_channels = {
        "緯來體育台":
            "https://livetvmax.com/channels/videoland-sports/",

        "ELTA體育1台":
            "https://livetvmax.com/channels/elta-sports1/",

        "ELTA體育2台":
            "https://livetvmax.com/channels/elta-sports2/",

        "DAZN 1":
            "https://livetvmax.com/channels/dazn1/",

        "DAZN 2":
            "https://livetvmax.com/channels/dazn2/",
    }

    captured_m3u8 = {}

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )

    print()
    print("=" * 60)
    print("【體育台 5 頻道 - GitHub 環境診斷版】")
    print("=" * 60)

    for name, url in sports_channels.items():

      timeout_limit = (
          35
          if name == "緯來體育台"
          else 22
      )

      result = capture_channel_m3u8(
          driver,
          name,
          url,
          max_timeout=timeout_limit
      )

      if not result:

        print()
        print(
            f"⚠️ {name} 進行第二次重試..."
        )

        result = capture_channel_m3u8(
            driver,
            name,
            url,
            max_timeout=15
        )

      if result:
        captured_m3u8[name] = result

      time.sleep(2)

    # ---------------------------------------------------------
    # 輸出
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("【全自動抓取結果】")
    print("=" * 60)

    if captured_m3u8:

      m3u_content = "#EXTM3U\n"

      for ch_name, data in captured_m3u8.items():

        print(
            f"🎯 {ch_name} -> "
            f"{data['url']}"
        )

        m3u_content += (
            f"#EXTINF:-1,{ch_name}\n"
        )

        m3u_content += (
            f"#EXTVLCOPT:http-referrer="
            f"{data['referer']}\n"
        )

        m3u_content += (
            f"#EXTVLCOPT:http-user-agent="
            f"{user_agent}\n"
        )

        m3u_content += (
            f"{data['url']}\n"
        )

      with open(
          "sports_channels.m3u",
          "w",
          encoding="utf-8"
      ) as f:
        f.write(m3u_content)

      print()
      print(
          f"🎉 成功取得 "
          f"{len(captured_m3u8)}/"
          f"{len(sports_channels)} 個頻道"
      )

      print(
          "📁 sports_channels.m3u"
      )

    else:
      print(
          "❌ 未取得任何頻道 m3u8"
      )

  except Exception as e:

    print(
        f"💥 主程序異常: {e}"
    )

    if driver:
      try:
        save_debug(
            driver,
            "main_error"
        )
      except Exception:
        pass

  finally:

    if driver:

      try:
        driver.quit()
      except Exception:
        pass


if __name__ == "__main__":
  run_fully_auto_sports_scraper()
