"""
TimeBound - Academic Task Manager with App Blocking
An innovative app for managing academic tasks with daily breakdown,
notifications, and app blocking during focus time.

Requirements:
pip install kivy plyer android (kivy==2.2.1, plyer==2.1.0)

For Desktop: pip install psutil
For APK building: buildozer
pip install buildozer cython apache-libcloud
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.togglebutton import ToggleButton
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.uix.widget import Widget

import json
import os
import platform
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
import math

# Try to import plyer for notifications (will fail gracefully if not available)
try:
    from plyer import notification, vibrator
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("Warning: plyer not installed. Notifications will be limited.")

# Try to import Google's Gemini SDK (optional)
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("Warning: google-generativeai not installed. Gemini API not available.")

try:
    import certifi
    CERTIFI_AVAILABLE = True
except ImportError:
    certifi = None
    CERTIFI_AVAILABLE = False
    print("Warning: certifi not installed. HTTPS certificate handling may be limited.")

# Try to import Pyjnius for Android (optional)
try:
    from jnius import autoclass, cast, PythonJavaClass, java_method
    PYJNIUS_AVAILABLE = True
    PLATFORM = 'android'
    print("[AppBlocker] Android detected - using OS-level app blocking")
except (ImportError, Exception):
    PYJNIUS_AVAILABLE = False
    PLATFORM = platform.system().lower()
    if PLATFORM == 'windows':
        print("[AppBlocker] Windows detected - using process monitoring")
    else:
        print(f"[AppBlocker] {PLATFORM.capitalize()} detected - blocking disabled on this platform")

# Try to import psutil for process management (Windows/Linux/Mac)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not installed. App blocking unavailable on desktop. (pip install psutil)")

# Set window to fullscreen mode (works on both desktop and Android)
Window.fullscreen = True

GEMINI_MODEL_NAME = "gemini-3-flash-preview"

# ─── DESIGN SYSTEM ────────────────────────────────────────────────────────────
# Deep Space Dark Theme — elegant, focused, premium
BG_BASE       = (0.055, 0.059, 0.078, 1)   # #0E0F14 - near-black base
BG_SURFACE    = (0.094, 0.098, 0.125, 1)   # #181820 - card surface
BG_ELEVATED   = (0.125, 0.129, 0.165, 1)   # #20212A - elevated surface
BG_BORDER     = (0.180, 0.184, 0.220, 1)   # #2E2F38 - subtle border

ACCENT_BLUE   = (0.231, 0.510, 1.000, 1)   # #3B82FF - electric blue primary
ACCENT_VIOLET = (0.549, 0.361, 0.965, 1)   # #8C5CF6 - deep violet
ACCENT_CYAN   = (0.051, 0.820, 0.863, 1)   # #0DD1DC - teal-cyan
ACCENT_AMBER  = (1.000, 0.690, 0.200, 1)   # #FFB033 - warm amber
ACCENT_RED    = (0.980, 0.302, 0.302, 1)   # #FA4D4D - alert red
ACCENT_GREEN  = (0.196, 0.878, 0.596, 1)   # #32E098 - success green

TEXT_PRIMARY  = (0.933, 0.937, 0.961, 1)   # #EEF0F5 - main text
TEXT_SECONDARY= (0.506, 0.522, 0.600, 1)   # #818599 - muted text
TEXT_INVERSE  = (0.055, 0.059, 0.078, 1)   # dark text on light bg

# Semantic aliases
COLOR_PRIMARY    = ACCENT_BLUE
COLOR_SECONDARY  = ACCENT_VIOLET
COLOR_ACCENT     = ACCENT_CYAN
COLOR_WARNING    = ACCENT_AMBER
COLOR_INFO       = ACCENT_BLUE
COLOR_DARK       = TEXT_PRIMARY
COLOR_LIGHT      = BG_BASE

Window.clearcolor = BG_BASE


# --- HELPER WIDGETS --------------------------------------------------──────

class Card(BoxLayout):
    """A rounded card with a subtle background."""
    def __init__(self, bg=None, radius=16, border_color=None, **kwargs):
        super().__init__(**kwargs)
        self._bg = bg or BG_SURFACE
        self._radius = radius
        self._border_color = border_color
        self.bind(size=self._redraw, pos=self._redraw)

    def _redraw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._bg)
            RoundedRectangle(size=self.size, pos=self.pos, radius=[self._radius])
            if self._border_color:
                Color(*self._border_color)
                Line(
                    rounded_rectangle=(self.x, self.y, self.width, self.height, self._radius),
                    width=1.2
                )


class PillButton(Button):
    """Modern pill-shaped button."""
    def __init__(self, accent=None, text_color=None, **kwargs):
        kwargs.setdefault('background_color', (0, 0, 0, 0))
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        super().__init__(**kwargs)
        self._accent = accent or ACCENT_BLUE
        self._text_color = text_color or TEXT_INVERSE
        self.color = self._text_color
        self.bold = True
        self.bind(size=self._redraw, pos=self._redraw)

    def _redraw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._accent)
            RoundedRectangle(size=self.size, pos=self.pos, radius=[self.height / 2])


class GhostButton(Button):
    """Outlined ghost button."""
    def __init__(self, accent=None, **kwargs):
        kwargs.setdefault('background_color', (0, 0, 0, 0))
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        super().__init__(**kwargs)
        self._accent = accent or ACCENT_BLUE
        self.color = self._accent
        self.bold = True
        self.bind(size=self._redraw, pos=self._redraw)

    def _redraw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._accent[:3], 0.12)
            RoundedRectangle(size=self.size, pos=self.pos, radius=[self.height / 2])
            Color(*self._accent)
            Line(
                rounded_rectangle=(self.x + 1, self.y + 1, self.width - 2, self.height - 2, self.height / 2),
                width=1.4
            )


class Divider(Widget):
    """Thin horizontal rule."""
    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', 1)
        super().__init__(**kwargs)
        self.bind(size=self._redraw, pos=self._redraw)

    def _redraw(self, *a):
        self.canvas.clear()
        with self.canvas:
            Color(*BG_BORDER)
            Rectangle(size=self.size, pos=self.pos)


def section_label(text, color=None, size='11sp'):
    """Small all-caps section heading."""
    return Label(
        text=text.upper(),
        font_size=size,
        bold=True,
        color=color or TEXT_SECONDARY,
        size_hint_y=None,
        height=28,
        halign='left',
        valign='middle',
    )


def body_label(text, markup=False, size='13sp', color=None, **kwargs):
    return Label(
        text=text,
        markup=markup,
        font_size=size,
        color=color or TEXT_PRIMARY,
        **kwargs
    )


def styled_input(hint='', password=False, text='', multiline=False):
    inp = TextInput(
        hint_text=hint,
        text=text,
        multiline=multiline,
        password=password,
        background_normal='',
        background_active='',
        background_color=BG_ELEVATED,
        foreground_color=TEXT_PRIMARY,
        hint_text_color=(*TEXT_SECONDARY[:3], 0.7),
        cursor_color=ACCENT_BLUE,
        padding=[14, 14, 14, 14] if multiline else [14, 12, 14, 12],
        font_size='14sp',
    )
    # Draw border around it
    def redraw(*a):
        inp.canvas.before.clear()
        with inp.canvas.before:
            Color(*BG_ELEVATED)
            RoundedRectangle(size=inp.size, pos=inp.pos, radius=[12])
            Color(*BG_BORDER)
            Line(
                rounded_rectangle=(inp.x + 1, inp.y + 1, inp.width - 2, inp.height - 2, 12),
                width=1.2
            )
    inp.bind(size=redraw, pos=redraw, focus=lambda i, v: _on_focus(i, v, redraw))
    return inp


def _on_focus(inp, focused, redraw_fn):
    def _redraw(*a):
        inp.canvas.before.clear()
        with inp.canvas.before:
            Color(*BG_ELEVATED)
            RoundedRectangle(size=inp.size, pos=inp.pos, radius=[12])
            if focused:
                Color(*ACCENT_BLUE)
            else:
                Color(*BG_BORDER)
            Line(
                rounded_rectangle=(inp.x + 1, inp.y + 1, inp.width - 2, inp.height - 2, 12),
                width=1.4 if focused else 1.2
            )
    _redraw()


# ─── APP BLOCKER (Platform-Specific) ──────────────────────────────────────────

class AppBlocker:
    """Handle platform-specific app blocking and monitoring"""
    
    def __init__(self):
        self.is_active = False
        self.blocked_apps = []
        self.monitor_job = None
        self.android_activity_manager = None
        self.android_package_manager = None
        self.usage_stats_manager = None
        self.last_status = ""
        self.lock_task_active = False
        
        # Initialize Android APIs if available
        if PYJNIUS_AVAILABLE and PLATFORM == 'android':
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                self.activity = PythonActivity.mActivity
                Context = autoclass('android.content.Context')
                self.android_activity_manager = self.activity.getSystemService(Context.ACTIVITY_SERVICE)
                self.android_package_manager = self.activity.getPackageManager()
                self.usage_stats_manager = self.activity.getSystemService(Context.USAGE_STATS_SERVICE)
                print("[AppBlocker] Android APIs initialized successfully")
            except Exception as e:
                print(f"[AppBlocker] Failed to initialize Android APIs: {e}")
                self.android_activity_manager = None
                self.usage_stats_manager = None

    def _normalize_app_terms(self, blocked_apps_list):
        terms = []
        for app in blocked_apps_list:
            normalized = (app or '').strip().lower().replace(' ', '')
            if normalized:
                terms.append(normalized)
        return terms

    def _matches_blocked_app(self, package_name):
        if not package_name:
            return False
        normalized_package = package_name.lower().replace(' ', '')
        for blocked_app in self.blocked_apps:
            if blocked_app in normalized_package:
                return True
        return False

    def _android_has_usage_access(self):
        if not self.usage_stats_manager:
            return False
        try:
            System = autoclass('java.lang.System')
            UsageStatsManager = autoclass('android.app.usage.UsageStatsManager')
            now = System.currentTimeMillis()
            stats = self.usage_stats_manager.queryUsageStats(
                UsageStatsManager.INTERVAL_DAILY,
                now - (5 * 60 * 1000),
                now,
            )
            return bool(stats and len(stats) > 0)
        except Exception as e:
            print(f"[AppBlocker] Usage access check failed: {e}")
            return False

    def request_android_usage_access(self):
        if PLATFORM != 'android' or not PYJNIUS_AVAILABLE:
            return False
        try:
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
            self.activity.startActivity(intent)
            self.last_status = "Opened Usage Access settings. Enable TimeBound and return."
            return True
        except Exception as e:
            self.last_status = f"Failed to open Usage Access settings: {e}"
            print(f"[AppBlocker] {self.last_status}")
            return False

    def request_android_app_settings(self):
        if PLATFORM != 'android' or not PYJNIUS_AVAILABLE:
            return False
        try:
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            Settings = autoclass('android.provider.Settings')
            intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            intent.setData(Uri.fromParts('package', self.activity.getPackageName(), None))
            self.activity.startActivity(intent)
            self.last_status = "Opened Android app settings."
            return True
        except Exception as e:
            self.last_status = f"Failed to open app settings: {e}"
            print(f"[AppBlocker] {self.last_status}")
            return False

    def request_android_security_settings(self):
        if PLATFORM != 'android' or not PYJNIUS_AVAILABLE:
            return False
        try:
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            intent = Intent(Settings.ACTION_SECURITY_SETTINGS)
            self.activity.startActivity(intent)
            self.last_status = "Opened Android Security settings (screen pinning is usually here)."
            return True
        except Exception as e:
            self.last_status = f"Failed to open security settings: {e}"
            print(f"[AppBlocker] {self.last_status}")
            return False

    def _start_android_lock_task(self):
        if PLATFORM != 'android' or not PYJNIUS_AVAILABLE:
            return False
        try:
            self.activity.startLockTask()
            self.lock_task_active = True
            print("[AppBlocker] Lock task started")
            return True
        except Exception as e:
            self.lock_task_active = False
            print(f"[AppBlocker] Lock task start failed: {e}")
            return False

    def _stop_android_lock_task(self):
        if PLATFORM != 'android' or not PYJNIUS_AVAILABLE or not self.lock_task_active:
            return
        try:
            self.activity.stopLockTask()
            print("[AppBlocker] Lock task stopped")
        except Exception as e:
            print(f"[AppBlocker] Lock task stop failed: {e}")
        finally:
            self.lock_task_active = False

    def android_usage_ready(self):
        return PLATFORM == 'android' and PYJNIUS_AVAILABLE and self._android_has_usage_access()

    def _get_foreground_package_android(self):
        if not self.usage_stats_manager:
            return None
        try:
            System = autoclass('java.lang.System')
            UsageEventsEvent = autoclass('android.app.usage.UsageEvents$Event')
            now = System.currentTimeMillis()
            events = self.usage_stats_manager.queryEvents(now - (20 * 1000), now)
            event = UsageEventsEvent()
            latest_package = None
            while events and events.hasNextEvent():
                events.getNextEvent(event)
                if event.getEventType() == UsageEventsEvent.MOVE_TO_FOREGROUND:
                    latest_package = event.getPackageName()
            return latest_package
        except Exception as e:
            print(f"[AppBlocker] Foreground package query failed: {e}")
            return None

    def _bring_timebound_to_front(self):
        try:
            Intent = autoclass('android.content.Intent')
            launch_intent = self.android_package_manager.getLaunchIntentForPackage(
                self.activity.getPackageName()
            )
            if launch_intent is None:
                return
            launch_intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            launch_intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)
            self.activity.startActivity(launch_intent)
        except Exception as e:
            print(f"[AppBlocker] Failed to bring app to front: {e}")
    
    def start_blocking(self, blocked_apps_list):
        """Start monitoring and blocking apps"""
        if not blocked_apps_list:
            print("[AppBlocker] No apps to block")
            self.last_status = "No apps added to block list."
            return False
        
        self.blocked_apps = self._normalize_app_terms(blocked_apps_list)
        self.is_active = True
        
        if PLATFORM == 'android' and PYJNIUS_AVAILABLE:
            if not self._android_has_usage_access():
                self.is_active = False
                self.last_status = "Usage Access permission is required on Android."
                return False
            self._start_android_blocking()
            lock_task_started = self._start_android_lock_task()
            if lock_task_started:
                self.last_status = (
                    f"Android blocker started for {len(self.blocked_apps)} app(s). "
                    "Screen pinning/lock task is active."
                )
            else:
                self.last_status = (
                    f"Android blocker started for {len(self.blocked_apps)} app(s), "
                    "but screen pinning could not start."
                )
            return True
        elif PLATFORM == 'windows' and PSUTIL_AVAILABLE:
            self._start_windows_blocking()
            self.last_status = f"Desktop blocker started for {len(self.blocked_apps)} app(s)."
            return True
        else:
            print(f"[AppBlocker] Blocking not supported on {PLATFORM}")
            self.last_status = f"Blocking not supported on {PLATFORM}."
            self.is_active = False
            return False
    
    def stop_blocking(self):
        """Stop monitoring and blocking"""
        self.is_active = False
        if self.monitor_job:
            self.monitor_job.cancel()
            self.monitor_job = None
        self._stop_android_lock_task()
        self.last_status = "Blocking stopped."
        print("[AppBlocker] Blocking stopped")
    
    def _start_android_blocking(self):
        """Start Android app blocking using Pyjnius"""
        if not self.usage_stats_manager:
            print("[AppBlocker] Android UsageStatsManager not available")
            return
        
        print(f"[AppBlocker] Starting Android blocking for: {self.blocked_apps}")
        self.monitor_job = Clock.schedule_interval(self._monitor_android_apps, 1.2)
    
    def _monitor_android_apps(self, dt):
        """Monitor current foreground app and redirect back if blocked"""
        if not self.is_active or not self.usage_stats_manager:
            return
        
        try:
            package_name = self._get_foreground_package_android()
            if not package_name:
                return
            if package_name == self.activity.getPackageName():
                return
            if self._matches_blocked_app(package_name):
                self.last_status = f"Blocked app detected: {package_name}"
                print(f"[AppBlocker] {self.last_status}")
                self._bring_timebound_to_front()
        except Exception as e:
            print(f"[AppBlocker] Error monitoring Android apps: {e}")
    
    def _start_windows_blocking(self):
        """Start Windows process blocking"""
        print(f"[AppBlocker] Starting Windows blocking for: {self.blocked_apps}")
        # Schedule monitoring every 3 seconds
        self.monitor_job = Clock.schedule_interval(self._monitor_windows_processes, 3)
    
    def _monitor_windows_processes(self, dt):
        """Monitor running Windows processes and kill blocked ones"""
        if not self.is_active or not PSUTIL_AVAILABLE:
            return
        
        try:
            # Get all running processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    process_name = proc.info['name'].lower()
                    
                    # Check if this matches any blocked app
                    for blocked_app in self.blocked_apps:
                        blocked_lower = blocked_app.lower()
                        # Match by executable name (with or without .exe)
                        if blocked_lower + '.exe' == process_name or blocked_lower == process_name:
                            try:
                                proc.terminate()
                                print(f"[AppBlocker] Terminated blocked app: {proc.info['name']}")
                            except Exception as e:
                                print(f"[AppBlocker] Failed to terminate {proc.info['name']}: {e}")
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"[AppBlocker] Error monitoring Windows processes: {e}")


# ─── DATA LAYER (unchanged) ───────────────────────────────────────────────────

class TimeBoundData:
    """Handle data persistence and task calculations"""

    def __init__(self):
        self.data_file = self._resolve_data_file()
        self.tasks = []
        self.blocked_apps = []
        self.gemini_api_key = ""
        self.use_ai = False
        self.last_ai_error = ""
        self.load_data()

    def _resolve_data_file(self):
        app = App.get_running_app()
        if app and getattr(app, 'user_data_dir', None):
            data_dir = app.user_data_dir
        else:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, 'timebound_data.json')

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.tasks = data.get('tasks', [])
                    self.blocked_apps = data.get('blocked_apps', [])
                    self.gemini_api_key = data.get('gemini_api_key', '')
                    self.use_ai = data.get('use_ai', False)
            except Exception as exc:
                print(f"[DEBUG] Failed to load data from {self.data_file}: {exc}")
                self.tasks = []
                self.blocked_apps = []
                self.gemini_api_key = ""
                self.use_ai = False
        else:
            self.tasks = []
            self.blocked_apps = []
            self.gemini_api_key = ""
            self.use_ai = False

    def save_data(self):
        self.data_file = self._resolve_data_file()
        with open(self.data_file, 'w') as f:
            json.dump({
                'tasks': self.tasks,
                'blocked_apps': self.blocked_apps,
                'gemini_api_key': self.gemini_api_key,
                'use_ai': self.use_ai
            }, f, indent=2, default=str)

    def set_api_key(self, key):
        self.gemini_api_key = key.strip()
        self.save_data()

    def _extract_gemini_text(self, payload):
        candidates = payload.get('candidates') or []
        for candidate in candidates:
            content = candidate.get('content') or {}
            parts = content.get('parts') or []
            text_chunks = []
            for part in parts:
                text = part.get('text')
                if text:
                    text_chunks.append(text)
            if text_chunks:
                return "\n".join(text_chunks).strip()
        return None

    def _generate_gemini_rest(self, prompt):
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{urllib.parse.quote(GEMINI_MODEL_NAME, safe='')}:generateContent"
        )
        payload = {
            'contents': [
                {
                    'parts': [
                        {'text': prompt}
                    ]
                }
            ]
        }
        request = urllib.request.Request(
            url=f"{endpoint}?key={urllib.parse.quote(self.gemini_api_key, safe='')}",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            ssl_context = None
            if CERTIFI_AVAILABLE:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(request, timeout=30, context=ssl_context) as response:
                response_payload = json.loads(response.read().decode('utf-8'))
                return self._extract_gemini_text(response_payload)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode('utf-8', errors='replace')
            self.last_ai_error = f"HTTP {exc.code}: {error_body[:200]}"
            print(f"[DEBUG] Gemini REST HTTP error: {exc.code} {error_body}")
        except Exception as exc:
            self.last_ai_error = str(exc)
            print(f"[DEBUG] Gemini REST error: {exc}")
        return None

    def get_ai_subtasks(self, task_name, deadline_date):
        self.last_ai_error = ""
        if not self.gemini_api_key or not self.use_ai:
            self.last_ai_error = "AI is disabled or no API key is saved."
            print(
                f"[DEBUG] AI unavailable: has_key={bool(self.gemini_api_key)}, "
                f"use_ai={self.use_ai}"
            )
            return None

        # Try to import genai fresh in case Android packaging made the initial import unreliable.
        try:
            import google.generativeai as genai_fresh
            use_genai = True
        except ImportError:
            genai_fresh = None
            use_genai = False
            print("[DEBUG] google-generativeai not available, using REST fallback")

        try:
            deadline = datetime.strptime(deadline_date, '%Y-%m-%d')
            today = datetime.now().date()
            deadline_date_obj = deadline.date()
            days_left = (deadline_date_obj - today).days
            if days_left <= 0:
                self.last_ai_error = "Deadline must be at least one day in the future."
                return None
            date_list = []
            for i in range(days_left):
                date_list.append((today + timedelta(days=i)).strftime('%Y-%m-%d'))
            dates_str = ", ".join(date_list)
            prompt = f"""You are an expert academic task planner. Break down this student assignment into {days_left} SPECIFIC, CONCRETE daily subtasks.

