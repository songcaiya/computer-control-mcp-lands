#!/usr/bin/env python3
"""
Computer Control MCP - Core Implementation
A compact ModelContextProtocol server that provides computer control capabilities
using PyAutoGUI for mouse/keyboard control.
"""

import shutil
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
from io import BytesIO
import re
import asyncio
import uuid
import datetime
from pathlib import Path
import tempfile

# --- Auto-install dependencies if needed ---
import pyautogui
from mcp.server.fastmcp import FastMCP, Image
import pygetwindow as gw
from fuzzywuzzy import fuzz, process

from rapidocr_onnxruntime import RapidOCR
import cv2

# Windows API imports for capturing inactive windows
if os.name == "nt":  # Windows
    import ctypes
from ctypes import wintypes
import numpy as np
from PIL import Image as PILImage

DEBUG = True  # Set to False in production
RELOAD_ENABLED = True  # Set to False to disable auto-reload

# Create FastMCP server instance at module level
mcp = FastMCP("ComputerControlMCP")


def log(message: str) -> None:
    """Log a message to stderr."""
    print(f"STDOUT: {message}", file=sys.stderr)


# Try to import win32 libraries for enhanced Windows support
try:
    import win32gui
    import win32ui
    import win32con
    import win32api
    WIN32_AVAILABLE = True
    log("Win32 libraries available for enhanced Windows API support")
except ImportError:
    WIN32_AVAILABLE = False
    log("Win32 libraries not available, using basic ctypes approach")


def get_downloads_dir() -> Path:
    """Get the OS downloads directory."""
    if os.name == "nt":  # Windows
        import winreg

        sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            downloads_dir = winreg.QueryValueEx(key, downloads_guid)[0]
        return Path(downloads_dir)
    else:  # macOS, Linux, etc.
        return Path.home() / "Downloads"


def save_image_to_downloads(
    image, prefix: str = "screenshot", directory: Path = None
) -> Tuple[str, bytes]:
    """Save an image to the downloads directory and return its absolute path.

    Args:
        image: Either a PIL Image object or MCP Image object
        prefix: Prefix for the filename (default: 'screenshot')
        directory: Optional directory to save the image to

    Returns:
        Tuple of (absolute_path, image_data_bytes)
    """
    # Create a unique filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{prefix}_{timestamp}_{unique_id}.png"

    # Get downloads directory
    downloads_dir = directory or get_downloads_dir()
    filepath = downloads_dir / filename

    # Handle different image types
    if hasattr(image, "save"):  # PIL Image
        image.save(filepath)
        # Also get the bytes for returning
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_bytes = img_byte_arr.getvalue()
    elif hasattr(image, "data"):  # MCP Image
        img_bytes = image.data
        with open(filepath, "wb") as f:
            f.write(img_bytes)
    else:
        raise TypeError("Unsupported image type")

    log(f"Saved image to {filepath}")
    return str(filepath.absolute()), img_bytes


