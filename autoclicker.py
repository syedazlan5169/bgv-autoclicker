import cv2
import numpy as np
import mss
import pyautogui
import time
from datetime import datetime
from pynput import keyboard
import threading
import traceback
import os
import urllib.request
import zipfile
import shutil
import sys

LOCAL_VERSION = "1.0.2"  # Set this to your current version
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/syedazlan5169/bgv-autoclicker/main/version.txt"
ZIP_DOWNLOAD_URL = "https://github.com/syedazlan5169/bgv-autoclicker/archive/refs/heads/main.zip"

def check_for_update():
    try:
        remote_version = urllib.request.urlopen(REMOTE_VERSION_URL).read().decode().strip()
        if remote_version > LOCAL_VERSION:
            print(f"[Updater] New version {remote_version} available. Updating...")
            update_program()
            return True
        else:
            print(f"[Updater] Already on latest version ({LOCAL_VERSION})")
            return False
    except Exception as e:
        print(f"[Updater] Update check failed: {e}")
        return False

def update_program():
    try:
        zip_path = "update.zip"
        extract_dir = "update_temp"

        # Download ZIP
        urllib.request.urlretrieve(ZIP_DOWNLOAD_URL, zip_path)

        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Get the inner extracted folder (e.g. bgv-autoclicker-main)
        extracted_folder = os.path.join(extract_dir, os.listdir(extract_dir)[0])

        # Copy files to current folder
        for item in os.listdir(extracted_folder):
            src = os.path.join(extracted_folder, item)
            dst = os.path.join(".", item)

            if os.path.isdir(src):
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

         # Cleanup
        os.remove(zip_path)
        shutil.rmtree(extract_dir)

        print("[Updater] Update complete. Restarting...")

        # 🔁 Auto-restart the script
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        os.execv(python_exe, [python_exe, script_path])

        print("[Updater] Update complete. Please restart the application.")
        sys.exit(0)

    except Exception as e:
        print(f"[Updater] Update failed: {e}")


pyautogui.FAILSAFE = True

paused = False

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def toggle_pause():
    global paused
    paused = not paused
    log("Paused." if paused else "Resumed.")

def pause_listener():
    def on_press(key):
        if key == keyboard.Key.space:
            toggle_pause()
        elif key == keyboard.Key.esc:
            log("Escape key pressed. Exiting...")
            exit(0)
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

listener_thread = threading.Thread(target=pause_listener, daemon=True)
listener_thread.start()

def find_and_click(template_path, threshold=0.7, scroll=False, max_scroll=20):
    template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if template is None:
        log(f"Template {template_path} could not be loaded.")
        return False

    template_h, template_w = template.shape[:2]
    found = False

    with mss.mss() as sct:
        monitor = sct.monitors[1]

        attempts = 0
        while not found and (not scroll or attempts < max_scroll):
            if paused:
                time.sleep(0.5)
                continue

            screenshot = np.array(sct.grab(monitor))
            screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

            # Force grayscale for template matching
            gray_screenshot = cv2.cvtColor(screenshot_rgb, cv2.COLOR_BGR2GRAY)
            gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            result = cv2.matchTemplate(gray_screenshot, gray_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= threshold:
                click_x = max_loc[0] + template_w // 2
                click_y = max_loc[1] + template_h // 2
                pyautogui.moveTo(click_x, click_y)
                pyautogui.click()
                log(f"Clicked on {template_path} at ({click_x}, {click_y}) [Confidence: {max_val:.2f}]")
                found = True
                return True

            if scroll:
                pyautogui.scroll(-300)
                log(f"Scroll attempt {attempts + 1}")
                attempts += 1

            time.sleep(0.5)

    if not found:
        log(f"{template_path} not found after {attempts} attempts.")
    return False


# --- Main Loop ---
# check for update
check_for_update()

# Get delay value from user
delay_seconds = int(input("Enter analysis time in seconds: "))
log(f"Using {delay_seconds} seconds delay between steps")

while True:
    try:
        if paused:
            time.sleep(0.5)
            continue

        # Step 1: Wait for button1
        log("Waiting for button1.png indefinitely...")
        while not find_and_click('button1.png', threshold=0.7):
            if paused:
                time.sleep(0.5)
                continue

        # Step 2: Wait for user-specified delay
        time.sleep(delay_seconds)

        # Step 3: Scroll to find button2 (max 20 tries)
        log("Searching for button2.png by scrolling...")
        find_and_click('button2.png', threshold=0.7, scroll=True, max_scroll=20)

        # Step 4: Wait before next cycle
        time.sleep(2)

    except KeyboardInterrupt:
        log("Script interrupted by user.")
        break
    except pyautogui.FailSafeException:
        log("Failsafe triggered by moving mouse to top-left corner.")
        break
    except Exception as e:
        log(f"Unexpected error: {e}")
        traceback.print_exc()
        break

log("Script ended.")