TASK: {task_name}
DEADLINE: {deadline_date}
DAYS AVAILABLE: {days_left}
TODAY: {today}
AVAILABLE DATES: {dates_str}

RULES:
1. Generate exactly {days_left} subtasks (one per day)
2. Each subtask must be SPECIFIC and ACTIONABLE (not generic "daily task")
3. INCLUDE THE DATE for each subtask (YYYY-MM-DD format)
4. Subtasks should progress logically from research > planning > execution > review
5. Include specific topics, chapters, materials, or deliverables
6. Early days = planning/research, middle days = execution, final days = review/polish
7. Make subtasks relevant to the actual subject matter
8. Use action verbs (Research, Read, Write, Analyze, Create, Review, Study, etc.)

EXPECTED OUTPUT FORMAT:
{date_list[0]}: Specific activity for this date related to the task
{date_list[1] if len(date_list) > 1 else 'YYYY-MM-DD'}: Next specific activity
{date_list[2] if len(date_list) > 2 else 'YYYY-MM-DD'}: Continue with activities...

EXAMPLE for "Study for Biology Exam":
{date_list[0]}: Research exam format and identify key chapters to study
{date_list[1] if len(date_list) > 1 else 'Day 2'}: Read Chapter 3: Human Nervous System and take notes
{date_list[2] if len(date_list) > 2 else 'Day 3'}: Study Chapter 4: Cellular Respiration and Photosynthesis
{date_list[3] if len(date_list) > 3 else 'Day 4'}: Create flashcards for Cell Division and Genetics concepts
{date_list[4] if len(date_list) > 4 else 'Day 5'}: Practice past exam questions and review weak areas