def _capture_window_without_activation(window) -> Optional[PILImage.Image]:
    """Capture a window screenshot without activating it using Windows API.
    
    Args:
        window: PyGetWindow window object
        
    Returns:
        PIL Image object or None if capture fails
    """
    if os.name != "nt":  # Only works on Windows
        return None
        
    try:
        # Get window handle
        hwnd = window._hWnd
        log(f"Window handle: {hwnd}")
        log(f"Window title: {window.title}")
        log(f"Window position: ({window.left}, {window.top})")
        log(f"Window minimized: {window.isMinimized}")
        
        # Verify window handle is valid
        if not ctypes.windll.user32.IsWindow(hwnd):
            log("Invalid window handle")
            return None
        
        # Check if window is minimized
        if window.isMinimized or window.left == -32000:
            log("Window is minimized, attempting to restore temporarily")
            # Get current window state
            placement = ctypes.create_string_buffer(44)  # WINDOWPLACEMENT size
            ctypes.windll.user32.GetWindowPlacement(hwnd, placement)
            
            # Restore window without activating it
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            import time
            time.sleep(0.1)  # Give it a moment to restore
            
            # Get updated dimensions after restore
            rect = ctypes.create_string_buffer(16)  # RECT size
            ctypes.windll.user32.GetWindowRect(hwnd, rect)
            left, top, right, bottom = ctypes.cast(rect, ctypes.POINTER(ctypes.c_int * 4)).contents
            width = right - left
            height = bottom - top
            log(f"Restored window dimensions: {width}x{height}")
        else:
            # Get window dimensions
            width = window.width
            height = window.height
        
        log(f"Using window dimensions: {width}x{height}")
        
        if width <= 0 or height <= 0:
            log(f"Invalid window dimensions: {width}x{height}")
            return None
        
        # Get device contexts
        hwndDC = ctypes.windll.user32.GetWindowDC(hwnd)
        if not hwndDC:
            log("Failed to get window DC")
            return None
            
        mfcDC = ctypes.windll.gdi32.CreateCompatibleDC(hwndDC)
        if not mfcDC:
            log("Failed to create compatible DC")
            ctypes.windll.user32.ReleaseDC(hwnd, hwndDC)
            return None
        
        # Create bitmap
        saveBitMap = ctypes.windll.gdi32.CreateCompatibleBitmap(hwndDC, width, height)
        if not saveBitMap:
            log("Failed to create compatible bitmap")
            ctypes.windll.gdi32.DeleteDC(mfcDC)
            ctypes.windll.user32.ReleaseDC(hwnd, hwndDC)
            return None
            
        # Select bitmap into DC
        old_bitmap = ctypes.windll.gdi32.SelectObject(mfcDC, saveBitMap)
        
        # Try PrintWindow first (works for most windows)
        result = ctypes.windll.user32.PrintWindow(hwnd, mfcDC, 2)  # PW_CLIENTONLY = 2
        
        if not result:
            log("PrintWindow failed, trying with PW_RENDERFULLCONTENT")
            result = ctypes.windll.user32.PrintWindow(hwnd, mfcDC, 3)  # PW_RENDERFULLCONTENT = 3
        
        if not result:
            log("PrintWindow failed completely, trying BitBlt")
            # Fallback to BitBlt (captures from screen)
            screenDC = ctypes.windll.user32.GetDC(0)  # Get screen DC
            result = ctypes.windll.gdi32.BitBlt(
                mfcDC, 0, 0, width, height,
                screenDC, window.left, window.top,
                0x00CC0020  # SRCCOPY
            )
            ctypes.windll.user32.ReleaseDC(0, screenDC)
        
        if result:
            log("Successfully captured window content")
            
            # Define BITMAPINFOHEADER structure
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ('biSize', ctypes.c_uint32),
                    ('biWidth', ctypes.c_int32),
                    ('biHeight', ctypes.c_int32),
                    ('biPlanes', ctypes.c_uint16),
                    ('biBitCount', ctypes.c_uint16),
                    ('biCompression', ctypes.c_uint32),
                    ('biSizeImage', ctypes.c_uint32),
                    ('biXPelsPerMeter', ctypes.c_int32),
                    ('biYPelsPerMeter', ctypes.c_int32),
                    ('biClrUsed', ctypes.c_uint32),
                    ('biClrImportant', ctypes.c_uint32)
                ]
            
            # Create BITMAPINFOHEADER
            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # Negative for top-down bitmap
            bmi.biPlanes = 1
            bmi.biBitCount = 32  # 32 bits per pixel (BGRA)
            bmi.biCompression = 0  # BI_RGB
            
            # Create buffer for bitmap data
            buffer_size = width * height * 4  # 4 bytes per pixel
            buffer = (ctypes.c_ubyte * buffer_size)()
            
            # Get bitmap bits
            lines_copied = ctypes.windll.gdi32.GetDIBits(
                mfcDC, saveBitMap, 0, height, buffer, ctypes.byref(bmi), 0  # DIB_RGB_COLORS
            )
            
            if lines_copied == height:
                log("Successfully retrieved bitmap data")
                
                # Convert to numpy array
                bmp_array = np.frombuffer(buffer, dtype=np.uint8)
                bmp_array = bmp_array.reshape((height, width, 4))
                
                # Convert BGRA to RGB
                rgb_array = bmp_array[:, :, [2, 1, 0]]  # BGR to RGB, ignore alpha
                
                # Create PIL Image
                image = PILImage.fromarray(rgb_array)
                
                # Clean up
                ctypes.windll.gdi32.SelectObject(mfcDC, old_bitmap)
                ctypes.windll.gdi32.DeleteObject(saveBitMap)
                ctypes.windll.gdi32.DeleteDC(mfcDC)
                ctypes.windll.user32.ReleaseDC(hwnd, hwndDC)
                
                # If window was minimized, restore it back to minimized state
                if window.isMinimized or window.left == -32000:
                    log("Restoring window back to minimized state")
                    ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
                
                log(f"Successfully captured window without activation: {window.title}")
                return image
            else:
                log(f"Failed to get bitmap bits, lines copied: {lines_copied}")
        else:
            log("Failed to capture window content with all methods")
            
    except Exception as e:
        log(f"Error capturing window without activation: {str(e)}")
        import traceback
        log(f"Stack trace: {traceback.format_exc()}")
    finally:
        # Clean up in case of error
        try:
            if 'old_bitmap' in locals():
                ctypes.windll.gdi32.SelectObject(mfcDC, old_bitmap)
            if 'saveBitMap' in locals():
                ctypes.windll.gdi32.DeleteObject(saveBitMap)
            if 'mfcDC' in locals():
                ctypes.windll.gdi32.DeleteDC(mfcDC)
            if 'hwndDC' in locals():
                ctypes.windll.user32.ReleaseDC(hwnd, hwndDC)
        except:
            pass
    
    return None


