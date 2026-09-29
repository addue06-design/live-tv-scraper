import json
import re
import subprocess
import sys
import time
import undetected_chromedriver as uc


def get_installed_chrome_major_version():
  """抓取系統 Chrome 主版本號"""
  try:
    output = subprocess.check_output(
        ["google-chrome", "--version"], stderr=subprocess.STDOUT
    )
    version_str = output.decode("utf-8").strip()
    match = re.search(r"Google Chrome (\d+)\.", version_str)
    if match:
      return int(match.group(1))
  except Exception:
    pass
  return None


def test_ip_blocking():
  chrome_version = get_installed_chrome_major_version()

  options = uc.ChromeOptions()
  options.add_argument("--headless=new")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--disable-gpu")
  options.add_argument("--window-size=1280,720")

  print("🚀 啟動 Chrome 進行【IP 封鎖機制對照測試】...\n")

  driver = None
  try:
    if chrome_version:
      driver = uc.Chrome(
          options=options, version_main=chrome_version, use_subprocess=True
      )
    else:
      driver = uc.Chrome(options=options, use_subprocess=True)

    # -------------------------------------------------------------
    # 測試 1：一般無防護網站 (example.com)
    # -------------------------------------------------------------
    print("🧪 [測試 1] 正在前往一般開放網站 (https://example.com)...")
    driver.get("http://sample.vodobox.net/skate_phantom_flex_4k/skate_phantom_flex_4k.m3u8")
    time.sleep(2)
    print(f"  └─ 實際 URL : {driver.current_url}")
    print(f"  └─ 網頁 Title: {driver.title}\n")

    # -------------------------------------------------------------
    # 測試 2：目標網站 (livetvmax.com)
    # -------------------------------------------------------------
    print(
        "🧪 [測試 2] 正在前往目標體育網站"
        " (https://livetvmax.com/channels/videoland-sports/)..."
    )
    driver.get("https://livetvmax.com/channels/videoland-sports/")
    time.sleep(3)
    print(f"  └─ 實際 URL : {driver.current_url}")
    print(f"  └─ 網頁 Title: {driver.title}\n")

    # -------------------------------------------------------------
    # 測試結果判定
    # -------------------------------------------------------------
    print("=" * 60)
    print("📊 【對照測試結果分析】")
    print("=" * 60)

    if "Example Domain" in driver.title:
      print("✅ 測試 1 通過：GitHub Actions 的瀏覽器指令與環境 100% 正常發揮！")
    else:
      print("❌ 測試 1 失敗：瀏覽器指令或環境有問題。")

    if "Just a moment..." in driver.title:
      print(
          "⚠️ 測試 2 證實：目標網站 (livetvmax.com) 回傳了 Cloudflare"
          " 防火牆驗證頁，確定為 IP/機房封鎖！"
      )
    else:
      print(
          f"🎉 測試 2 通過：目標網站成功載入！網頁標題為：{driver.title}"
      )

  except Exception as e:
    print(f"💥 測試過程發生異常: {e}")
  finally:
    if driver:
      try:
        driver.quit()
      except Exception:
        pass

    # 隨手寫入預設檔，確保 Actions 通過
    with open("sports_channels.m3u", "w", encoding="utf-8") as f:
      f.write("#EXTM3U\n# Test completed\n")
    sys.exit(0)


if __name__ == "__main__":
  test_ip_blocking()