EXAMPLE for "Write History Essay":
{date_list[0]}: Research essay topic and gather 5-7 primary sources
{date_list[1] if len(date_list) > 1 else 'Day 2'}: Create detailed outline with thesis statement and main arguments
{date_list[2] if len(date_list) > 2 else 'Day 3'}: Write introduction and first two body paragraphs
{date_list[3] if len(date_list) > 3 else 'Day 4'}: Complete final body paragraphs and write conclusion
{date_list[4] if len(date_list) > 4 else 'Day 5'}: Edit, proofread, and finalize citations

Keep each activity to 1-3 sentences. Be VERY SPECIFIC about WHAT to study, READ, WRITE, or ANALYZE."""
            text = None
            if use_genai:
                try:
                    genai_fresh.configure(api_key=self.gemini_api_key)
                    model = genai_fresh.GenerativeModel(GEMINI_MODEL_NAME)
                    response = model.generate_content(prompt)
                    if response:
                        text = getattr(response, 'text', None)
                        if not text and hasattr(response, 'to_dict'):
                            text = self._extract_gemini_text(response.to_dict())
                except Exception as exc:
                    self.last_ai_error = str(exc)
                    print(f"[DEBUG] Gemini SDK error: {exc}")

            if not text:
                text = self._generate_gemini_rest(prompt)

            if text:
                self.last_ai_error = ""
                print(f"\n[DEBUG] Gemini API Response for '{task_name}':\n{text}\n")
                return self._parse_ai_subtasks(text, deadline_date)

            if not self.last_ai_error:
                self.last_ai_error = "Gemini returned an empty response."
            print("[DEBUG] Gemini API returned empty response")
        except Exception as e:
            self.last_ai_error = str(e)
            print(f"[DEBUG] Gemini API error: {e}")
        return None

    def _parse_ai_subtasks(self, ai_text, deadline_str):
        subtasks = []
        try:
            lines = ai_text.strip().split('\n')
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            subtask_count = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if len(line) > 10 and line[4] == '-' and line[7] == '-':
                    try:
                        date_str = line[:10]
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        if ':' in line:
                            description = line.split(':', 1)[1].strip()
                        else:
                            description = line[10:].strip()
                        if description and date_obj <= deadline:
                            subtasks.append({
                                'id': f"subtask_{subtask_count}_{date_obj.isoformat()}",
                                'date': date_obj.isoformat(),
                                'time': '09:00',
                                'description': description[:150],
                                'completed': False,
                                'notification_enabled': True
                            })
                            subtask_count += 1
                            print(f"[DEBUG] Parsed: {date_obj.isoformat()} - {description[:80]}")
                    except Exception:
                        pass
        except Exception as e:
            print(f"[DEBUG] Error parsing AI subtasks: {e}")
        print(f"[DEBUG] Total subtasks parsed: {len(subtasks)}")
        return subtasks if len(subtasks) > 0 else None

    def add_task(self, task_name, deadline_date):
        task = {
            'id': len(self.tasks),
            'name': task_name,
            'deadline': deadline_date,
            'created': datetime.now().isoformat(),
            'subtasks': self._generate_subtasks(deadline_date),
            'completed': False
        }
        self.tasks.append(task)
        self.save_data()
        return task

    def _generate_subtasks(self, deadline_str):
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        except:
            return []
        today = datetime.now().date()
        deadline_date = deadline.date()
        if deadline_date <= today:
            return []
        days_left = (deadline_date - today).days
        subtasks = []
        for day in range(days_left):
            current_date = today + timedelta(days=day)
            subtasks.append({
                'id': f"subtask_{day}_{current_date.isoformat()}",
                'date': current_date.isoformat(),
                'time': '09:00',
                'description': f'Daily task - Day {day + 1}',
                'completed': False,
                'notification_enabled': True
            })
        return subtasks

    def update_subtask_time(self, task_id, subtask_id, time_str):
        if 0 <= task_id < len(self.tasks):
            task = self.tasks[task_id]
            for subtask in task['subtasks']:
                if subtask.get('id') == subtask_id:
                    subtask['time'] = time_str
        self.save_data()

    def get_task_count(self):
        return len(self.tasks)

    def get_subtask_count(self):
        return sum(len(task['subtasks']) for task in self.tasks)

    def mark_subtask_complete(self, task_id, subtask_id):
        if 0 <= task_id < len(self.tasks):
            task = self.tasks[task_id]
            for subtask in task['subtasks']:
                if subtask.get('id') == subtask_id:
                    subtask['completed'] = not subtask['completed']
        self.save_data()

    def delete_task(self, task_id):
        if 0 <= task_id < len(self.tasks):
            self.tasks.pop(task_id)
        self.save_data()


# ─── MAIN APP ─────────────────────────────────────────────────────────────────

class TimeBoundApp(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = TimeBoundData()
        self.notification_jobs = {}
        self.focus_mode_active = False
        self.focus_mode_blocked_until = None
        self.sent_notifications = set()  # Track which notifications have been sent
        self.app_blocker = AppBlocker()  # Initialize app blocker

    # ── Root build ────────────────────────────────────────────────────────────

    def build(self):
        self.title = "TimeBound"

        panel = TabbedPanel(
            do_default_tab=False,
            tab_width=74,
            tab_height=46,
            tab_pos='top_mid',
            background_color=BG_BASE,
            strip_border=(0, 0, 0, 0),
            strip_image='',
        )

        # Style the panel background
        with panel.canvas.before:
            Color(*BG_BASE)
            Rectangle(size=panel.size, pos=panel.pos)
        panel.bind(size=self._update_panel_bg, pos=self._update_panel_bg)

        tabs = [
            ('Home', self.build_dashboard),
            ('Add', self.build_add_task),
            ('Tasks', self.build_tasks_view),
            ('Schedule', self.build_schedule_view),
            ('Blocker', self.build_blocker_view),
            ('Settings', self.build_settings_view),
        ]

        for icon, builder in tabs:
            item = TabbedPanelItem(text=icon)
            item.background_normal = ''
            item.background_down = ''
            item.background_color = BG_SURFACE
            item.color = TEXT_PRIMARY
            item.font_size = '12sp'
            item.bold = True
            item.content = builder()
            panel.add_widget(item)
            if icon == 'Tasks':
                self.tasks_tab = item
            elif icon == 'Schedule':
                self.schedule_tab = item
            elif icon == 'Blocker':
                self.blocker_tab = item
            elif icon == 'Settings':
                self.settings_tab = item

        Clock.schedule_interval(self.check_notifications, 60)
        return panel

    def _update_panel_bg(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*BG_BASE)
            Rectangle(size=instance.size, pos=instance.pos)

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def build_dashboard(self):
        layout = BoxLayout(orientation='vertical', padding=[24, 34, 24, 30], spacing=28)

        # ── Header ──
        header = BoxLayout(size_hint_y=None, height=80, orientation='vertical', spacing=8)
        wordmark = Label(
            text='[b]TimeBound[/b]',
            markup=True,
            font_size='28sp',
            color=TEXT_PRIMARY,
            halign='left',
            valign='bottom',
            size_hint_y=None,
            height=38,
        )
        wordmark.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        tagline = Label(
            text='Academic Task Manager',
            font_size='12sp',
            color=TEXT_SECONDARY,
            halign='left',
            valign='top',
            size_hint_y=None,
            height=22,
        )
        tagline.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        header.add_widget(wordmark)
        header.add_widget(tagline)
        layout.add_widget(header)

        layout.add_widget(Divider())

        # ── Stat cards ──
        stats_row = BoxLayout(size_hint_y=None, height=130, spacing=16)

        task_count = self.data.get_task_count()
        subtask_count = self.data.get_subtask_count()

        task_card = Card(bg=BG_SURFACE, radius=14, padding=[20, 18, 20, 18])
        task_card.orientation = 'vertical'
        task_num = Label(text=str(task_count), font_size='32sp', bold=True, color=ACCENT_BLUE,
                         size_hint_y=0.6, halign='left', valign='bottom')
        task_num.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        task_lbl = Label(text='TASKS', font_size='10sp', bold=True, color=TEXT_SECONDARY,
                         size_hint_y=0.4, halign='left', valign='top')
        task_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        task_card.add_widget(task_num)
        task_card.add_widget(task_lbl)
        stats_row.add_widget(task_card)
        self.task_counter = task_num

        sub_card = Card(bg=BG_SURFACE, radius=14, padding=[20, 18, 20, 18])
        sub_card.orientation = 'vertical'
        sub_num = Label(text=str(subtask_count), font_size='32sp', bold=True, color=ACCENT_VIOLET,
                        size_hint_y=0.6, halign='left', valign='bottom')
        sub_num.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        sub_lbl = Label(text='SUBTASKS', font_size='10sp', bold=True, color=TEXT_SECONDARY,
                        size_hint_y=0.4, halign='left', valign='top')
        sub_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        sub_card.add_widget(sub_num)
        sub_card.add_widget(sub_lbl)
        stats_row.add_widget(sub_card)
        self.subtask_counter = sub_num

        layout.add_widget(stats_row)

        # ── Upcoming Notifications ──
        upcoming_card = Card(bg=(*ACCENT_BLUE[:3], 0.08), radius=14, padding=[16, 14, 16, 14],
                            orientation='vertical', spacing=12,
                            size_hint_y=None)
        
        upcoming_title = Label(
            text='[b]Today\'s Schedule[/b]',
            markup=True,
            font_size='12sp',
            bold=True,
            color=ACCENT_CYAN,
            size_hint_y=None,
            height=28,
            halign='left',
        )
        upcoming_title.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        upcoming_card.add_widget(upcoming_title)
        
        today = datetime.now().strftime('%Y-%m-%d')
        upcoming_found = False
        
        for task_idx, task in enumerate(self.data.tasks):
            for subtask in task['subtasks']:
                if subtask['date'] == today and subtask['notification_enabled'] and not subtask['completed']:
                    upcoming_found = True
                    sched_row = BoxLayout(size_hint_y=None, height=38, spacing=12)
                    
                    time_lbl = Label(
                        text=subtask['time'],
                        font_size='11sp',
                        bold=True,
                        color=ACCENT_CYAN,
                        halign='left',
                        valign='middle',
                        size_hint_x=0.2,
                    )
                    time_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
                    sched_row.add_widget(time_lbl)
                    
                    desc_lbl = Label(
                        text=task['name'],
                        font_size='11sp',
                        color=TEXT_PRIMARY,
                        halign='left',
                        valign='middle',
                        size_hint_x=0.8,
                    )
                    desc_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
                    sched_row.add_widget(desc_lbl)
                    
                    upcoming_card.add_widget(sched_row)
        
        if not upcoming_found:
            empty_sched = Label(
                text='No scheduled reminders today',
                font_size='11sp',
                color=TEXT_SECONDARY,
                size_hint_y=None,
                height=32,
                halign='left',
            )
            empty_sched.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            upcoming_card.add_widget(empty_sched)
        
        upcoming_card.size_hint_y = None
        upcoming_card.height = 28 + (38 * max(1, sum(1 for t in self.data.tasks for s in t['subtasks'] if s['date'] == today and s['notification_enabled'] and not s['completed'])))
        layout.add_widget(upcoming_card)

        # ── Feature list ──
        feat_card = Card(bg=BG_SURFACE, radius=14, padding=[20, 18, 20, 18],
                         orientation='vertical', spacing=14)

        feat_title = Label(
            text='GETTING STARTED',
            font_size='10sp',
            bold=True,
            color=TEXT_SECONDARY,
            size_hint_y=None,
            height=22,
            halign='left',
            valign='middle',
        )
        feat_title.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        feat_card.add_widget(feat_title)

        steps = [
            (ACCENT_BLUE,   '1', 'New Task  >  Enter your assignment & deadline'),
            (ACCENT_VIOLET, '2', 'Settings  >  Add your Gemini API key (optional)'),
            (ACCENT_CYAN,   '3', 'Schedule  >  Set your daily notification times'),
            (ACCENT_AMBER,  '4', 'Blocker   >  Add distracting apps to block'),
        ]
        for color, num, text in steps:
            row = BoxLayout(size_hint_y=None, height=50, spacing=14)
            badge = Label(text=num, font_size='12sp', bold=True, color=color,
                          size_hint_x=None, width=26)
            step_lbl = Label(text=text, font_size='12sp', color=TEXT_PRIMARY,
                             halign='left', valign='middle')
            step_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            row.add_widget(badge)
            row.add_widget(step_lbl)
            feat_card.add_widget(row)

        layout.add_widget(feat_card)

        # ── Refresh button ──
        refresh_btn = GhostButton(
            text='Refresh Stats',
            size_hint_y=None,
            height=46,
            accent=ACCENT_BLUE,
            font_size='13sp',
        )
        refresh_btn.bind(on_press=self.refresh_dashboard)
        layout.add_widget(refresh_btn)

        # Spacer
        layout.add_widget(Widget())

        return layout

    def refresh_dashboard(self, instance):
        self.task_counter.text = str(self.data.get_task_count())
        self.subtask_counter.text = str(self.data.get_subtask_count())

    # ── Add Task ──────────────────────────────────────────────────────────────

    def build_add_task(self):
        layout = BoxLayout(orientation='vertical', padding=[24, 34, 24, 30], spacing=28)

        # Header
        hdr = Label(
            text='[b]New Task[/b]',
            markup=True,
            font_size='22sp',
            color=TEXT_PRIMARY,
            size_hint_y=None,
            height=40,
            halign='left',
            valign='middle',
        )
        hdr.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        layout.add_widget(hdr)
        layout.add_widget(Divider())

        form_card = Card(bg=BG_SURFACE, radius=16, padding=[22, 24, 22, 24],
                 orientation='vertical', spacing=22)

        # Task description
        form_card.add_widget(section_label('Task Description'))
        task_name_input = styled_input(
            'Describe the assignment, exam, or project you need to finish',
            multiline=True,
        )
        task_name_input.size_hint_y = None
        task_name_input.height = 112
        form_card.add_widget(task_name_input)
        self.task_name_input = task_name_input

        # Deadline
        form_card.add_widget(section_label('Deadline'))
        deadline_input = styled_input('YYYY-MM-DD  e.g. 2026-04-15')
        deadline_input.size_hint_y = None
        deadline_input.height = 46
        form_card.add_widget(deadline_input)
        self.deadline_input = deadline_input

        form_card.add_widget(Divider())

        # AI toggle row
        ai_row = BoxLayout(size_hint_y=None, height=46, spacing=12)
        ai_icon = Label(text='AI', font_size='13sp', bold=True, color=ACCENT_BLUE, size_hint_x=None, width=40)
        ai_lbl = Label(
            text='Smart AI Breakdown',
            font_size='13sp',
            color=TEXT_PRIMARY,
            halign='left',
            valign='middle',
        )
        ai_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        ai_checkbox = CheckBox(
            size_hint_x=None,
            width=36,
            active=False,
            color=ACCENT_BLUE,
        )
        ai_row.add_widget(ai_icon)
        ai_row.add_widget(ai_lbl)
        ai_row.add_widget(ai_checkbox)
        form_card.add_widget(ai_row)

        hint_lbl = Label(
            text='Requires Gemini API key in Settings',
            font_size='11sp',
            color=TEXT_SECONDARY,
            size_hint_y=None,
            height=20,
            halign='left',
        )
        hint_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        form_card.add_widget(hint_lbl)

        layout.add_widget(form_card)

        # Create button
        def add_task_action(btn):
            task_name = task_name_input.text.strip()
            deadline = deadline_input.text.strip()
            use_ai = ai_checkbox.active

            if not task_name:
                self.show_message("Missing Info", "Please enter a task description.")
                return
            if not deadline:
                self.show_message("Missing Info", "Please enter a deadline.")
                return
            try:
                datetime.strptime(deadline, '%Y-%m-%d')
            except ValueError:
                self.show_message("Invalid Date", "Use the format YYYY-MM-DD")
                return

            ai_subtasks = None
            if use_ai and self.data.use_ai:
                self.show_message("Processing", "Generating smart breakdown…")
                ai_subtasks = self.data.get_ai_subtasks(task_name, deadline)

            task = self.data.add_task(task_name, deadline)
            if ai_subtasks:
                task['subtasks'] = ai_subtasks
                self.data.save_data()

            task_name_input.text = ''
            deadline_input.text = ''
            ai_checkbox.active = False

            self.refresh_dashboard(None)
            self.refresh_tasks_view(None)
            if hasattr(self, 'schedule_tab') and self.schedule_tab:
                self.schedule_tab.content = self.build_schedule_view()

            message = f"'{task_name}' added with {len(task['subtasks'])} daily subtasks."
            if use_ai and self.data.use_ai and not ai_subtasks:
                message += (
                    "\n\nAI breakdown failed on this attempt, so standard subtasks were used."
                    f"\nReason: {self.data.last_ai_error or 'Unknown Gemini error.'}"
                )
            self.show_message("Task Created", message)

        create_btn = PillButton(
            text='Create Task',
            size_hint_y=None,
            height=52,
            font_size='14sp',
            accent=ACCENT_BLUE,
            text_color=TEXT_INVERSE,
        )
        create_btn.bind(on_press=add_task_action)
        layout.add_widget(create_btn)
        layout.add_widget(Widget())

        return layout

    # ── Tasks View ────────────────────────────────────────────────────────────

    def build_tasks_view(self):
        main_layout = BoxLayout(orientation='vertical', padding=[32, 44, 32, 40], spacing=36)

        # Header row
        hdr_row = BoxLayout(size_hint_y=None, height=60, spacing=18)
        hdr = Label(
            text='[b]Your Tasks[/b]',
            markup=True,
            font_size='24sp',
            color=TEXT_PRIMARY,
            halign='left',
            valign='middle',
        )
        hdr.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        hdr_row.add_widget(hdr)
        refresh_btn = GhostButton(
            text='Refresh',
            size_hint_x=None,
            width=104,
            height=48,
            accent=ACCENT_BLUE,
            font_size='13sp',
        )
        refresh_btn.bind(on_press=self.refresh_tasks_view)
        hdr_row.add_widget(refresh_btn)
        main_layout.add_widget(hdr_row)
        main_layout.add_widget(Divider())

        scroll = ScrollView()
        tasks_layout = GridLayout(cols=1, spacing=38, size_hint_y=None, padding=[0, 22, 0, 24])
        tasks_layout.bind(minimum_height=tasks_layout.setter('height'))

        if not self.data.tasks:
            empty = Label(
                text='No tasks yet.\nTap [+] to create your first task.',
                size_hint_y=None,
                height=140,
                font_size='15sp',
                color=TEXT_SECONDARY,
                halign='center',
            )
            empty.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            tasks_layout.add_widget(empty)
        else:
            for idx, task in enumerate(self.data.tasks):
                tasks_layout.add_widget(self.create_task_widget(idx, task))

        scroll.add_widget(tasks_layout)
        self.tasks_layout_ref = tasks_layout
        main_layout.add_widget(scroll)
        return main_layout

    def _estimate_subtask_layout(self, description):
        normalized = " ".join((description or '').split())
        if not normalized:
            normalized = 'Untitled subtask'
        estimated_lines = max(1, math.ceil(len(normalized) / 34))
        description_height = max(56, estimated_lines * 22)
        row_height = max(108, description_height + 52)
        return description_height, row_height

    def create_task_widget(self, task_id, task):
        total = len(task['subtasks'])
        done = sum(1 for s in task['subtasks'] if s['completed'])
        pct = int(done / total * 100) if total else 0

        subtask_row_heights = []
        for subtask in task['subtasks']:
            desc = subtask.get('description', f"Subtask for {subtask['date']}")
            _, row_height = self._estimate_subtask_layout(desc)
            subtask_row_heights.append(row_height)

        subtask_section_height = sum(subtask_row_heights)
        if subtask_row_heights:
            subtask_section_height += 18 * (len(subtask_row_heights) - 1)
        else:
            subtask_section_height = 72

        card_height = 44 + 40 + 10 + 72 + 52 + subtask_section_height

        card = Card(bg=BG_SURFACE, radius=16, padding=[28, 26, 28, 26],
                    orientation='vertical', spacing=24,
                size_hint_y=None, height=card_height)

        # ── Task header ──
        hdr_row = BoxLayout(size_hint_y=None, height=44, spacing=14)
        name_lbl = Label(
            text=f"[b]{task['name']}[/b]",
            markup=True,
            font_size='17sp',
            color=TEXT_PRIMARY,
            halign='left',
            valign='middle',
        )
        name_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        hdr_row.add_widget(name_lbl)

        delete_btn = Button(
            text='Delete',
            size_hint_x=None,
            width=84,
            font_size='12sp',
            bold=True,
            color=ACCENT_RED,
            background_color=(0, 0, 0, 0),
            background_normal='',
            background_down='',
        )
        delete_btn.bind(on_press=lambda x: self.delete_task(task_id))
        hdr_row.add_widget(delete_btn)
        card.add_widget(hdr_row)

        # Deadline + progress
        meta_row = BoxLayout(size_hint_y=None, height=40, spacing=18)
        dl_lbl = Label(
            text=f"Deadline: {task['deadline']}",
            font_size='13sp',
            color=TEXT_SECONDARY,
            halign='left',
            valign='middle',
            size_hint_x=0.6,
        )
        dl_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        prog_lbl = Label(
            text=f"{done}/{total}  ({pct}%)",
            font_size='13sp',
            color=ACCENT_GREEN if pct == 100 else ACCENT_BLUE,
            halign='right',
            valign='middle',
            size_hint_x=0.4,
        )
        prog_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        meta_row.add_widget(dl_lbl)
        meta_row.add_widget(prog_lbl)
        card.add_widget(meta_row)

        # Progress bar
        bar_bg = Widget(size_hint_y=None, height=10)
        def draw_bar(w, *a):
            w.canvas.clear()
            with w.canvas:
                Color(*BG_ELEVATED)
                RoundedRectangle(size=w.size, pos=w.pos, radius=[5])
                if total:
                    fill_color = ACCENT_GREEN if pct == 100 else ACCENT_BLUE
                    Color(*fill_color)
                    RoundedRectangle(
                        size=(w.width * pct / 100, w.height),
                        pos=w.pos,
                        radius=[5]
                    )
        bar_bg.bind(size=draw_bar, pos=draw_bar)
        card.add_widget(bar_bg)

        # ── Subtasks ──
        subtask_layout = GridLayout(cols=1, spacing=18, size_hint_y=None)
        subtask_layout.bind(minimum_height=subtask_layout.setter('height'))

        for subtask in task['subtasks']:
            desc = subtask.get('description', f"Subtask for {subtask['date']}")
            completed = subtask['completed']
            description_height, row_height = self._estimate_subtask_layout(desc)

            row = BoxLayout(size_hint_y=None, height=row_height, spacing=18, padding=[18, 16, 16, 16])

            with row.canvas.before:
                Color(*BG_ELEVATED) if not completed else Color(*ACCENT_GREEN[:3], 0.06)
                RoundedRectangle(size=row.size, pos=row.pos, radius=[8])
            row.bind(size=lambda w, s, c=completed: self._redraw_subtask_row(w, c),
                     pos=lambda w, s, c=completed: self._redraw_subtask_row(w, c))

            text_col = BoxLayout(orientation='vertical', spacing=12, size_hint_y=None,
                                 height=description_height + 36)
            desc_lbl = Label(
                text=desc,
                font_size='14sp',
                color=(TEXT_SECONDARY if completed else TEXT_PRIMARY),
                halign='left',
                valign='top',
                size_hint_y=None,
                height=description_height,
            )
            desc_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            date_lbl = Label(
                text=f"{subtask['date']}  -  {subtask['time']}",
                font_size='12sp',
                color=TEXT_SECONDARY,
                halign='left',
                valign='top',
                size_hint_y=None,
                height=24,
            )
            date_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            text_col.add_widget(desc_lbl)
            text_col.add_widget(date_lbl)
            row.add_widget(text_col)

            check_lbl = 'Done' if completed else 'Mark'
            check_color = ACCENT_GREEN if completed else TEXT_SECONDARY
            check_btn = Button(
                text=check_lbl,
                size_hint_x=None,
                width=76,
                font_size='12sp',
                bold=True,
                color=check_color,
                background_color=(0, 0, 0, 0),
                background_normal='',
                background_down='',
            )
            check_btn.bind(on_press=lambda x, sid=task_id, st_id=subtask.get('id'):
                           self.toggle_subtask(sid, st_id))
            row.add_widget(check_btn)
            subtask_layout.add_widget(row)

        if not task['subtasks']:
            empty_lbl = Label(
                text='No subtasks generated yet.',
                font_size='13sp',
                color=TEXT_SECONDARY,
                size_hint_y=None,
                height=48,
                halign='left',
                valign='middle',
            )
            empty_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            card.add_widget(empty_lbl)
        else:
            card.add_widget(subtask_layout)
        return card

    def _redraw_subtask_row(self, widget, completed):
        widget.canvas.before.clear()
        with widget.canvas.before:
            if completed:
                Color(*ACCENT_GREEN[:3], 0.07)
            else:
                Color(*BG_ELEVATED)
            RoundedRectangle(size=widget.size, pos=widget.pos, radius=[8])

    def toggle_subtask(self, task_id, subtask_id):
        self.data.mark_subtask_complete(task_id, subtask_id)
        self.refresh_tasks_view(None)

    def delete_task(self, task_id):
        self.data.delete_task(task_id)
        self.refresh_dashboard(None)
        self.refresh_tasks_view(None)

    def refresh_tasks_view(self, instance):
        self.tasks_layout_ref.clear_widgets()
        if not self.data.tasks:
            empty = Label(
                text='No tasks yet.\nTap [+] to create your first task.',
                size_hint_y=None,
                height=100,
                font_size='13sp',
                color=TEXT_SECONDARY,
                halign='center',
            )
            empty.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            self.tasks_layout_ref.add_widget(empty)
        else:
            for idx, task in enumerate(self.data.tasks):
                self.tasks_layout_ref.add_widget(self.create_task_widget(idx, task))

    # ── Schedule View ─────────────────────────────────────────────────────────

    def build_schedule_view(self):
        layout = BoxLayout(orientation='vertical', padding=[24, 34, 24, 30], spacing=24)

        hdr = Label(
            text='[b]Notification Schedule[/b]',
            markup=True,
            font_size='22sp',
            color=TEXT_PRIMARY,
            size_hint_y=None,
            height=40,
            halign='left',
            valign='middle',
        )
        hdr.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        layout.add_widget(hdr)

        info = Label(
            text='Set the daily reminder time for each subtask.',
            font_size='12sp',
            color=TEXT_SECONDARY,
            size_hint_y=None,
            height=28,
            halign='left',
        )
        info.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        layout.add_widget(info)
        layout.add_widget(Divider())

        scroll = ScrollView()
        sched_layout = GridLayout(cols=1, spacing=20, size_hint_y=None, padding=[0, 12])
        sched_layout.bind(minimum_height=sched_layout.setter('height'))

        if not self.data.tasks:
            empty = Label(
                text='No tasks found. Create one first.',
                size_hint_y=None,
                height=60,
                font_size='13sp',
                color=TEXT_SECONDARY,
                halign='center',
            )
            empty.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            sched_layout.add_widget(empty)
        else:
            for task_id, task in enumerate(self.data.tasks):
                for subtask in task['subtasks']:
                    sched_layout.add_widget(
                        self.create_schedule_widget(task_id, task['name'], subtask)
                    )

        scroll.add_widget(sched_layout)
        layout.add_widget(scroll)
        return layout

    def create_schedule_widget(self, task_id, task_name, subtask):
        card = Card(bg=BG_SURFACE, radius=14, padding=[18, 16, 18, 16],
                orientation='vertical', spacing=12,
                size_hint_y=None, height=132)

        # Task + date label
        title_row = BoxLayout(size_hint_y=None, height=22)
        t_lbl = Label(
            text=f"[b]{task_name}[/b]  -  {subtask['date']}",
            markup=True,
            font_size='12sp',
            color=TEXT_PRIMARY,
            halign='left',
            valign='middle',
        )
        t_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        title_row.add_widget(t_lbl)
        card.add_widget(title_row)

        # Time picker row
        time_row = BoxLayout(size_hint_y=None, height=46, spacing=10)

        hours = [f'{h:02d}' for h in range(24)]
        minutes = ['00', '15', '30', '45']

        hour_sp = Spinner(
            text=subtask['time'].split(':')[0],
            values=hours,
            size_hint_x=0.28,
            background_normal='',
            background_down='',
            background_color=BG_ELEVATED,
            color=TEXT_PRIMARY,
            font_size='13sp',
        )
        sep = Label(text=':', font_size='16sp', bold=True, color=TEXT_SECONDARY,
                    size_hint_x=0.08)
        min_sp = Spinner(
            text=subtask['time'].split(':')[1] if subtask['time'].split(':')[1] in minutes else '00',
            values=minutes,
            size_hint_x=0.28,
            background_normal='',
            background_down='',
            background_color=BG_ELEVATED,
            color=TEXT_PRIMARY,
            font_size='13sp',
        )
        tz_lbl = Label(
            text='local time',
            font_size='10sp',
            color=TEXT_SECONDARY,
            size_hint_x=0.36,
            halign='left',
        )
        tz_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        time_row.add_widget(hour_sp)
        time_row.add_widget(sep)
        time_row.add_widget(min_sp)
        time_row.add_widget(tz_lbl)
        card.add_widget(time_row)

        def save_time(btn):
            new_time = f"{hour_sp.text}:{min_sp.text}"
            self.data.update_subtask_time(task_id, subtask.get('id'), new_time)
            self.show_message("Saved", f"Reminder set to {new_time}")

        save_btn = PillButton(
            text='Save Time',
            size_hint_y=None,
            height=30,
            font_size='12sp',
            accent=ACCENT_CYAN,
            text_color=BG_BASE,
        )
        save_btn.bind(on_press=save_time)
        card.add_widget(save_btn)
        return card

    # ── Blocker View ──────────────────────────────────────────────────────────

    def build_blocker_view(self):
        layout = BoxLayout(orientation='vertical', padding=[24, 34, 24, 30], spacing=24)

        hdr = Label(
            text='[b]Focus Mode[/b]',
            markup=True,
            font_size='22sp',
            color=TEXT_PRIMARY,
            size_hint_y=None,
            height=40,
            halign='left',
            valign='middle',
        )
        hdr.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        layout.add_widget(hdr)

        sub = Label(
            text='Block distracting apps during focus sessions.',
            font_size='12sp',
            color=TEXT_SECONDARY,
            size_hint_y=None,
            height=28,
            halign='left',
        )
        sub.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        layout.add_widget(sub)

        if PLATFORM == 'android':
            perm_note = Label(
                text='Android blocking uses Usage Access + screen pinning (lock task).',
                font_size='11sp',
                color=ACCENT_AMBER,
                size_hint_y=None,
                height=24,
                halign='left',
            )
            perm_note.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            layout.add_widget(perm_note)

            usage_state_text = (
                'Usage Access: enabled' if self.app_blocker.android_usage_ready()
                else 'Usage Access: not enabled'
            )
            usage_state = Label(
                text=usage_state_text,
                font_size='11sp',
                color=ACCENT_GREEN if self.app_blocker.android_usage_ready() else ACCENT_AMBER,
                size_hint_y=None,
                height=22,
                halign='left',
            )
            usage_state.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            layout.add_widget(usage_state)

            perm_btn = GhostButton(
                text='Open Usage Access Settings',
                size_hint_y=None,
                height=44,
                font_size='12sp',
                accent=ACCENT_AMBER,
            )

            def open_usage_access(btn):
                opened = self.app_blocker.request_android_usage_access()
                if opened:
                    self.show_message(
                        "Permission",
                        "Enable TimeBound in Usage Access settings, then return and start Focus Mode."
                    )
                else:
                    self.show_message("Permission", self.app_blocker.last_status or "Could not open settings.")

            perm_btn.bind(on_press=open_usage_access)
            layout.add_widget(perm_btn)

            app_settings_btn = GhostButton(
                text='Open Android App Settings',
                size_hint_y=None,
                height=42,
                font_size='12sp',
                accent=ACCENT_BLUE,
            )

            def open_app_settings(btn):
                opened = self.app_blocker.request_android_app_settings()
                if not opened:
                    self.show_message("Settings", self.app_blocker.last_status or "Could not open app settings.")

            app_settings_btn.bind(on_press=open_app_settings)
            layout.add_widget(app_settings_btn)

            security_btn = GhostButton(
                text='Open Security Settings (Screen Pinning)',
                size_hint_y=None,
                height=42,
                font_size='12sp',
                accent=ACCENT_CYAN,
            )

            def open_security_settings(btn):
                opened = self.app_blocker.request_android_security_settings()
                if not opened:
                    self.show_message("Settings", self.app_blocker.last_status or "Could not open security settings.")

            security_btn.bind(on_press=open_security_settings)
            layout.add_widget(security_btn)

        layout.add_widget(Divider())

        # Store reference to focus controls container for dynamic updates
        focus_controls_container = BoxLayout(orientation='vertical', spacing=16, size_hint_y=None)
        focus_controls_container.bind(minimum_height=focus_controls_container.setter('height'))
        self.focus_controls_container = focus_controls_container
        
        # Build initial focus controls
        self._rebuild_focus_controls(focus_controls_container)
        layout.add_widget(focus_controls_container)
        layout.add_widget(Divider())

        # Blocked apps list
        layout.add_widget(section_label('Apps to Block'))
        scroll = ScrollView(size_hint_y=0.25)
        apps_layout = GridLayout(cols=1, spacing=14, size_hint_y=None, padding=[0, 8])
        apps_layout.bind(minimum_height=apps_layout.setter('height'))

        self._populate_apps_list(apps_layout)

        scroll.add_widget(apps_layout)
        layout.add_widget(scroll)
        self.apps_layout_ref = apps_layout

        # Add app input
        layout.add_widget(section_label('Add New App'))
        app_input = styled_input('e.g. Instagram, TikTok, YouTube')
        app_input.size_hint_y = None
        app_input.height = 46
        layout.add_widget(app_input)
        self.app_input = app_input

        def add_app_action(btn):
            app_name = app_input.text.strip()
            if app_name and app_name not in self.data.blocked_apps:
                self.data.blocked_apps.append(app_name)
                self.data.save_data()
                app_input.text = ''
                self.refresh_blocker_view()
                self.show_message("Added", f"'{app_name}' added to block list.")

        add_btn = PillButton(
            text='+ Add to Block List',
            size_hint_y=None,
            height=50,
            font_size='14sp',
            accent=ACCENT_AMBER,
            text_color=BG_BASE,
        )
        add_btn.bind(on_press=add_app_action)
        layout.add_widget(add_btn)
        layout.add_widget(Widget())
        return layout

    def _rebuild_focus_controls(self, container):
        """Rebuild focus mode controls based on current state"""
        container.clear_widgets()

        # Focus mode status card
        status_card = Card(bg=BG_ELEVATED if self.focus_mode_active else BG_SURFACE, 
                  radius=14, padding=[16, 16, 16, 16],
                  orientation='vertical', spacing=10,
                  size_hint_y=None, height=124)
        
        status_color = ACCENT_GREEN if self.focus_mode_active else TEXT_SECONDARY
        status_text = "FOCUS MODE ACTIVE" if self.focus_mode_active else "Focus mode is off"
        
        status_lbl = Label(
            text=f"[b]{status_text}[/b]",
            markup=True,
            font_size='14sp',
            bold=True,
            color=status_color,
            size_hint_y=None,
            height=30,
            halign='center',
        )
        status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        status_card.add_widget(status_lbl)
        
        if self.focus_mode_active:
            timer_lbl = Label(
                text='Focus session in progress',
                font_size='11sp',
                color=ACCENT_GREEN,
                size_hint_y=None,
                height=22,
                halign='center',
            )
            timer_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            status_card.add_widget(timer_lbl)
            self.focus_status_label = status_lbl
            self.focus_timer_label = timer_lbl

        if self.app_blocker.last_status:
            blocker_status_lbl = Label(
                text=self.app_blocker.last_status,
                font_size='10sp',
                color=ACCENT_AMBER if 'required' in self.app_blocker.last_status.lower() else TEXT_SECONDARY,
                size_hint_y=None,
                height=20,
                halign='center',
            )
            blocker_status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            status_card.add_widget(blocker_status_lbl)
        
        container.add_widget(status_card)

        if not self.focus_mode_active:
            # Show start controls
            container.add_widget(section_label('Start Focus Session'))
            
            control_row = BoxLayout(size_hint_y=None, height=46, spacing=12)
            
            dur_input = TextInput(
                text='30',
                multiline=False,
                size_hint_x=0.3,
                input_filter='int',
                padding=[10, 8],
                background_normal='',
                background_color=BG_ELEVATED,
                foreground_color=TEXT_PRIMARY,
                font_size='13sp',
                height=42,
            )
            self.focus_duration_input = dur_input
            control_row.add_widget(dur_input)
            
            dur_lbl = Label(
                text='minutes',
                font_size='13sp',
                color=TEXT_SECONDARY,
                size_hint_x=0.25,
                halign='left',
            )
            dur_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            control_row.add_widget(dur_lbl)
            
            def start_focus(btn):
                try:
                    duration = int(dur_input.text.strip() or '30')
                    if duration > 0:
                        if PLATFORM == 'android' and self.data.blocked_apps and not self.app_blocker.android_usage_ready():
                            self.show_message(
                                "Permission Required",
                                "Enable Usage Access for TimeBound first, then start Focus Mode."
                            )
                            self.app_blocker.last_status = "Usage Access permission is required on Android."
                            self._rebuild_focus_controls(self.focus_controls_container)
                            return

                        # Start blocking apps
                        started = True
                        if self.data.blocked_apps:
                            started = self.app_blocker.start_blocking(self.data.blocked_apps)
                            if started:
                                block_status = f" - {len(self.data.blocked_apps)} apps blocked!"
                            else:
                                block_status = f" - {self.app_blocker.last_status}"
                        else:
                            block_status = " (no apps to block)"

                        if self.data.blocked_apps and not started:
                            self.show_message("Focus", f"Could not start app blocking{block_status}")
                            self._rebuild_focus_controls(self.focus_controls_container)
                            return

                        self.focus_mode_active = True
                        self.focus_mode_blocked_until = datetime.now() + timedelta(minutes=duration)
                        self.show_message("Focus", f"Focus mode started for {duration} minutes!{block_status}")
                        self._rebuild_focus_controls(self.focus_controls_container)
                        self.refresh_blocker_view()
                        Clock.schedule_once(self.check_focus_timer, 1)
                except:
                    self.show_message("Error", "Please enter a valid number")
            
            focus_btn = Button(
                text='Start',
                size_hint_x=0.35,
                background_normal='',
                background_down='',
                background_color=ACCENT_CYAN,
                color=BG_BASE,
                font_size='13sp',
                bold=True,
                height=42,
            )
            focus_btn.bind(on_press=start_focus)
            control_row.add_widget(focus_btn)
            container.add_widget(control_row)
        else:
            # Show stop button when focus is active
            def stop_focus(btn):
                self.focus_mode_active = False
                self.focus_mode_blocked_until = None
                # Stop blocking apps
                self.app_blocker.stop_blocking()
                self.show_message("Stopped", "Focus mode ended")
                self._rebuild_focus_controls(self.focus_controls_container)
                self.refresh_blocker_view()
            
            stop_btn = PillButton(
                text='Stop Focus Mode',
                size_hint_y=None,
                height=46,
                font_size='12sp',
                accent=ACCENT_RED,
                text_color=BG_BASE,
            )
            stop_btn.bind(on_press=stop_focus)
            container.add_widget(stop_btn)
    
    def check_focus_timer(self, dt):
        """Check if focus session is still active and update UI"""
        if not self.focus_mode_active:
            return
        
        if datetime.now() >= self.focus_mode_blocked_until:
            self.focus_mode_active = False
            # Stop blocking apps
            self.app_blocker.stop_blocking()
            self.show_message("Done", "Focus session completed!")
            self._rebuild_focus_controls(self.focus_controls_container)
            self.refresh_blocker_view()
        else:
            # Update timer display if labels exist
            if hasattr(self, 'focus_timer_label'):
                remaining = self.focus_mode_blocked_until - datetime.now()
                mins = remaining.seconds // 60
                secs = remaining.seconds % 60
                self.focus_timer_label.text = f"Time remaining: {mins}m {secs}s"
            Clock.schedule_once(self.check_focus_timer, 1)

    def _populate_apps_list(self, apps_layout):
        apps_layout.clear_widgets()
        if not self.data.blocked_apps:
            empty = Label(
                text='No apps to block',
                size_hint_y=None,
                height=40,
                font_size='13sp',
                color=TEXT_SECONDARY,
                halign='center',
            )
            empty.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            apps_layout.add_widget(empty)
        else:
            for app in self.data.blocked_apps:
                row = Card(bg=BG_SURFACE if not self.focus_mode_active else (*ACCENT_RED[:3], 0.1), 
                          radius=10, padding=[14, 10, 10, 10],
                          orientation='horizontal', spacing=12,
                          size_hint_y=None, height=54)
                a_lbl = Label(
                    text=app,
                    font_size='12sp',
                    color=TEXT_PRIMARY,
                    halign='left',
                    valign='middle',
                )
                a_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
                row.add_widget(a_lbl)
                rm_btn = Button(
                    text='Remove',
                    size_hint_x=None,
                    width=76,
                    font_size='11sp',
                    bold=True,
                    color=ACCENT_RED,
                    background_color=(0, 0, 0, 0),
                    background_normal='',
                    background_down='',
                )
                rm_btn.bind(on_press=lambda x, a=app: self.remove_blocked_app(a))
                row.add_widget(rm_btn)
                apps_layout.add_widget(row)

    def remove_blocked_app(self, app_name):
        if app_name in self.data.blocked_apps:
            self.data.blocked_apps.remove(app_name)
            self.data.save_data()
            self.refresh_blocker_view()

    def refresh_blocker_view(self):
        self._populate_apps_list(self.apps_layout_ref)

    # ── Settings View ─────────────────────────────────────────────────────────

    def build_settings_view(self):
        layout = BoxLayout(orientation='vertical', padding=[24, 34, 24, 30], spacing=24)

        hdr = Label(
            text='[b]Settings[/b]',
            markup=True,
            font_size='22sp',
            color=TEXT_PRIMARY,
            size_hint_y=None,
            height=40,
            halign='left',
            valign='middle',
        )
        hdr.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        layout.add_widget(hdr)
        layout.add_widget(Divider())

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', spacing=24, size_hint_y=None, padding=[0, 12])
        inner.bind(minimum_height=inner.setter('height'))

        # ── Gemini card ──
        api_card = Card(bg=BG_SURFACE, radius=16, padding=[20, 20, 20, 20],
                        orientation='vertical', spacing=14,
                        size_hint_y=None, height=360)

        api_hdr = BoxLayout(size_hint_y=None, height=44, spacing=12)
        api_icon = Label(text='AI', font_size='16sp', bold=True, color=ACCENT_VIOLET, size_hint_x=None, width=40)
        api_title = Label(
            text='[b]Google Gemini AI[/b]',
            markup=True,
            font_size='15sp',
            color=TEXT_PRIMARY,
            halign='left',
            valign='middle',
        )
        api_title.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        api_hdr.add_widget(api_icon)
        api_hdr.add_widget(api_title)
        api_card.add_widget(api_hdr)

        desc = Label(
            text=(
                'Connect your Gemini API key to unlock AI-powered task\n'
                'breakdowns. Without a key the app still works perfectly\n'
                'with standard daily subtasks.\n\n'
                'Get a free key at: makersuite.google.com/app/apikey\n'
                'Free tier: 10 000+ tasks per month.'
            ),
            font_size='11sp',
            color=TEXT_SECONDARY,
            size_hint_y=None,
            height=110,
            halign='left',
            valign='top',
        )
        desc.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        api_card.add_widget(desc)

        api_card.add_widget(section_label('API Key'))
        api_input = styled_input('Paste your Gemini API key here', password=True,
                                 text=self.data.gemini_api_key)
        api_input.size_hint_y = None
        api_input.height = 46
        api_card.add_widget(api_input)

        ai_toggle_row = BoxLayout(size_hint_y=None, height=44, spacing=10)
        at_lbl = Label(
            text='Enable AI Breakdown',
            font_size='13sp',
            color=TEXT_PRIMARY,
            halign='left',
            valign='middle',
        )
        at_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        ai_checkbox = CheckBox(
            size_hint_x=None,
            width=36,
            active=self.data.use_ai,
            color=ACCENT_BLUE,
        )
        ai_toggle_row.add_widget(at_lbl)
        ai_toggle_row.add_widget(ai_checkbox)
        api_card.add_widget(ai_toggle_row)

        inner.add_widget(api_card)

        # ── Status card ──
        configured = bool(self.data.gemini_api_key)
        status_card = Card(
            bg=BG_SURFACE,
            border_color=ACCENT_GREEN if configured else BG_BORDER,
            radius=14,
            padding=[16, 12, 16, 12],
            orientation='vertical',
            spacing=6,
            size_hint_y=None,
            height=72,
        )

        s_icon = 'OK' if configured else 'NO'
        s_color = ACCENT_GREEN if configured else TEXT_SECONDARY
        s_text = 'API key configured' if configured else 'API key not set'
        s_lbl = Label(
            text=f"[b]{s_icon}  {s_text}[/b]",
            markup=True,
            font_size='13sp',
            color=s_color,
            size_hint_y=None,
            height=24,
            halign='left',
        )
        s_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        ai_s_text = f"AI Breakdown: {'Enabled' if self.data.use_ai else 'Disabled'}"
        ai_s_lbl = Label(
            text=ai_s_text,
            font_size='12sp',
            color=ACCENT_VIOLET if self.data.use_ai else TEXT_SECONDARY,
            size_hint_y=None,
            height=20,
            halign='left',
        )
        ai_s_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        status_card.add_widget(s_lbl)
        status_card.add_widget(ai_s_lbl)
        inner.add_widget(status_card)

        scroll.add_widget(inner)
        layout.add_widget(scroll)

        # Save button
        def save_settings(btn):
            self.data.set_api_key(api_input.text)
            self.data.use_ai = ai_checkbox.active
            self.data.save_data()
            self.show_message(
                "Saved",
                f"Settings saved.\nAI Mode: {'Enabled' if ai_checkbox.active else 'Disabled'}"
            )

        save_btn = PillButton(
            text='Save Settings',
            size_hint_y=None,
            height=52,
            font_size='14sp',
            accent=ACCENT_VIOLET,
            text_color=TEXT_PRIMARY,
        )
        save_btn.bind(on_press=save_settings)
        layout.add_widget(save_btn)
        return layout

    # ── Notifications ─────────────────────────────────────────────────────────

    def check_notifications(self, dt):
        if not PLYER_AVAILABLE:
            return
        
        current_time = datetime.now()
        current_minutes = current_time.hour * 60 + current_time.minute
        
        for task_idx, task in enumerate(self.data.tasks):
            for subtask in task['subtasks']:
                if not subtask['notification_enabled'] or subtask['completed']:
                    continue
                if subtask['date'] != current_time.strftime('%Y-%m-%d'):
                    continue
                
                subtask_time = subtask['time']
                scheduled_hour, scheduled_min = map(int, subtask_time.split(':'))
                scheduled_minutes = scheduled_hour * 60 + scheduled_min
                
                # Create unique ID for this notification
                notif_id = f"{task_idx}_{subtask['date']}_{subtask_time}"
                
                # Fire notification if within 2-minute window (2 min before to current time)
                # This makes it more reliable if app isn't running at exact second
                if scheduled_minutes - 2 <= current_minutes <= scheduled_minutes:
                    if notif_id not in self.sent_notifications:
                        try:
                            notification.notify(
                                title='TimeBound Reminder',
                                message=f"{task['name']}\n{subtask['date']} - Start your daily task!",
                                timeout=10
                            )
                            self.sent_notifications.add(notif_id)
                            try:
                                vibrator.vibrate(0.5)
                            except:
                                pass
                            print(f"[Notification] Sent for {task['name']} at {subtask_time}")
                        except Exception as e:
                            print(f"[Notification Error] {e}")
                
                # Reset sent notification at end of day to allow next day's notification
                if current_time.hour == 0 and current_time.minute == 0:
                    if notif_id in self.sent_notifications:
                        self.sent_notifications.discard(notif_id)

    # ── Popup helper ──────────────────────────────────────────────────────────

    def show_message(self, title, message):
        overlay = BoxLayout(orientation='vertical', padding=24, spacing=16)

        with overlay.canvas.before:
            Color(*BG_SURFACE)
            RoundedRectangle(size=overlay.size, pos=overlay.pos, radius=[18])
        overlay.bind(
            size=lambda w, s: self._redraw_popup_bg(w),
            pos=lambda w, s: self._redraw_popup_bg(w),
        )

        t_lbl = Label(
            text=f'[b]{title}[/b]',
            markup=True,
            font_size='16sp',
            color=TEXT_PRIMARY,
            size_hint_y=None,
            height=30,
        )
        m_lbl = Label(
            text=message,
            font_size='13sp',
            color=TEXT_SECONDARY,
            halign='center',
        )
        m_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        ok_btn = PillButton(
            text='OK',
            size_hint_y=None,
            height=46,
            font_size='14sp',
            accent=ACCENT_BLUE,
            text_color=TEXT_INVERSE,
        )
        overlay.add_widget(t_lbl)
        overlay.add_widget(m_lbl)
        overlay.add_widget(ok_btn)

        popup = Popup(
            title='',
            title_size='1sp',
            content=overlay,
            size_hint=(0.82, 0.36),
            background='',
            background_color=(0, 0, 0, 0.55),
            separator_height=0,
        )
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()

    def _redraw_popup_bg(self, widget):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(*BG_SURFACE)
            RoundedRectangle(size=widget.size, pos=widget.pos, radius=[18])


if __name__ == '__main__':
    TimeBoundApp().run()