def _capture_window_with_win32(window) -> Optional[PILImage.Image]:
    """Capture a window screenshot using win32 libraries (enhanced method).
    
    Args:
        window: PyGetWindow window object
        
    Returns:
        PIL Image object or None if capture fails
    """
    if not WIN32_AVAILABLE:
        log("Win32 libraries not available")
        return None
        
    try:
        hwnd = window._hWnd
        log(f"Using win32 method for window: {window.title}")
        
        # Get window dimensions
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        log(f"Win32 window rect: ({left}, {top}, {right}, {bottom})")
        log(f"Win32 window dimensions: {width}x{height}")
        
        if width <= 0 or height <= 0:
            log(f"Invalid win32 window dimensions: {width}x{height}")
            return None
        
        # Check if window is minimized and restore temporarily
        window_placement = win32gui.GetWindowPlacement(hwnd)
        was_minimized = window_placement[1] == win32con.SW_SHOWMINIMIZED
        
        if was_minimized:
            log("Window is minimized, restoring temporarily for win32 capture")
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            import time
            time.sleep(0.2)  # Wait for restore
            
            # Get updated rect after restore
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            log(f"Updated win32 dimensions after restore: {width}x{height}")
        
        # Get device contexts
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        
        # Create bitmap
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        
        # Copy window content
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)  # PW_RENDERFULLCONTENT
        
        if not result:
            log("Win32 PrintWindow failed, trying BitBlt")
            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
        
        if result:
            # Get bitmap info
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            # Convert to PIL Image
            img = PILImage.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # Clean up
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            # Restore minimized state if needed
            if was_minimized:
                log("Restoring window back to minimized state")
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            
            log(f"Successfully captured window with win32: {window.title}")
            return img
        else:
            log("Win32 capture failed")
            
    except Exception as e:
        log(f"Error in win32 capture: {str(e)}")
        import traceback
        log(f"Win32 stack trace: {traceback.format_exc()}")
    finally:
        # Clean up in case of error
        try:
            if 'saveBitMap' in locals():
                win32gui.DeleteObject(saveBitMap.GetHandle())
            if 'saveDC' in locals():
                saveDC.DeleteDC()
            if 'mfcDC' in locals():
                mfcDC.DeleteDC()
            if 'hwndDC' in locals():
                win32gui.ReleaseDC(hwnd, hwndDC)
        except:
            pass
    
    return None


