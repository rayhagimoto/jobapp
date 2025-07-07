import os
import platform
import subprocess
import shutil
import time
import requests
from pathlib import Path
from typing import Optional, Tuple


class ChromeManager:
    """Cross-platform Chrome browser manager for remote debugging"""
    
    def __init__(self, debug_port: int = 9222):
        self.debug_port = debug_port
        self.debug_data_dir = None
        self.chrome_process = None
        self.system = platform.system().lower()
        self.using_actual_profile = False  # Track if we're using actual profile
        
    def find_chrome_executable(self, custom_path: Optional[str] = None) -> Optional[str]:
        """
        Find Chrome executable across different platforms
        
        Args:
            custom_path: User-specified full path to Chrome executable (takes priority)
            
        Returns:
            Path to Chrome executable or None if not found
        """
        # Priority 1: User-specified path (highest priority)
        if custom_path:
            if os.path.exists(custom_path):
                print(f"[INFO] Using user-specified Chrome: {custom_path}")
                return custom_path
            else:
                print(f"[ERROR] User-specified Chrome path does not exist: {custom_path}")
                return None
        
        # Priority 2: Auto-detection based on platform
        print(f"[INFO] Auto-detecting Chrome on {self.system}...")
        
        if self.system == "linux":
            # Try common Linux Chrome locations
            candidates = [
                "google-chrome-stable",
                "google-chrome", 
                "chromium-browser",
                "chromium",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/snap/bin/chromium",
                "/opt/google/chrome/chrome",  # Some distributions
                "/usr/local/bin/google-chrome"
            ]
        elif self.system == "darwin":  # macOS
            candidates = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"
            ]
        elif self.system == "windows":
            candidates = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
                os.path.expanduser(r"~\AppData\Local\Chromium\Application\chrome.exe")
            ]
        else:
            print(f"[WARNING] Unsupported platform: {self.system}")
            return None
            
        for candidate in candidates:
            if shutil.which(candidate) or os.path.exists(candidate):
                print(f"[INFO] Found Chrome at: {candidate}")
                return candidate
                
        return None
    
    def find_chrome_profile_dir(self, custom_profile_dir: Optional[str] = None) -> Optional[str]:
        """
        Find Chrome profile directory across different platforms
        
        Args:
            custom_profile_dir: User-specified full path to Chrome profile directory (takes priority)
            
        Returns:
            Path to Chrome profile directory or None if not found
        """
        # Priority 1: User-specified path (highest priority)
        if custom_profile_dir:
            expanded_path = os.path.expanduser(custom_profile_dir)
            if os.path.exists(expanded_path):
                print(f"[INFO] Using user-specified Chrome profile: {expanded_path}")
                return expanded_path
            else:
                print(f"[ERROR] User-specified Chrome profile path does not exist: {expanded_path}")
                return None
        
        # Priority 2: Auto-detection based on platform
        print(f"[INFO] Auto-detecting Chrome profile on {self.system}...")
        
        if self.system == "linux":
            candidates = [
                "~/.config/google-chrome",
                "~/.config/chromium",
                "~/snap/chromium/common/chromium"  # Snap package
            ]
        elif self.system == "darwin":  # macOS
            candidates = [
                "~/Library/Application Support/Google/Chrome",
                "~/Library/Application Support/Chromium"
            ]
        elif self.system == "windows":
            candidates = [
                r"~\AppData\Local\Google\Chrome\User Data",
                r"~\AppData\Local\Chromium\User Data"
            ]
        else:
            print(f"[WARNING] Unsupported platform: {self.system}")
            return None
        
        for candidate in candidates:
            profile_dir = os.path.expanduser(candidate)
            if os.path.exists(profile_dir):
                print(f"[INFO] Found Chrome profile at: {profile_dir}")
                return profile_dir
                
        return None
    
    def setup_debug_profile(self, original_profile_path: str) -> str:
        """Create a debug profile directory with copied session data"""
        if self.system == "windows":
            debug_dir = os.path.join(os.environ.get("TEMP", "C:\\temp"), "chrome-debug-profile")
        else:
            debug_dir = "/tmp/chrome-debug-profile"
            
        # Clean up existing debug directory
        if os.path.exists(debug_dir):
            try:
                shutil.rmtree(debug_dir)
            except Exception:
                pass  # Ignore errors when cleaning up
        os.makedirs(debug_dir, exist_ok=True)
        
        # Copy essential profile data
        try:
            # Determine if we're given a full profile path or just the User Data directory
            if os.path.basename(original_profile_path) in ["Default", "Profile 1", "Profile 2", "Profile 3", "Profile 4", "Profile 5"]:
                # We were given a specific profile directory
                source_profile = original_profile_path
                profile_name = os.path.basename(original_profile_path)
            else:
                # We were given the User Data directory, use Default
                source_profile = os.path.join(original_profile_path, "Default")
                profile_name = "Default"
                
            if os.path.exists(source_profile):
                print(f"[INFO] Copying essential Chrome profile data from {source_profile}...")
                dest_profile = os.path.join(debug_dir, profile_name)
                os.makedirs(dest_profile, exist_ok=True)
                
                # Copy only essential files for login sessions and performance
                essential_files = [
                    "Cookies", "Login Data", "Login Data For Account", 
                    "Web Data", "Preferences", "Secure Preferences",
                    "Network Action Predictor", "Top Sites", "History"
                ]
                
                essential_dirs = [
                    "Local Storage", "Session Storage", "IndexedDB"
                ]
                
                try:
                    # Copy essential files
                    for file_name in essential_files:
                        src_file = os.path.join(source_profile, file_name)
                        if os.path.exists(src_file):
                            try:
                                shutil.copy2(src_file, dest_profile)
                            except Exception:
                                continue  # Skip files that can't be copied
                    
                    # Copy essential directories
                    for dir_name in essential_dirs:
                        src_dir = os.path.join(source_profile, dir_name)
                        dst_dir = os.path.join(dest_profile, dir_name)
                        if os.path.exists(src_dir):
                            try:
                                shutil.copytree(src_dir, dst_dir)
                            except Exception:
                                continue  # Skip directories that can't be copied
                                
                except Exception as copy_error:
                    print(f"[WARNING] Error copying profile: {copy_error}")
                    print("[INFO] Chrome will start with a fresh profile")
                
                # Copy Local State file from the User Data directory
                if profile_name != "Default":
                    # If we're using a non-default profile, Local State is in the parent directory
                    user_data_dir = os.path.dirname(source_profile)
                else:
                    # If we're using Default, original_profile_path might be the User Data dir
                    user_data_dir = original_profile_path if os.path.basename(original_profile_path) != "Default" else os.path.dirname(original_profile_path)
                    
                local_state = os.path.join(user_data_dir, "Local State")
                if os.path.exists(local_state):
                    shutil.copy2(local_state, debug_dir)
            else:
                print(f"[WARNING] Profile directory not found: {source_profile}")
                
        except Exception as e:
            print(f"[WARNING] Could not copy all profile data: {e}")
            
        self.debug_data_dir = debug_dir
        return debug_dir
    
    def setup_full_profile_copy(self, original_profile_path: str) -> str:
        """Create a debug profile directory with a full copy of the profile"""
        if self.system == "windows":
            debug_dir = os.path.join(os.environ.get("TEMP", "C:\\temp"), "chrome-full-profile")
        else:
            debug_dir = "/tmp/chrome-full-profile"
            
        # Clean up existing debug directory
        if os.path.exists(debug_dir):
            try:
                shutil.rmtree(debug_dir)
            except Exception:
                pass  # Ignore errors when cleaning up
        os.makedirs(debug_dir, exist_ok=True)
        
        # Copy the entire profile directory
        try:
            print(f"[INFO] Copying full Chrome profile from {original_profile_path}...")
            
            # Determine source directory structure
            if os.path.basename(original_profile_path) in ["Default", "Profile 1", "Profile 2", "Profile 3", "Profile 4", "Profile 5"]:
                # We were given a specific profile directory
                source_profile = original_profile_path
                profile_name = os.path.basename(original_profile_path)
                user_data_dir = os.path.dirname(original_profile_path)
            else:
                # We were given the User Data directory, use Default
                source_profile = os.path.join(original_profile_path, "Default")
                profile_name = "Default"
                user_data_dir = original_profile_path
                
            if os.path.exists(source_profile):
                dest_profile = os.path.join(debug_dir, profile_name)
                
                # Copy the entire profile directory
                try:
                    def ignore_errors(src, names):
                        # Return empty list to copy all files, but handle errors gracefully
                        return []
                    
                    shutil.copytree(source_profile, dest_profile, ignore=ignore_errors)
                    print(f"[INFO] Copied profile to: {dest_profile}")
                except Exception as copy_error:
                    print(f"[WARNING] Error copying full profile: {copy_error}")
                    print("[INFO] Chrome will start with a minimal profile")
                    os.makedirs(dest_profile, exist_ok=True)
                
                # Copy Local State file from the User Data directory
                local_state = os.path.join(user_data_dir, "Local State")
                if os.path.exists(local_state):
                    try:
                        shutil.copy2(local_state, debug_dir)
                        print("[INFO] Copied Local State file")
                    except Exception:
                        print("[WARNING] Could not copy Local State file")
            else:
                print(f"[WARNING] Profile directory not found: {source_profile}")
                
        except Exception as e:
            print(f"[WARNING] Could not copy profile data: {e}")
            
        self.debug_data_dir = debug_dir
        return debug_dir
    
    def start_chrome_debug(self, chrome_executable: str, profile_dir: str, 
                          open_linkedin: bool = True, use_actual_profile: bool = True) -> subprocess.Popen:
        """Start Chrome with remote debugging enabled"""
        
        if use_actual_profile:
            # Copy the entire actual profile to a debug directory
            data_dir = self.setup_full_profile_copy(profile_dir)
            print(f"[INFO] Using full copy of Chrome profile: {data_dir}")
            self.using_actual_profile = True
        else:
            # Use the old behavior of copying only essential files
            data_dir = self.setup_debug_profile(profile_dir)
            print(f"[INFO] Using essential files copy: {data_dir}")
            self.using_actual_profile = False
        
        chrome_args = [
            chrome_executable,
            f"--remote-debugging-port={self.debug_port}",
            f"--user-data-dir={data_dir}",
            "--disable-web-security",  # Allow cross-origin requests for debugging
            "--disable-features=VizDisplayCompositor",  # Improve stability
            "--no-first-run",  # Skip first run setup
            "--no-default-browser-check",  # Skip default browser check
            "--window-size=1920,1080",  # Set viewport size to 1920x1080
            "--start-maximized",  # Ensure window is maximized
        ]
        
        if open_linkedin:
            chrome_args.append("https://www.linkedin.com")
            
        print(f"[INFO] Starting Chrome with remote debugging on port {self.debug_port}...")
        
        try:
            if self.system == "windows":
                # On Windows, use CREATE_NEW_PROCESS_GROUP to avoid inheriting console
                self.chrome_process = subprocess.Popen(
                    chrome_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                self.chrome_process = subprocess.Popen(
                    chrome_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
            return self.chrome_process
            
        except Exception as e:
            print(f"[ERROR] Failed to start Chrome: {e}")
            raise
    
    def wait_for_debug_ready(self, timeout: int = 20) -> bool:
        """Wait for Chrome remote debugging to become available"""
        print("[INFO] Waiting for Chrome to initialize...")
        
        for i in range(timeout):
            try:
                response = requests.get(f"http://localhost:{self.debug_port}/json", 
                                      timeout=2)
                if response.status_code == 200:
                    print("[SUCCESS] Chrome remote debugging is working!")
                    return True
            except requests.RequestException:
                pass
                
            print(f"  Attempt {i+1}/{timeout}: Waiting for Chrome...")
            time.sleep(1)
            
        print(f"[ERROR] Chrome remote debugging not responding after {timeout} seconds")
        return False
    
    def stop_chrome(self):
        """Stop the Chrome debug process"""
        if self.chrome_process:
            try:
                self.chrome_process.terminate()
                self.chrome_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.chrome_process.kill()
            except Exception as e:
                print(f"[WARNING] Could not stop Chrome cleanly: {e}")
    
    def cleanup(self):
        """Clean up debug profile directory (only if using temporary copy)"""
        if not self.using_actual_profile and self.debug_data_dir and os.path.exists(self.debug_data_dir):
            try:
                print(f"[INFO] Cleaning up temporary debug directory: {self.debug_data_dir}")
                shutil.rmtree(self.debug_data_dir)
            except Exception as e:
                print(f"[WARNING] Could not clean up debug directory: {e}")
        elif self.using_actual_profile:
            print("[INFO] Using actual profile - no cleanup needed")


def start_chrome_for_scraping(custom_chrome_path: Optional[str] = None,
                            custom_profile_dir: Optional[str] = None,
                            debug_port: int = 9222,
                            use_actual_profile: bool = True) -> Tuple[ChromeManager, bool]:
    """
    Convenience function to start Chrome for scraping
    
    Args:
        custom_chrome_path: Optional path to Chrome executable
        custom_profile_dir: Optional path to Chrome profile directory
        debug_port: Port for remote debugging (default: 9222)
        use_actual_profile: If True, use the actual profile directory directly.
                           If False, copy essential files to a temporary directory.
        
    Returns:
        Tuple of (ChromeManager instance, success boolean)
    """
    manager = ChromeManager(debug_port)
    
    # Find Chrome executable
    chrome_exe = manager.find_chrome_executable(custom_chrome_path)
    if not chrome_exe:
        print("[ERROR] Could not find Chrome executable.")
        print("Please install Google Chrome or specify the path with --chrome-path")
        return manager, False
        
    print(f"[INFO] Found Chrome at: {chrome_exe}")
    
    # Find Chrome profile
    profile_dir = manager.find_chrome_profile_dir(custom_profile_dir)
    if not profile_dir:
        print("[ERROR] Could not find Chrome profile directory.")
        print("Please specify the profile directory with --chrome-profile")
        return manager, False
        
    print(f"[INFO] Using Chrome profile: {profile_dir}")
    
    # Start debug session (user will manually ensure no Chrome is running)
    manager.start_chrome_debug(chrome_exe, profile_dir, use_actual_profile=use_actual_profile)
    
    # Wait for Chrome to be ready
    if manager.wait_for_debug_ready():
        print(f"[INFO] Chrome is ready for scraping!")
        print(f"[INFO] Remote debugging available at: http://localhost:{debug_port}")
        return manager, True
    else:
        manager.stop_chrome()
        return manager, False 