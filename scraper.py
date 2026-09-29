import json
import re
import subprocess
import sys
import time
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


# ============================================================
# Windows / GitHub Actions UTF-8
# ============================================================

if os.name == "nt":
  try:
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )
  except Exception:
    pass

  try:
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="replace"
    )
  except Exception:
    pass


def get_installed_chrome_major_version():
  try:
    if os.name == "nt":
      paths = [
          r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
          os.path.expandvars(
              r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
          ),
      ]

      for chrome_path in paths:
        if os.path.exists(chrome_path):
          result = subprocess.run(
              [
                  "powershell.exe",
                  "-NoProfile",
                  "-NonInteractive",
                  "-Command",
                  f"(Get-Item '{chrome_path}').VersionInfo.ProductVersion"
              ],
              capture_output=True,
              text=True,
              timeout=10,
              check=False
          )

          version_str = result.stdout.strip()

          match = re.search(
              r"(\d+)\.",
              version_str
          )

          if match:
            major_version = int(match.group(1))

            print(
                f"📌 偵測到系統 Google Chrome 版本: "
                f"{version_str} "
                f"(主版本號: {major_version})"
            )

            return major_version

    else:
      output = subprocess.check_output(
          ["google-chrome", "--version"],
          stderr=subprocess.STDOUT
      )

      version_str = output.decode(
          "utf-8"
      ).strip()

      match = re.search(
          r"Google Chrome (\d+)\.",
          version_str
      )

      if match:
        major_version = int(
            match.group(1)
        )

        print(
            f"📌 偵測到系統 Google Chrome 版本: "
            f"{version_str} "
            f"(主版本號: {major_version})"
        )

        return major_version

  except Exception as e:
    print(
        f"⚠️ Chrome 版本偵測失敗: {e}"
    )

  print(
      "⚠️ 無法取得 Chrome 主版本號，"
      "將讓 undetected-chromedriver 自行處理"
  )

  return None