def _find_matching_window(
    windows: any,
    title_pattern: str = None,
    use_regex: bool = False,
    threshold: int = 60,
) -> Optional[Dict[str, Any]]:
    """Helper function to find a matching window based on title pattern.

    Args:
        windows: List of window dictionaries
        title_pattern: Pattern to match window title
        use_regex: If True, treat the pattern as a regex, otherwise use fuzzy matching
        threshold: Minimum score (0-100) required for a fuzzy match

    Returns:
        The best matching window or None if no match found
    """
    if not title_pattern:
        log("No title pattern provided, returning None")
        return None

    # For regex matching
    if use_regex:
        for window in windows:
            if re.search(title_pattern, window["title"], re.IGNORECASE):
                log(f"Regex match found: {window['title']}")
                return window
        return None

    # For fuzzy matching using fuzzywuzzy
    # Extract all window titles
    window_titles = [window["title"] for window in windows]

    # Use process.extractOne to find the best match
    best_match_title, score = process.extractOne(
        title_pattern, window_titles, scorer=fuzz.partial_ratio
    )
    log(f"Best fuzzy match: '{best_match_title}' with score {score}")

    # Only return if the score is above the threshold
    if score >= threshold:
        # Find the window with the matching title
        for window in windows:
            if window["title"] == best_match_title:
                return window

    return None


# --- MCP Function Handlers ---


@mcp.tool()
def tool_version() -> str:
    """Get the version of the tool."""
    return "0.2.7"


@mcp.tool()
def click_screen(x: int, y: int) -> str:
    """Click at the specified screen coordinates."""
    try:
        pyautogui.click(x=x, y=y)
        return f"Successfully clicked at coordinates ({x}, {y})"
    except Exception as e:
        return f"Error clicking at coordinates ({x}, {y}): {str(e)}"


@mcp.tool()
def get_screen_size() -> Dict[str, Any]:
    """Get the current screen resolution."""
    try:
        width, height = pyautogui.size()
        return {
            "width": width,
            "height": height,
            "message": f"Screen size: {width}x{height}",
        }
    except Exception as e:
        return {"error": str(e), "message": f"Error getting screen size: {str(e)}"}


@mcp.tool()
def type_text(text: str) -> str:
    """Type the specified text at the current cursor position."""
    try:
        pyautogui.typewrite(text)
        return f"Successfully typed text: {text}"
    except Exception as e:
        return f"Error typing text: {str(e)}"


