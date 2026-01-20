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

LOCAL_VERSION = "1.0.3"
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/syedazlan5169/bgv-autoclicker/main/version.txt"
ZIP_DOWNLOAD_URL = "https://github.com/syedazlan5169/bgv-autoclicker/archive/refs/heads/main.zip"

paused = False
exiting = False
pending_delay_change = 0

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

        urllib.request.urlretrieve(ZIP_DOWNLOAD_URL, zip_path)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        extracted_folder = os.path.join(extract_dir, os.listdir(extract_dir)[0])

        for item in os.listdir(extracted_folder):
            src = os.path.join(extracted_folder, item)
            dst = os.path.join(".", item)

            if os.path.isdir(src):
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        os.remove(zip_path)
        shutil.rmtree(extract_dir)

        print("[Updater] Update complete. Restarting...")
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        os.execv(python_exe, [python_exe, script_path])

    except Exception as e:
        print(f"[Updater] Update failed: {e}")

pyautogui.FAILSAFE = True

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def toggle_pause():
    global paused
    paused = not paused
    log("Paused." if paused else "Resumed.")

def pause_listener():
    def on_press(key):
        global paused, exiting, pending_delay_change
        if key == keyboard.Key.space:
            toggle_pause()
        elif key == keyboard.Key.esc:
            if not exiting:
                exiting = True
                log("Escape key pressed. Exiting in 3 seconds...")
        elif hasattr(key, 'char'):
            if key.char == '+':
                pending_delay_change += 1
                log("Delay increased by 1 second (applied next loop)")
            elif key.char == '-':
                pending_delay_change -= 1
                log("Delay decreased by 1 second (applied next loop)")
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

listener_thread = threading.Thread(target=pause_listener, daemon=True)
listener_thread.start()

def safe_sleep(seconds):
    remaining = seconds
    while remaining > 0:
        if exiting:
            break
        if paused:
            time.sleep(0.5)
        else:
            sleep_chunk = min(0.1, remaining)
            time.sleep(sleep_chunk)
            remaining -= sleep_chunk

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
            if paused or exiting:
                safe_sleep(0.5)
                continue

            screenshot = np.array(sct.grab(monitor))
            screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
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

            safe_sleep(0.5)

    if not found:
        log(f"{template_path} not found after {attempts} attempts.")
    return False

def display_title():
    """Display the AKPS title banner"""
    title = """
    ╔═══════════════════════════════════════╗
    ║                                       ║
    ║     █████╗ ██╗  ██╗██████╗ ███████╗   ║
    ║    ██╔══██╗██║ ██╔╝██╔══██╗██╔════╝   ║
    ║    ███████║█████╔╝ ██████╔╝███████╗   ║
    ║    ██╔══██║██╔═██╗ ██╔═══╝ ╚════██║   ║
    ║    ██║  ██║██║  ██╗██║     ███████║   ║
    ║    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝   ║
    ║                                       ║
    ╚═══════════════════════════════════════╝
    """
    print(title)
    print("=" * 43)
    print()

# --- Main Loop ---
display_title()
check_for_update()
delay_seconds = int(input("Enter analysis time in seconds: "))
log(f"Using {delay_seconds} seconds for image analysis")

while True:
    try:
        if exiting:
            safe_sleep(3)
            log("Script ended.")
            sys.exit(0)

        if pending_delay_change != 0:
            delay_seconds = max(1, delay_seconds + pending_delay_change)
            log(f"Updated delay_seconds to {delay_seconds} seconds")
            pending_delay_change = 0

        if paused:
            safe_sleep(0.5)
            continue

        log("Waiting for button1.png indefinitely...")
        while not find_and_click('button1.png', threshold=0.7):
            if paused or exiting:
                safe_sleep(0.5)
                continue

        safe_sleep(1)

        for i in range(5):
            if paused or exiting:
                safe_sleep(0.5)
                continue
            pyautogui.scroll(-300)
            log(f"Manual scroll {i + 1}/5")
            safe_sleep(0.3)

        for i in range(delay_seconds, 0, -1):
            log(f"Submitting in {i} seconds...")
            safe_sleep(1)

        log("Looking for button2.png (3 second timeout)...")
        found_button2 = False
        timeout_start = time.time()
        while time.time() - timeout_start < 3:
            if paused or exiting:
                safe_sleep(0.5)
                continue
            if find_and_click('button2.png', threshold=0.7):
                found_button2 = True
                break
            safe_sleep(0.3)

        if not found_button2:
            log("button2.png not found within 3 seconds. Restarting loop...")
            continue

        safe_sleep(2)

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