def trigger_player_click(driver):
  try:
    driver.execute_script("""
      document.querySelectorAll(
        'div[class*="overlay"], div[class*="pop"], div[style*="z-index"]'
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
        'video, .dplayer, .jwplayer, div[id*="player"], div[class*="player"]'
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
        driver.switch_to.frame(
            frame
        )

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
        try:
          driver.switch_to.default_content()
        except Exception:
          pass

  except Exception:
    pass

  try:
    actions = ActionChains(
        driver
    )

    actions.move_by_offset(
        640,
        360
    ).click().send_keys(
        Keys.SPACE
    ).perform()

    actions.reset_actions()

  except Exception:
    pass


def capture_channel_m3u8(
    driver,
    channel_name,
    page_url,
    max_timeout=30
):
  print(
      f"\n➡️ 前往頻道: "
      f"{channel_name} "
      f"({page_url})"
  )

  try:
    driver.get(
        page_url
    )

    time.sleep(2)

    print(
        f"  [📌] Title: "
        f"{driver.title}"
    )

    print(
        f"  [📌] URL: "
        f"{driver.current_url}"
    )

  except Exception as e:
    print(
        f"  [⚠️ 連線失敗] "
        f"{e}"
    )

    return None

  start_time = time.time()
  last_click_time = 0

  while (
      time.time() - start_time
      < max_timeout
  ):
    current_elapsed = (
        time.time() - start_time
    )

    if (
        current_elapsed
        - last_click_time
        >= 2.5
    ):
      trigger_player_click(
          driver
      )

      last_click_time = (
          current_elapsed
      )

    try:
      logs = driver.get_log(
          "performance"
      )

      for entry in logs:
        try:
          log_data = json.loads(
              entry["message"]
          )["message"]

          if (
              log_data["method"]
              != "Network.responseReceived"
          ):
            continue

          res_url = log_data[
              "params"
          ][
              "response"
          ][
              "url"
          ]

          lower_url = (
              res_url.lower()
          )

          if (
              ".m3u8" in lower_url
              and any(
                  kw in lower_url
                  for kw in [
                      "api",
                      "live",
                      "stream",
                      "yeslivetv"
                  ]
              )
          ):
            print(
                f"  [🎯 動態獲取成功] "
                f"用時 "
                f"{round(current_elapsed, 1)} 秒 -> "
                f"{res_url[:120]}"
            )

            return {
                "url": res_url,
                "referer": page_url
            }

        except Exception:
          pass

    except Exception:
      pass

    time.sleep(
        0.8
    )

  print(
      f"  [❌ 逾時終止] "
      f"超過 {max_timeout} 秒"
      f"未偵測到 .m3u8 封包。"
  )

  print(
      f"  [📌 最終 Title] "
      f"{driver.title}"
  )

  return None


def run_fully_auto_sports_scraper():

  print(
      "\n"
      + "=" * 60
  )

  print(
      "【Self-hosted Windows 測試版】"
  )

  print(
      "=" * 60
  )

  chrome_version = (
      get_installed_chrome_major_version()
  )

  options = uc.ChromeOptions()

  # ============================================================
  # 重要：
  # 這次不使用 --headless
  # 因為你要測試的是「自己的 Windows」
  # 與你平常本機執行的環境是否一致。
  # ============================================================

  options.add_argument(
      "--disable-popup-blocking"
  )

  options.add_argument(
      "--autoplay-policy=no-user-gesture-required"
  )

  options.add_argument(
      "--window-size=1280,720"
  )

  options.set_capability(
      "goog:loggingPrefs",
      {
          "performance": "ALL",
          "browser": "ALL"
      }
  )

  driver = None

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
          "https://livetvmax.com/channels/dazn2/"
  }

  captured_m3u8 = {}

  user_agent = (
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 "
      "(KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36"
  )

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

    driver.execute_cdp_cmd(
        "Network.enable",
        {}
    )

    driver.set_window_size(
        1280,
        720
    )

    print(
        f"📌 Chrome 啟動完成"
    )

    print(
        f"📌 navigator.userAgent: "
        f"{driver.execute_script('return navigator.userAgent;')}"
    )

    print(
        f"📌 navigator.platform: "
        f"{driver.execute_script('return navigator.platform;')}"
    )

    print(
        f"📌 navigator.webdriver: "
        f"{driver.execute_script('return navigator.webdriver;')}"
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "【開始抓取 5 個頻道】"
    )

    print(
        "=" * 60
    )

    for name, url in (
        sports_channels.items()
    ):

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

        print(
            f"  ⚠️ {name} "
            f"進行二次重試..."
        )

        result = capture_channel_m3u8(
            driver,
            name,
            url,
            max_timeout=18
        )

      if result:
        captured_m3u8[name] = (
            result
        )

      time.sleep(
          2
      )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "【全自動抓取結果彙整】"
    )

    print(
        "=" * 60
    )

    m3u_content = (
        "#EXTM3U\n"
    )

    if captured_m3u8:

      for ch_name, data in (
          captured_m3u8.items()
      ):

        print(
            f"🎯 {ch_name} -> "
            f"{data['url']}"
        )

        m3u_content += (
            f"#EXTINF:-1,"
            f"{ch_name}\n"
        )

        m3u_content += (
            f"#EXTVLCOPT:"
            f"http-referrer="
            f"{data['referer']}\n"
        )

        m3u_content += (
            f"#EXTVLCOPT:"
            f"http-user-agent="
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
        f.write(
            m3u_content
        )

      print(
          f"\n🎉 成功匯出 "
          f"{len(captured_m3u8)}/"
          f"{len(sports_channels)} "
          f"個頻道"
      )

    else:

      print(
          "❌ 未能抓取到任何 "
          ".m3u8 網址。"
      )

      with open(
          "sports_channels.m3u",
          "w",
          encoding="utf-8"
      ) as f:
        f.write(
            "#EXTM3U\n"
            "# No streams detected\n"
        )

  except Exception as e:

    print(
        f"💥 主程序執行異常: "
        f"{e}"
    )

  finally:

    if driver:

      try:
        driver.quit()
      except Exception:
        pass


if __name__ == "__main__":
  run_fully_auto_sports_scraper()