@mcp.tool()
def take_screenshot(
    title_pattern: str = None,
    use_regex: bool = False,
    threshold: int = 60,
    with_ocr_text_and_coords: bool = False,
    scale_percent_for_ocr: int = 100,
    save_to_downloads: bool = False,
) -> Any:
    """
    Get screenshot and  OCR text with absolute coordinates (returned after adding the window offset from true (0, 0) of screen to the OCR coordinates, so clicking is on-point. Recommended to click in the middle of OCR Box) and confidence from window with the specified title pattern.
    If no title pattern is provided, get screenshot of entire screen and all text on the screen.

    Args:
        title_pattern: Pattern to match window title, if None, take screenshot of entire screen
        use_regex: If True, treat the pattern as a regex, otherwise best match with fuzzy matching
        threshold: Minimum score (0-100) required for a fuzzy match
        with_ocr_text_and_coords: If True, get OCR text with absolute coordinates from the screenshot
        scale_percent_for_ocr: Percentage to scale the image down before processing, you wont need this most of the time unless your pc is extremely old or slow
        save_to_downloads: If True, save the screenshot to the downloads directory and return the absolute path

    Returns:
        Returns a single screenshot as MCP Image object, if with_ocr_text_and_coords is True, returns a MCP Image object followed by list of UI elements as [[4 corners of box], text, confidence], "content type image not supported" means preview isnt supported but Image object is there.
    """
    try:

        all_windows = gw.getAllWindows()

        # Convert to list of dictionaries for _find_matching_window
        windows = []
        for window in all_windows:
            if window.title:  # Only include windows with titles
                windows.append(
                    {
                        "title": window.title,
                        "window_obj": window,  # Store the actual window object
                    }
                )

        log(f"Found {len(windows)} windows")
        window = _find_matching_window(windows, title_pattern, use_regex, threshold)
        window = window["window_obj"] if window else None

        # Store the currently active window

        # Take the screenshot
        if not window:
            log("No matching window found, taking screenshot of entire screen")
            screenshot = pyautogui.screenshot()
        else:
            log(f"Taking screenshot of window: {window.title}")
            
            # First try win32 enhanced method (if available)
            screenshot = None
            if WIN32_AVAILABLE:
                log("Attempting to capture window using win32 enhanced method")
                screenshot = _capture_window_with_win32(window)
            
            # If win32 failed, try basic Windows API method
            if screenshot is None and os.name == "nt":
                log("Win32 capture failed or unavailable, trying basic Windows API")
                screenshot = _capture_window_without_activation(window)
            
            # If both methods failed or not on Windows, fall back to activation method
            if screenshot is None:
                log("All non-activation methods failed or not available, falling back to activation method")
                current_active_window = gw.getActiveWindow()
                
                # Try to activate the window with error handling
                try:
                    # Check if window is still valid
                    _ = window.title
                    _ = window.isActive
                    
                    # Activate the window with retry mechanism
                    max_retries = 3
                    activation_successful = False
                    for attempt in range(max_retries):
                        try:
                            window.activate()
                            pyautogui.sleep(0.5)  # Wait for activation
                            activation_successful = True
                            break
                        except Exception as activate_error:
                            if attempt == max_retries - 1:  # Last attempt
                                log(f"Failed to activate window after {max_retries} attempts: {str(activate_error)}")
                                log("Taking screenshot of entire screen instead")
                                screenshot = pyautogui.screenshot()
                                break
                            log(f"Activation attempt {attempt + 1} failed: {str(activate_error)}")
                            pyautogui.sleep(0.5)  # Wait before retry
                    
                    if activation_successful:
                        screenshot = pyautogui.screenshot(
                            region=(window.left, window.top, window.width, window.height)
                        )
                        
                except Exception as window_error:
                    log(f"Window validation failed: {str(window_error)}")
                    log("Taking screenshot of entire screen instead")
                    screenshot = pyautogui.screenshot()
                
                # Restore the previously active window
                if current_active_window:
                    try:
                        current_active_window.activate()
                        pyautogui.sleep(0.2)  # Wait a bit to ensure previous window is restored
                    except Exception as e:
                        log(f"Error restoring previous window: {str(e)}")
            else:
                log("Successfully captured window without activation")

        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp())

        # Save screenshot and get filepath
        filepath, _ = save_image_to_downloads(
            screenshot, prefix="screenshot", directory=temp_dir
        )

        # Create Image object from filepath
        image = Image(filepath)

        if not with_ocr_text_and_coords:
            return image  # MCP Image object

        # Copy from temp to downloads
        if save_to_downloads:
            log("Copying screenshot from temp to downloads")
            shutil.copy(filepath, get_downloads_dir())

        image_path = image.path
        img = cv2.imread(image_path)

        # Lower down resolution before processing
        width = int(img.shape[1] * scale_percent_for_ocr / 100)
        height = int(img.shape[0] * scale_percent_for_ocr / 100)
        dim = (width, height)
        resized_img = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
        # save resized image to pwd
        # cv2.imwrite("resized_img.png", resized_img)
        engine = RapidOCR()

        result, elapse_list = engine(resized_img)
        boxes, txts, scores = list(zip(*result))
        boxes = [
            [[x + window.left, y + window.top] if window else [x, y] for x, y in box]
            for box in boxes
        ]
        zipped_results = list(zip(boxes, txts, scores))

        return [image, *zipped_results]

    except Exception as e:
        log(f"Error in screenshot or getting UI elements: {str(e)}")
        import traceback

        stack_trace = traceback.format_exc()
        log(f"Stack trace:\n{stack_trace}")
        return f"Error in screenshot or getting UI elements: {str(e)}\nStack trace:\n{stack_trace}"


@mcp.tool()
def move_mouse(x: int, y: int) -> str:
    """Move the mouse to the specified screen coordinates."""
    try:
        pyautogui.moveTo(x=x, y=y)
        return f"Successfully moved mouse to coordinates ({x}, {y})"
    except Exception as e:
        return f"Error moving mouse to coordinates ({x}, {y}): {str(e)}"


