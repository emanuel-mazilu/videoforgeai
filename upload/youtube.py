import time
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import subprocess
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class UploadWorker(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool)

    def __init__(self, project):
        super().__init__()
        self.project = project

    def wait_for_element(self, driver, by, value, timeout=30, retries=3):
        """Wait for element with retries"""
        for attempt in range(retries):
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                return element
            except:
                print(f"Attempt {attempt + 1} failed to find element {value}")
                if attempt < retries - 1:
                    driver.refresh()
                    time.sleep(5)
        return None

    def find_upload_button(self, driver):
        """Try multiple methods to find the upload button"""
        selectors = [
            (By.XPATH, '//*[@id="upload-icon"]'),
            (By.CSS_SELECTOR, "#upload-icon"),
            (By.XPATH, '//ytcp-icon-button[@id="upload-icon"]'),
            (By.XPATH, '//div[@id="upload-icon"]'),
            (By.XPATH, '//button[contains(@aria-label, "Upload")]'),
            (By.XPATH, '//ytcp-button[contains(@aria-label, "Upload")]'),
            (By.CSS_SELECTOR, 'ytcp-button[id="upload-icon"]'),
            (By.CSS_SELECTOR, "#create-icon"),  # Fallback to create button
        ]

        for by, selector in selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                if element and element.is_displayed():
                    return element
            except:
                continue
        return None

    def handle_file_upload(self, driver, video_path: str) -> bool:
        """Handle file upload with improved error handling"""
        try:
            # Wait for upload dialog to be fully loaded
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "ytcp-uploads-dialog"))
            )
            time.sleep(2)  # Additional wait for dialog animation

            # First attempt - Direct file input
            try:
                file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                if file_inputs:
                    file_inputs[0].send_keys(str(video_path))
                    print("Upload succeeded using direct file input")
                    
                    # Wait for upload progress indicator
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR, 
                            "ytcp-upload-progress-bar, ytcp-video-upload-progress"
                        ))
                    )
                    return True
            except Exception as e:
                print(f"Direct file input failed: {e}")

            # Second attempt - Create and use temporary file input
            try:
                js_code = """
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.style.display = 'none';
                    document.body.appendChild(input);
                    return input;
                """
                file_input = driver.execute_script(js_code)
                driver.execute_script("arguments[0].style.display = 'block';", file_input)
                file_input.send_keys(str(video_path))
                
                # Wait for upload progress indicator
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "ytcp-upload-progress-bar, ytcp-video-upload-progress"
                    ))
                )
                
                driver.execute_script("arguments[0].remove();", file_input)
                print("Upload succeeded using temporary file input")
                return True
                
            except Exception as e:
                print(f"Temporary file input failed: {e}")

            # Third attempt - Click select files button and use active element
            try:
                select_files_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "#select-files-button"
                    ))
                )
                select_files_button.click()
                time.sleep(2)
                
                # Create a new file input and trigger it
                js_code = """
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.style.opacity = '0';
                    input.style.position = 'fixed';
                    input.style.left = '0';
                    input.style.top = '0';
                    document.body.appendChild(input);
                    return input;
                """
                file_input = driver.execute_script(js_code)
                file_input.send_keys(str(video_path))
                
                # Wait for upload progress indicator
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "ytcp-upload-progress-bar, ytcp-video-upload-progress"
                    ))
                )
                
                print("Upload succeeded using select files button")
                return True
                
            except Exception as e:
                print(f"Select files button method failed: {e}")

            return False

        except Exception as e:
            print(f"Upload handler error: {e}")
            return False

    def set_title_with_verification(self, driver, title):
        """Set title with improved clearing and verification"""
        try:
            # Wait for title container and any auto-population
            time.sleep(8)
            
            # Find title input using multiple selectors
            title_input = None
            selectors = [
                "ytcp-social-suggestion-input.style-scope.ytcp-video-metadata-editor-basics",
                "#textbox",
                "//div[@id='textbox']"
            ]
            
            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        title_input = driver.find_element(By.XPATH, selector)
                    else:
                        title_input = driver.find_element(By.CSS_SELECTOR, selector)
                    if title_input:
                        break
                except:
                    continue
            
            if not title_input:
                print("Could not find title input")
                return False
                
            # Clear title using JavaScript first
            driver.execute_script("arguments[0].innerHTML = '';", title_input)
            time.sleep(1)
            
            # Click to focus
            title_input.click()
            time.sleep(1)
            
            # Clear using keyboard shortcuts
            active_element = driver.switch_to.active_element
            active_element.send_keys(Keys.CONTROL + "a")
            time.sleep(0.5)
            active_element.send_keys(Keys.DELETE)
            time.sleep(0.5)
            active_element.send_keys(Keys.BACKSPACE)  # Extra clear
            time.sleep(1)
            
            # Verify field is empty
            current_text = title_input.get_attribute('innerHTML').strip()
            if current_text:
                print(f"Failed to clear title field, current text: {current_text}")
                # Try one more time to clear
                driver.execute_script("arguments[0].innerHTML = '';", title_input)
                time.sleep(1)
            
            # Set new title
            active_element.send_keys(title)
            time.sleep(2)
            
            # Click outside to ensure title is set
            driver.execute_script("""
                document.querySelector('ytcp-video-metadata-editor-basics').click();
            """)
            time.sleep(1)
            
            # Verify title was set correctly
            current_title = title_input.get_attribute('innerHTML').strip()
            if current_title != title:
                print(f"Title verification failed. Expected: {title}, Got: {current_title}")
                return False
                
            print("Successfully set and verified title")
            return True
            
        except Exception as e:
            print(f"Error in set_title_with_verification: {e}")
            return False

    def run(self):
        driver = None
        try:
            # Get metadata
            video_path = Path(self.project.output_path).absolute()
            title = sanitize_text(self.project.title)
            description = sanitize_text(
                self.project.metadata.get("youtube_description", "")
            )

            # Kill any existing Chrome processes
            try:
                subprocess.run(["pkill", "Google Chrome"])
                time.sleep(2)
            except:
                pass

            # Initialize Chrome
            self.progress.emit("Initializing browser...", 10)
            options = uc.ChromeOptions()

            # Use default Chrome profile
            profile_path = str(
                Path.home() / "Library/Application Support/Google/Chrome/Default"
            )
            options.add_argument(
                f"--user-data-dir={str(Path.home() / 'Library/Application Support/Google/Chrome')}"
            )
            options.add_argument("--profile-directory=Default")
            options.add_argument("--no-sandbox")
            options.add_argument("--start-maximized")

            print(f"Using Chrome profile: {profile_path}")
            driver = uc.Chrome(
                options=options,
                version_main=None,  # Auto-detect Chrome version
                use_subprocess=True,
            )

            # Navigate to YouTube Studio with retries
            self.progress.emit("Navigating to YouTube Studio...", 20)
            max_retries = 3
            success = False

            for attempt in range(max_retries):
                try:
                    print(f"Navigation attempt {attempt + 1}")
                    driver.get("https://studio.youtube.com")
                    time.sleep(5)

                    # Try to find upload button with new method
                    upload_button = self.find_upload_button(driver)

                    if upload_button:
                        print("Found upload button")
                        success = True
                        break
                    else:
                        # Try alternative URL
                        print("Trying direct channel URL...")
                        driver.get("https://studio.youtube.com/channel/UC")
                        time.sleep(5)

                        upload_button = self.find_upload_button(driver)
                        if upload_button:
                            print("Found upload button on channel page")
                            success = True
                            break

                except Exception as e:
                    print(f"Navigation error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(3)
                    else:
                        raise Exception("Could not navigate to YouTube Studio")

            if not success:
                raise Exception("Could not find upload button")

            # Start upload process
            self.progress.emit("Starting upload process...", 30)
            
            # Wait for any overlays to disappear
            time.sleep(2)
            
            # Click create button
            create_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#create-icon"))
            )
            driver.execute_script("arguments[0].click();", create_button)
            time.sleep(2)
            
            # Click upload option
            upload_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "tp-yt-paper-item#text-item-0"))
            )
            driver.execute_script("arguments[0].click();", upload_option)
            time.sleep(2)

            # Handle file upload with improved method
            video_path = Path(self.project.output_path).resolve()
            if not self.handle_file_upload(driver, str(video_path)):
                raise Exception("Failed to upload file")

            # Wait for upload dialog to be ready
            time.sleep(8)  # Longer wait after upload

            # Set title with improved method
            self.progress.emit("Setting video title...", 60)
            if not self.set_title_with_verification(driver, title):
                print("Warning: Could not verify title was set correctly")

            # Set description with improved handling
            self.progress.emit("Setting video description...", 70)
            try:
                # Wait for description container
                description_container = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "div[aria-label='Tell viewers about your video (type @ to mention a channel)']"
                    ))
                )
                
                # Click to focus
                description_container.click()
                time.sleep(1)
                
                # Clear and set description
                active_element = driver.switch_to.active_element
                active_element.send_keys(Keys.CONTROL + "a")
                active_element.send_keys(Keys.DELETE)
                time.sleep(1)
                active_element.send_keys(description)
                
                print("Successfully set description")
                time.sleep(2)
            except Exception as e:
                print(f"Error setting description: {e}")

            # Click through next buttons
            self.progress.emit("Configuring upload settings...", 80)
            for _ in range(3):
                try:
                    next_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "next-button"))
                    )
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(2)
                except Exception as e:
                    print(f"Error clicking next button: {e}")
                    # Try alternative method
                    try:
                        driver.execute_script(
                            'document.querySelector("#next-button").click()'
                        )
                        time.sleep(2)
                    except:
                        pass

            # Set visibility
            self.progress.emit("Setting video visibility...", 90)
            time.sleep(2)

            try:
                # Wait for visibility section and select unlisted
                unlisted_radio = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "UNLISTED"))
                )
                driver.execute_script("arguments[0].click();", unlisted_radio)
            except:
                try:
                    # Alternative method using JavaScript
                    driver.execute_script(
                        'document.querySelector(\'tp-yt-paper-radio-button[name="UNLISTED"]\').click()'
                    )
                except Exception as e:
                    print(f"Could not set video visibility to unlisted: {e}")

            time.sleep(2)

            # Click done
            self.progress.emit("Finishing upload...", 95)
            try:
                done_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "done-button"))
                )
                driver.execute_script("arguments[0].click();", done_button)
            except:
                try:
                    # Alternative method
                    driver.execute_script(
                        'document.querySelector("#done-button").click()'
                    )
                except Exception as e:
                    print(f"Error clicking done button: {e}")

            time.sleep(20)

            driver.quit()
            self.finished.emit(True)

        except Exception as e:
            print(f"Upload error: {str(e)}")
            if driver:
                try:
                    driver.save_screenshot("error_screenshot.png")
                    print("Error screenshot saved")
                    driver.quit()
                except:
                    pass
            self.finished.emit(False)


def sanitize_text(text: str) -> str:
    """Sanitize text to only use BMP characters"""
    return "".join(char for char in text if ord(char) < 0xFFFF)


__all__ = ["UploadWorker"]