@mcp.tool()
async def drag_mouse(
    from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.5
) -> str:
    """
    Drag the mouse from one position to another.

    Args:
        from_x: Starting X coordinate
        from_y: Starting Y coordinate
        to_x: Ending X coordinate
        to_y: Ending Y coordinate
        duration: Duration of the drag in seconds (default: 0.5)

    Returns:
        Success or error message
    """
    try:
        # First move to the starting position
        pyautogui.moveTo(x=from_x, y=from_y)
        # Then drag to the destination
        log("starting drag")
        await asyncio.to_thread(pyautogui.dragTo, x=to_x, y=to_y, duration=duration)
        log("done drag")
        return f"Successfully dragged from ({from_x}, {from_y}) to ({to_x}, {to_y})"
    except Exception as e:
        return f"Error dragging from ({from_x}, {from_y}) to ({to_x}, {to_y}): {str(e)}"


@mcp.tool()
def press_key(key: str) -> str:
    """Press the specified keyboard key."""
    try:
        pyautogui.press(key)
        return f"Successfully pressed key: {key}"
    except Exception as e:
        return f"Error pressing key {key}: {str(e)}"


@mcp.tool()
def list_windows() -> List[Dict[str, Any]]:
    """List all open windows on the system."""
    try:
        windows = gw.getAllWindows()
        result = []
        for window in windows:
            if window.title:  # Only include windows with titles
                try:
                    # Check if window is still valid before accessing properties
                    result.append(
                        {
                            "title": window.title,
                            "left": window.left,
                            "top": window.top,
                            "width": window.width,
                            "height": window.height,
                            "is_active": window.isActive,
                            "is_visible": window.visible,
                            "is_minimized": window.isMinimized,
                            "is_maximized": window.isMaximized,
                            # Removed screenshot to fix serialization issue
                        }
                    )
                except Exception as window_error:
                    log(f"Error accessing window '{window.title}': {str(window_error)}")
                    continue
        return result
    except Exception as e:
        log(f"Error listing windows: {str(e)}")
        return [{"error": str(e)}]


@mcp.tool()
def activate_window(
    title_pattern: str, use_regex: bool = False, threshold: int = 60
) -> str:
    """
    Activate a window (bring it to the foreground) by matching its title.

    Args:
        title_pattern: Pattern to match window title
        use_regex: If True, treat the pattern as a regex, otherwise use fuzzy matching
        threshold: Minimum score (0-100) required for a fuzzy match

    Returns:
        Success or error message
    """
    try:
        # Get all windows
        all_windows = gw.getAllWindows()

        # Convert to list of dictionaries for _find_matching_window
        windows = []
        for window in all_windows:
            if window.title:  # Only include windows with titles
                windows.append(
                    {
                        "title": window.title,
                        "window_obj": window,  # Store the actual window object
                    }
                )

        # Find matching window using our improved function
        matched_window_dict = _find_matching_window(
            windows, title_pattern, use_regex, threshold
        )

        if not matched_window_dict:
            log(f"No window found matching pattern: {title_pattern}")
            return f"Error: No window found matching pattern: {title_pattern}"

        # Get the actual window object
        matched_window = matched_window_dict["window_obj"]

        # Check if window is still valid and try to activate it
        try:
            # First check if window is still accessible
            _ = matched_window.title
            _ = matched_window.isActive
            
            # Try to activate the window with retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    matched_window.activate()
                    pyautogui.sleep(0.2)  # Give time for activation
                    break
                except Exception as activate_error:
                    if attempt == max_retries - 1:  # Last attempt
                        raise activate_error
                    log(f"Activation attempt {attempt + 1} failed: {str(activate_error)}")
                    pyautogui.sleep(0.5)  # Wait before retry
            
            return f"Successfully activated window: '{matched_window.title}'"
            
        except Exception as window_error:
            error_msg = f"Cannot activate window '{matched_window_dict.get('title', 'Unknown')}': {str(window_error)}"
            log(error_msg)
            return f"Error: {error_msg}"
    except Exception as e:
        log(f"Error activating window: {str(e)}")
        return f"Error activating window: {str(e)}"


def main():
    """Main entry point for the MCP server."""
    pyautogui.FAILSAFE = True

    try:
        # Run the server
        mcp.run()

    except KeyboardInterrupt:
        log("Server shutting down...")
    except Exception as e:
        log(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
