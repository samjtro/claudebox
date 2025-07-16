#!/usr/bin/env python3
"""
PyTask - Python Task Manager with LLM-Friendly Interface
Version: 2.0.0

A comprehensive task management system designed for both human and LLM operation.
Features include phase-based development, cross-context messaging, extension support,
and automatic state persistence.

Compatible with Python 3.6+ and works across all platforms and terminal types.
"""

import sqlite3
import json
import os
import sys
import datetime
import subprocess
import argparse
import textwrap
import re
import threading
import queue
import uuid
import shutil
import tempfile
import traceback
import platform
import time
import errno
import resource
import signal
import ast
import pickle
import base64
import hashlib
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from abc import ABC, abstractmethod

# Version and metadata
__version__ = "2.0.0"
__author__ = "PyTask Development Team"
__llm_friendly__ = True

# Platform compatibility checks - MUST RUN FIRST
def check_python_version():
    """Ensure Python version is compatible."""
    if sys.version_info < (3, 6):
        print(f"Error: Python 3.6+ required, found {sys.version}")
        print("Please upgrade Python to use this tool.")
        sys.exit(1)

def check_required_modules():
    """Verify all required modules are available."""
    required_modules = [
        'sqlite3', 'json', 'os', 'sys', 'datetime', 'subprocess',
        'argparse', 'textwrap', 're', 'threading', 'queue', 'uuid',
        'shutil', 'tempfile', 'traceback', 'platform', 'pathlib',
        'contextlib', 'typing', 'enum', 'dataclasses', 'collections', 'abc'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"Error: Missing required modules: {', '.join(missing)}")
        print("These are Python standard library modules.")
        print("Your Python installation may be incomplete.")
        sys.exit(1)
    
    return missing

def get_platform_config() -> Dict[str, Any]:
    """Get platform-specific configuration."""
    config = {
        'enable_colors': True,
        'path_separator': os.sep,
        'home_dir': Path.home(),
        'temp_dir': tempfile.gettempdir()
    }
    
    # Platform-specific adjustments
    if platform.system() == 'Windows':
        # Check if running in modern terminal that supports ANSI
        config['enable_colors'] = (
            os.environ.get('TERM_PROGRAM') == 'vscode' or
            os.environ.get('WT_SESSION') is not None or  # Windows Terminal
            'ANSICON' in os.environ
        )
    elif platform.system() == 'Darwin':  # macOS
        config['enable_colors'] = sys.stdout.isatty()
    else:  # Linux/Unix
        config['enable_colors'] = sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'
    
    return config

# Run compatibility checks
check_python_version()
check_required_modules()
PLATFORM_CONFIG = get_platform_config()

# Terminal compatibility layer
class ColorSupport(Enum):
    """Terminal color support levels"""
    NONE = 0        # No colors at all
    BASIC = 1       # Basic 8 colors
    EXTENDED = 2    # 16 colors
    FULL = 3        # 256+ colors (full ANSI)

class TerminalAdapter:
    """Intelligent terminal compatibility layer"""
    
    def __init__(self):
        self.color_support = self._detect_color_support()
        self.width = self._get_terminal_width()
        self.encoding = self._detect_encoding()
        self.unicode_support = self._detect_unicode_support()
        self._init_formatters()
    
    def _detect_color_support(self) -> ColorSupport:
        """Comprehensive color support detection"""
        # Check NO_COLOR environment variable (https://no-color.org/)
        if os.environ.get('NO_COLOR'):
            return ColorSupport.NONE
        
        # Not a TTY - no colors
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return ColorSupport.NONE
        
        # Windows specific checks
        if platform.system() == 'Windows':
            return self._detect_windows_color_support()
        
        # Unix-like systems
        term = os.environ.get('TERM', '').lower()
        colorterm = os.environ.get('COLORTERM', '').lower()
        
        # Advanced color support
        if colorterm in ['truecolor', '24bit'] or 'color' in colorterm:
            return ColorSupport.FULL
        
        # Check TERM variable
        if term == 'dumb':
            return ColorSupport.NONE
        elif any(x in term for x in ['256', 'color']):
            return ColorSupport.FULL
        elif term in ['xterm', 'screen', 'vt100', 'linux']:
            return ColorSupport.EXTENDED
        elif term:
            return ColorSupport.BASIC
        
        # Default to basic if we have a TERM
        return ColorSupport.BASIC if term else ColorSupport.NONE
    
    def _detect_windows_color_support(self) -> ColorSupport:
        """Windows-specific color detection"""
        try:
            import ctypes
            import ctypes.wintypes
            
            # Try to enable virtual terminal processing
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            
            mode = ctypes.wintypes.DWORD()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                if kernel32.SetConsoleMode(handle, mode.value | 0x0004):
                    return ColorSupport.FULL
            
            # Check Windows version (10+ has better support)
            if sys.getwindowsversion().major >= 10:
                return ColorSupport.EXTENDED
            
            return ColorSupport.BASIC
            
        except Exception:
            # Fallback for older Windows
            return ColorSupport.BASIC
    
    def _detect_encoding(self) -> str:
        """Detect safe terminal encoding"""
        # Get various encoding hints
        candidates = [
            sys.stdout.encoding,
            sys.getdefaultencoding(),
            os.environ.get('LANG', '').split('.')[-1],
            'utf-8'
        ]
        
        # Test each candidate
        for encoding in candidates:
            if encoding:
                try:
                    '测试'.encode(encoding)
                    return encoding
                except (UnicodeEncodeError, LookupError):
                    continue
        
        # Absolute fallback
        return 'ascii'
    
    def _detect_unicode_support(self) -> bool:
        """Check if terminal supports Unicode characters"""
        if self.encoding.lower() in ['utf-8', 'utf8', 'utf-16', 'utf16']:
            # Test actual output
            try:
                test_char = '✓'
                test_char.encode(self.encoding)
                return True
            except UnicodeEncodeError:
                return False
        return False
    
    def _get_terminal_width(self) -> int:
        """Get terminal width with fallback"""
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80  # Standard default
    
    def _init_formatters(self):
        """Initialize format functions based on capabilities"""
        if self.color_support == ColorSupport.NONE:
            # No colors at all
            self.colors = {
                'red': '', 'green': '', 'yellow': '', 'blue': '',
                'magenta': '', 'cyan': '', 'white': '', 'reset': ''
            }
            self.bold = ''
            self.dim = ''
            self.underline = ''
        elif self.color_support == ColorSupport.BASIC:
            # Basic 8 colors only
            self.colors = {
                'red': '\033[31m', 'green': '\033[32m', 
                'yellow': '\033[33m', 'blue': '\033[34m',
                'magenta': '\033[35m', 'cyan': '\033[36m',
                'white': '\033[37m', 'reset': '\033[0m'
            }
            self.bold = '\033[1m'
            self.dim = ''  # Not supported in basic
            self.underline = ''
        else:
            # Full ANSI support
            self.colors = {
                'red': '\033[91m', 'green': '\033[92m',
                'yellow': '\033[93m', 'blue': '\033[94m',
                'magenta': '\033[95m', 'cyan': '\033[96m',
                'white': '\033[97m', 'reset': '\033[0m'
            }
            self.bold = '\033[1m'
            self.dim = '\033[2m'
            self.underline = '\033[4m'
        
        # Unicode/ASCII symbols
        if self.unicode_support:
            self.symbols = {
                'check': '✓', 'cross': '✗', 'arrow': '→',
                'bullet': '•', 'box_h': '─', 'box_v': '│',
                'box_tl': '┌', 'box_tr': '┐', 'box_bl': '└', 
                'box_br': '┘', 'warning': '⚠️', 'info': 'ℹ️'
            }
        else:
            self.symbols = {
                'check': '[OK]', 'cross': '[X]', 'arrow': '->',
                'bullet': '*', 'box_h': '-', 'box_v': '|',
                'box_tl': '+', 'box_tr': '+', 'box_bl': '+',
                'box_br': '+', 'warning': '[!]', 'info': '[i]'
            }
    
    def format(self, text: str, color: Optional[str] = None, 
               bold: bool = False, dim: bool = False) -> str:
        """Format text with color and style"""
        result = text
        
        if color and color in self.colors:
            result = f"{self.colors[color]}{result}{self.colors['reset']}"
        
        if bold and self.bold:
            result = f"{self.bold}{result}{self.colors['reset']}"
            
        if dim and self.dim:
            result = f"{self.dim}{result}{self.colors['reset']}"
        
        return result

# Global terminal adapter instance
terminal = TerminalAdapter()

# Configuration with platform awareness
class Config:
    """Global configuration settings."""
    DB_FILE = ".tasks.db"
    BACKUP_DIR = ".task_backups"
    MAX_BACKUPS = 10
    ENABLE_COLORS = terminal.color_support != ColorSupport.NONE
    REQUIRE_REVIEW = True
    AUTO_COMMIT_CHECK = True
    MESSAGE_RETENTION_DAYS = 30
    AUDIT_RETENTION_DAYS = 90
    DEFAULT_PHASE_TITLE = "Initial Development"
    GIT_TIMEOUT = 30  # seconds
    MAX_JSON_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Platform-specific paths
    if platform.system() == 'Windows':
        DEFAULT_SHELL = 'cmd.exe'
    else:
        DEFAULT_SHELL = '/bin/sh'

# Enhanced color codes with platform support
class Colors:
    """ANSI color codes for terminal output."""
    RESET = terminal.colors['reset']
    BOLD = terminal.bold
    RED = terminal.colors['red']
    GREEN = terminal.colors['green']
    YELLOW = terminal.colors['yellow']
    BLUE = terminal.colors['blue']
    MAGENTA = terminal.colors['magenta']
    CYAN = terminal.colors['cyan']
    INVERSE = '\033[7m' if Config.ENABLE_COLORS else ''

# Custom exceptions for better error handling
class TaskManagerError(Exception):
    """Base exception for task manager errors."""
    pass

class DiskFullError(TaskManagerError):
    """Raised when disk is full."""
    def __init__(self, operation: str, path: Optional[str] = None):
        msg = f"Disk full during {operation}"
        if path:
            try:
                stat = shutil.disk_usage(os.path.dirname(path) or '.')
                free_mb = stat.free / (1024 * 1024)
                msg += f". Only {free_mb:.1f}MB free at {path}"
            except:
                pass
        super().__init__(msg)

class CorruptedDataError(TaskManagerError):
    """Raised when data corruption is detected."""
    pass

class NetworkTimeoutError(TaskManagerError):
    """Raised when network operations timeout."""
    pass

class InvalidEncodingError(TaskManagerError):
    """Raised when invalid encoding is encountered."""
    pass

# Task status enum
class TaskStatus(Enum):
    """Valid task statuses with state machine transitions."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    
    def can_transition_to(self, new_status: 'TaskStatus') -> bool:
        """Check if transition to new status is valid."""
        transitions = {
            TaskStatus.PENDING: [TaskStatus.IN_PROGRESS],
            TaskStatus.IN_PROGRESS: [TaskStatus.REVIEW, TaskStatus.PENDING],
            TaskStatus.REVIEW: [TaskStatus.COMPLETED, TaskStatus.PENDING],
            TaskStatus.COMPLETED: []  # Terminal state
        }
        return new_status in transitions.get(self, [])

# Enhanced data classes with validation
@dataclass
class Task:
    """Task entity with all attributes."""
    id: Optional[int] = None
    description: str = ""
    status: str = TaskStatus.PENDING.value
    phase_id: Optional[int] = None
    created_at: Optional[datetime.datetime] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    reviewed_at: Optional[datetime.datetime] = None
    review_comment: Optional[str] = None
    review_feedback: Optional[str] = None
    commit_hash: Optional[str] = None
    assignee: Optional[str] = None
    priority: int = 3
    
    def __post_init__(self):
        """Validate task data."""
        # Validate UTF-8 encoding
        if isinstance(self.description, bytes):
            try:
                self.description = self.description.decode('utf-8')
            except UnicodeDecodeError:
                raise InvalidEncodingError("Task description contains invalid UTF-8")
        
        # Validate priority
        if not 1 <= self.priority <= 5:
            raise ValueError(f"Priority must be between 1-5, got {self.priority}")

@dataclass
class Phase:
    """Phase entity for grouping tasks."""
    id: Optional[int] = None
    number: int = 1
    title: str = Config.DEFAULT_PHASE_TITLE
    status: str = "active"
    created_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    description: Optional[str] = None

@dataclass
class Message:
    """Message entity for cross-context communication."""
    id: Optional[int] = None
    content: str = ""
    from_context: str = "unknown"
    to_context: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    read_at: Optional[datetime.datetime] = None
    priority: str = "normal"
    tags: List[str] = field(default_factory=list)

# Safe JSON handling utilities
def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safely load JSON with corruption handling."""
    if not data:
        return default
    
    try:
        # Check size limit
        if len(data) > Config.MAX_JSON_SIZE:
            raise CorruptedDataError(f"JSON too large: {len(data)} bytes")
        
        return json.loads(data)
    except json.JSONDecodeError as e:
        # Log the error but don't crash
        print(f"{Colors.YELLOW}Warning: Corrupted JSON data: {e}{Colors.RESET}")
        return default
    except RecursionError:
        raise CorruptedDataError("JSON data has recursive references")

def safe_json_dumps(obj: Any) -> str:
    """Safely dump object to JSON with error handling."""
    try:
        # Use custom encoder for non-serializable objects
        class SafeEncoder(json.JSONEncoder):
            def default(self, obj):
                if hasattr(obj, '__dict__'):
                    return obj.__dict__
                elif hasattr(obj, '__str__'):
                    return str(obj)
                else:
                    return f"<non-serializable: {type(obj).__name__}>"
        
        result = json.dumps(obj, cls=SafeEncoder, ensure_ascii=True)
        
        # Check size
        if len(result) > Config.MAX_JSON_SIZE:
            raise ValueError(f"JSON output too large: {len(result)} bytes")
        
        return result
    except (TypeError, ValueError, RecursionError) as e:
        raise ValueError(f"Cannot serialize to JSON: {e}")

# Safe subprocess execution
def safe_subprocess_run(cmd: List[str], timeout: Optional[float] = None,
                       check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run subprocess with timeout and encoding handling."""
    if timeout is None:
        timeout = Config.GIT_TIMEOUT
    
    try:
        # Force text mode with UTF-8
        kwargs.setdefault('capture_output', True)
        kwargs.setdefault('text', True)
        kwargs.setdefault('encoding', 'utf-8')
        kwargs.setdefault('errors', 'replace')  # Replace invalid UTF-8
        
        result = subprocess.run(cmd, timeout=timeout, check=check, **kwargs)
        return result
        
    except subprocess.TimeoutExpired:
        raise NetworkTimeoutError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
    except FileNotFoundError:
        raise TaskManagerError(f"Command not found: {cmd[0]}")
    except subprocess.CalledProcessError as e:
        # Check for network-related errors
        if e.stderr and 'unable to access' in e.stderr:
            raise NetworkTimeoutError(f"Network error: {e.stderr}")
        raise

# Repository abstraction layer
class RepositoryDetector(ABC):
    """Abstract base class for repository detection."""
    
    @abstractmethod
    def detect(self) -> Dict[str, Any]:
        """Detect repository and return info."""
        pass
    
    @abstractmethod
    def get_uncommitted_changes(self) -> bool:
        """Check for uncommitted changes."""
        pass
    
    @abstractmethod
    def get_current_revision(self) -> Optional[str]:
        """Get current revision/commit hash."""
        pass

class GitDetector(RepositoryDetector):
    """Git repository detector."""
    
    def detect(self) -> Dict[str, Any]:
        """Detect git repository."""
        info = {
            'type': 'git',
            'root': os.getcwd(),
            'branch': None,
            'remote': None,
            'clean': True,
            'error': None
        }
        
        try:
            # Check if git repo
            safe_subprocess_run(['git', 'rev-parse', '--git-dir'])
            
            # Get root
            result = safe_subprocess_run(['git', 'rev-parse', '--show-toplevel'])
            info['root'] = result.stdout.strip()
            
            # Get branch
            result = safe_subprocess_run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
            info['branch'] = result.stdout.strip()
            
            # Get remote
            try:
                result = safe_subprocess_run(['git', 'config', '--get', 'remote.origin.url'])
                info['remote'] = result.stdout.strip()
            except subprocess.CalledProcessError:
                pass  # No remote configured
            
            # Check if clean
            info['clean'] = not self.get_uncommitted_changes()
            
        except NetworkTimeoutError as e:
            info['type'] = 'none'
            info['error'] = str(e)
        except (subprocess.CalledProcessError, TaskManagerError):
            info['type'] = 'none'
        
        return info
    
    def get_uncommitted_changes(self) -> bool:
        """Check for uncommitted git changes."""
        try:
            result = safe_subprocess_run(['git', 'status', '--porcelain'])
            return bool(result.stdout.strip())
        except (subprocess.CalledProcessError, NetworkTimeoutError):
            return False
    
    def get_current_revision(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = safe_subprocess_run(['git', 'rev-parse', 'HEAD'])
            return result.stdout.strip()
        except (subprocess.CalledProcessError, NetworkTimeoutError):
            return None

class SVNDetector(RepositoryDetector):
    """Subversion repository detector."""
    
    def detect(self) -> Dict[str, Any]:
        """Detect SVN repository."""
        info = {
            'type': 'none',
            'root': os.getcwd(),
            'url': None,
            'revision': None,
            'clean': True
        }
        
        # Check for .svn directory
        if not os.path.exists('.svn'):
            return info
        
        try:
            # Get SVN info
            result = safe_subprocess_run(['svn', 'info', '--xml'])
            
            # Parse XML output (basic parsing without external libs)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(result.stdout)
            
            entry = root.find('.//entry')
            if entry is not None:
                info['type'] = 'svn'
                info['revision'] = entry.get('revision')
                
                url_elem = entry.find('.//url')
                if url_elem is not None:
                    info['url'] = url_elem.text
                
                repo_elem = entry.find('.//root')
                if repo_elem is not None:
                    info['root'] = repo_elem.text
            
            # Check if clean
            info['clean'] = not self.get_uncommitted_changes()
            
        except (subprocess.CalledProcessError, NetworkTimeoutError, ET.ParseError):
            pass
        
        return info
    
    def get_uncommitted_changes(self) -> bool:
        """Check for uncommitted SVN changes."""
        try:
            result = safe_subprocess_run(['svn', 'status', '-q'])
            return bool(result.stdout.strip())
        except (subprocess.CalledProcessError, NetworkTimeoutError):
            return False
    
    def get_current_revision(self) -> Optional[str]:
        """Get current SVN revision."""
        try:
            result = safe_subprocess_run(['svnversion', '-n'])
            return result.stdout.strip()
        except (subprocess.CalledProcessError, NetworkTimeoutError):
            return None

class MercurialDetector(RepositoryDetector):
    """Mercurial repository detector."""
    
    def detect(self) -> Dict[str, Any]:
        """Detect Mercurial repository."""
        info = {
            'type': 'none',
            'root': os.getcwd(),
            'branch': None,
            'remote': None,
            'clean': True
        }
        
        # Check for .hg directory
        if not os.path.exists('.hg'):
            return info
        
        try:
            # Get branch
            result = safe_subprocess_run(['hg', 'branch'])
            info['type'] = 'mercurial'
            info['branch'] = result.stdout.strip()
            
            # Get root
            result = safe_subprocess_run(['hg', 'root'])
            info['root'] = result.stdout.strip()
            
            # Get remote
            try:
                result = safe_subprocess_run(['hg', 'paths', 'default'])
                info['remote'] = result.stdout.strip()
            except subprocess.CalledProcessError:
                pass  # No default remote
            
            # Check if clean
            info['clean'] = not self.get_uncommitted_changes()
            
        except (subprocess.CalledProcessError, NetworkTimeoutError):
            info['type'] = 'none'
        
        return info
    
    def get_uncommitted_changes(self) -> bool:
        """Check for uncommitted Mercurial changes."""
        try:
            result = safe_subprocess_run(['hg', 'status', '-mard'])
            return bool(result.stdout.strip())
        except (subprocess.CalledProcessError, NetworkTimeoutError):
            return False
    
    def get_current_revision(self) -> Optional[str]:
        """Get current Mercurial revision."""
        try:
            result = safe_subprocess_run(['hg', 'identify', '-i'])
            return result.stdout.strip()
        except (subprocess.CalledProcessError, NetworkTimeoutError):
            return None

class NoRepositoryDetector(RepositoryDetector):
    """Fallback when no repository is detected."""
    
    def detect(self) -> Dict[str, Any]:
        """Return info for non-repository directory."""
        return {
            'type': 'none',
            'root': os.getcwd(),
            'clean': True
        }
    
    def get_uncommitted_changes(self) -> bool:
        """No repository, no changes."""
        return False
    
    def get_current_revision(self) -> Optional[str]:
        """No repository, no revision."""
        return None

class RepositoryDetectorFactory:
    """Factory for creating appropriate repository detector."""
    
    @staticmethod
    def create() -> RepositoryDetector:
        """Create appropriate detector based on current directory."""
        # Check in order of likelihood
        if os.path.exists('.git'):
            return GitDetector()
        elif os.path.exists('.svn'):
            return SVNDetector()
        elif os.path.exists('.hg'):
            return MercurialDetector()
        else:
            return NoRepositoryDetector()

# Enhanced database manager with better error handling
class DatabaseManager:
    """Handles all database operations with safety and migrations."""
    
    SCHEMA_VERSION = 2
    
    def __init__(self, db_path: str = Config.DB_FILE):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                timeout=30.0  # Prevent lock timeouts
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            self._local.conn.execute("PRAGMA journal_mode = WAL")
        return self._local.conn
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions with enhanced error handling."""
        conn = self.conn
        try:
            yield conn
            conn.commit()
        except sqlite3.OperationalError as e:
            conn.rollback()
            error_msg = str(e).lower()
            if 'disk' in error_msg or 'space' in error_msg:
                raise DiskFullError("database write", self.db_path)
            elif 'locked' in error_msg:
                raise TaskManagerError("Database is locked. Another process may be using it.")
            else:
                raise
        except Exception:
            conn.rollback()
            raise
    
    def _check_disk_space(self, required_bytes: int = 1024 * 1024):
        """Check if sufficient disk space is available."""
        try:
            stat = shutil.disk_usage(os.path.dirname(self.db_path) or '.')
            if stat.free < required_bytes:
                raise DiskFullError("pre-check", self.db_path)
        except OSError as e:
            if e.errno == errno.ENOSPC:
                raise DiskFullError("disk check", self.db_path)
            raise
    
    def _init_db(self):
        """Initialize database with schema and migrations."""
        self._check_disk_space()
        
        with self.transaction() as conn:
            # Create schema version table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Check current version
            current_version = conn.execute(
                "SELECT MAX(version) FROM schema_version"
            ).fetchone()[0] or 0
            
            # Apply migrations
            if current_version < self.SCHEMA_VERSION:
                self._apply_migrations(current_version)
    
    def _apply_migrations(self, from_version: int):
        """Apply database migrations from current version."""
        migrations = {
            1: self._migration_v1,
            2: self._migration_v2,
        }
        
        for version in range(from_version + 1, self.SCHEMA_VERSION + 1):
            if version in migrations:
                migrations[version]()
                self.conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (version,)
                )
    
    def _migration_v1(self):
        """Initial schema creation."""
        schema_sql = """
        -- Tasks table
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'in_progress', 'review', 'completed')),
            phase_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            review_comment TEXT,
            review_feedback TEXT,
            commit_hash TEXT,
            assignee TEXT,
            priority INTEGER DEFAULT 3 CHECK(priority BETWEEN 1 AND 5),
            FOREIGN KEY (phase_id) REFERENCES phases(id)
        );
        
        -- Phases table
        CREATE TABLE IF NOT EXISTS phases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER NOT NULL UNIQUE,
            title TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('active', 'completed')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            description TEXT
        );
        
        -- Messages table
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            from_context TEXT NOT NULL,
            to_context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP,
            priority TEXT DEFAULT 'normal' CHECK(priority IN ('low', 'normal', 'high', 'urgent')),
            tags TEXT
        );
        
        -- Extensions table
        CREATE TABLE IF NOT EXISTS extensions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            enabled BOOLEAN DEFAULT 1,
            author TEXT,
            version TEXT DEFAULT '1.0.0'
        );
        
        -- Audit log
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            user_context TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Repository info
        CREATE TABLE IF NOT EXISTS repository_info (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_phase ON tasks(phase_id);
        CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(read_at);
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
        """
        
        for statement in schema_sql.split(';'):
            if statement.strip():
                self.conn.execute(statement)
        
        # Create initial phase
        self.conn.execute("""
            INSERT OR IGNORE INTO phases (number, title, status)
            VALUES (1, ?, 'active')
        """, (Config.DEFAULT_PHASE_TITLE,))
    
    def _migration_v2(self):
        """Add wizard state persistence table."""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS wizard_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                wizard_name TEXT NOT NULL,
                current_step INTEGER NOT NULL,
                state_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                completed BOOLEAN DEFAULT 0
            )
        ''')
        
        # Index for cleanup
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_wizard_expires 
            ON wizard_states(expires_at) 
            WHERE completed = 0
        ''')
    
    def backup(self) -> str:
        """Create a backup of the database with disk space checking."""
        self._check_disk_space(os.path.getsize(self.db_path) * 2)  # Need 2x space
        
        os.makedirs(Config.BACKUP_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(Config.BACKUP_DIR, f"tasks_{timestamp}.db")
        
        try:
            # Use SQLite backup API
            with sqlite3.connect(backup_path) as backup_conn:
                self.conn.backup(backup_conn)
        except sqlite3.Error as e:
            if os.path.exists(backup_path):
                os.remove(backup_path)
            raise DiskFullError("backup creation", backup_path)
        except OSError as e:
            if e.errno == errno.ENOSPC:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                raise DiskFullError("backup write", backup_path)
            raise
        
        # Clean old backups
        self._cleanup_old_backups()
        
        return backup_path
    
    def _cleanup_old_backups(self):
        """Remove old backups keeping only the most recent ones."""
        try:
            backup_files = sorted([
                f for f in os.listdir(Config.BACKUP_DIR)
                if f.startswith("tasks_") and f.endswith(".db")
            ])
            
            while len(backup_files) > Config.MAX_BACKUPS:
                old_file = backup_files.pop(0)
                os.remove(os.path.join(Config.BACKUP_DIR, old_file))
        except OSError:
            pass  # Non-critical, ignore cleanup errors
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

# Enhanced Task Manager with better error handling
class TaskManager:
    """Manages task CRUD operations and state transitions."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.repo_detector = RepositoryDetectorFactory.create()
    
    def create_task(self, description: str, phase_id: Optional[int] = None,
                    priority: int = 3, assignee: Optional[str] = None) -> Task:
        """Create a new task with validation."""
        # Validate UTF-8
        if isinstance(description, bytes):
            try:
                description = description.decode('utf-8')
            except UnicodeDecodeError:
                raise InvalidEncodingError("Task description must be valid UTF-8")
        
        if not description or not description.strip():
            raise ValueError("Task description cannot be empty")
        
        # Get current phase if not specified
        if phase_id is None:
            phase_id = self._get_current_phase_id()
        
        try:
            with self.db.transaction() as conn:
                cursor = conn.execute("""
                    INSERT INTO tasks (description, status, phase_id, priority, assignee)
                    VALUES (?, 'pending', ?, ?, ?)
                """, (description, phase_id, priority, assignee))
                
                task_id = cursor.lastrowid
                
                # Audit log with safe JSON
                self._audit_log('tasks', task_id, 'create', None, {
                    'description': description,
                    'phase_id': phase_id,
                    'priority': priority,
                    'assignee': assignee
                })
                
                return self.get_task(task_id)
        except sqlite3.OperationalError as e:
            if 'disk' in str(e).lower():
                raise DiskFullError("task creation", self.db.db_path)
            raise
    
    def get_task(self, task_id: int) -> Optional[Task]:
        """Retrieve a task by ID."""
        row = self.db.conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        
        if row:
            return Task(**dict(row))
        return None
    
    def list_tasks(self, status: Optional[str] = None,
                   phase_id: Optional[int] = None) -> List[Task]:
        """List tasks with optional filtering."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if phase_id is not None:
            query += " AND phase_id = ?"
            params.append(phase_id)
        
        query += " ORDER BY priority DESC, created_at ASC"
        
        rows = self.db.conn.execute(query, params).fetchall()
        return [Task(**dict(row)) for row in rows]
    
    def update_task_status(self, task_id: int, new_status: str,
                          comment: Optional[str] = None) -> Task:
        """Update task status with state machine validation."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Validate state transition
        current = TaskStatus(task.status)
        new = TaskStatus(new_status)
        
        if not current.can_transition_to(new):
            raise ValueError(
                f"Invalid transition from {current.value} to {new.value}"
            )
        
        updates = {"status": new_status}
        
        if new == TaskStatus.IN_PROGRESS:
            updates["started_at"] = datetime.datetime.now()
            # Check for existing in-progress tasks (warn but don't block)
            in_progress = self.list_tasks(status=TaskStatus.IN_PROGRESS.value)
            if in_progress:
                print(f"{Colors.YELLOW}Warning: You have {len(in_progress)} other task(s) in progress{Colors.RESET}")
        
        elif new == TaskStatus.REVIEW:
            # Check for uncommitted changes if repository detected
            if Config.AUTO_COMMIT_CHECK and self.repo_detector.detect()['type'] != 'none':
                try:
                    if self.repo_detector.get_uncommitted_changes():
                        raise ValueError(
                            "Cannot move to review with uncommitted changes. "
                            "Please commit your work first."
                        )
                    updates["commit_hash"] = self.repo_detector.get_current_revision()
                except NetworkTimeoutError:
                    # Network timeout shouldn't block task progress
                    print(f"{Colors.YELLOW}Warning: Could not check repository status (timeout){Colors.RESET}")
            
            updates["completed_at"] = datetime.datetime.now()
            if comment:
                updates["review_comment"] = comment
        
        elif new == TaskStatus.COMPLETED:
            updates["reviewed_at"] = datetime.datetime.now()
        
        elif new == TaskStatus.PENDING and current == TaskStatus.REVIEW:
            # Rejection case
            updates["started_at"] = None
            updates["completed_at"] = None
            if comment:
                updates["review_feedback"] = comment
        
        # Build update query
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [task_id]
        
        try:
            with self.db.transaction() as conn:
                # Audit log - capture old values
                old_values = {
                    "status": task.status,
                    "started_at": task.started_at,
                    "completed_at": task.completed_at,
                    "reviewed_at": task.reviewed_at,
                    "review_comment": task.review_comment,
                    "review_feedback": task.review_feedback,
                    "commit_hash": task.commit_hash
                }
                
                conn.execute(
                    f"UPDATE tasks SET {set_clause} WHERE id = ?",
                    values
                )
                
                self._audit_log('tasks', task_id, 'status_change', old_values, updates)
            
            return self.get_task(task_id)
        except sqlite3.OperationalError as e:
            if 'disk' in str(e).lower():
                raise DiskFullError("task update", self.db.db_path)
            raise
    
    def delete_task(self, task_id: int) -> bool:
        """Delete a task (soft delete by moving to completed)."""
        task = self.get_task(task_id)
        if not task:
            return False
        
        try:
            with self.db.transaction() as conn:
                conn.execute("""
                    UPDATE tasks 
                    SET status = 'completed', 
                        review_comment = 'DELETED',
                        reviewed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (task_id,))
                
                self._audit_log('tasks', task_id, 'delete', 
                               asdict(task) if task else None, None)
            
            return True
        except sqlite3.OperationalError as e:
            if 'disk' in str(e).lower():
                raise DiskFullError("task deletion", self.db.db_path)
            raise
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get comprehensive task statistics."""
        stats = {}
        
        # Count by status
        for status in TaskStatus:
            count = self.db.conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = ?",
                (status.value,)
            ).fetchone()[0]
            stats[status.value] = count
        
        # Additional metrics
        stats['total'] = sum(stats.values())
        stats['active'] = stats['in_progress'] + stats['review']
        
        # Phase statistics
        phase_stats = self.db.conn.execute("""
            SELECT p.id, p.title, COUNT(t.id) as task_count
            FROM phases p
            LEFT JOIN tasks t ON p.id = t.phase_id
            WHERE p.status = 'active'
            GROUP BY p.id
        """).fetchall()
        
        stats['current_phase'] = dict(phase_stats[0]) if phase_stats else None
        
        return stats
    
    def _get_current_phase_id(self) -> int:
        """Get the current active phase ID."""
        row = self.db.conn.execute(
            "SELECT id FROM phases WHERE status = 'active' ORDER BY number DESC LIMIT 1"
        ).fetchone()
        
        if row:
            return row['id']
        
        # Create default phase if none exists
        cursor = self.db.conn.execute("""
            INSERT INTO phases (number, title, status)
            VALUES (1, ?, 'active')
        """, (Config.DEFAULT_PHASE_TITLE,))
        
        return cursor.lastrowid
    
    def _audit_log(self, entity_type: str, entity_id: int, action: str,
                   old_value: Any, new_value: Any):
        """Record audit log entry with safe JSON serialization."""
        try:
            self.db.conn.execute("""
                INSERT INTO audit_log (entity_type, entity_id, action, old_value, new_value, user_context)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entity_type,
                entity_id,
                action,
                safe_json_dumps(old_value) if old_value else None,
                safe_json_dumps(new_value) if new_value else None,
                os.environ.get('USER', 'unknown')
            ))
        except ValueError as e:
            # Log serialization errors but don't fail the operation
            print(f"{Colors.YELLOW}Warning: Could not serialize audit log: {e}{Colors.RESET}")

# Phase Manager
class PhaseManager:
    """Manages development phases."""
    
    def __init__(self, db: DatabaseManager, task_manager: TaskManager):
        self.db = db
        self.task_manager = task_manager
    
    def get_current_phase(self) -> Optional[Phase]:
        """Get the current active phase."""
        row = self.db.conn.execute(
            "SELECT * FROM phases WHERE status = 'active' ORDER BY number DESC LIMIT 1"
        ).fetchone()
        
        if row:
            return Phase(**dict(row))
        return None
    
    def create_phase(self, title: str, description: Optional[str] = None) -> Phase:
        """Create a new phase (current phase must be clear)."""
        current = self.get_current_phase()
        if current:
            # Check if board is clear
            active_tasks = (
                self.task_manager.list_tasks(status=TaskStatus.PENDING.value) +
                self.task_manager.list_tasks(status=TaskStatus.IN_PROGRESS.value) +
                self.task_manager.list_tasks(status=TaskStatus.REVIEW.value)
            )
            
            if active_tasks:
                raise ValueError(
                    f"Cannot create new phase. {len(active_tasks)} active tasks remain. "
                    "Complete all tasks before starting a new phase."
                )
            
            # Check if current phase has any tasks
            all_tasks = self.task_manager.list_tasks(phase_id=current.id)
            if not all_tasks:
                raise ValueError(
                    "Cannot close a phase with no tasks. "
                    "Add tasks to the current phase or rename it instead."
                )
            
            # Archive current phase
            try:
                with self.db.transaction() as conn:
                    conn.execute("""
                        UPDATE phases 
                        SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (current.id,))
            except sqlite3.OperationalError as e:
                if 'disk' in str(e).lower():
                    raise DiskFullError("phase archival", self.db.db_path)
                raise
        
        # Create new phase
        next_number = (current.number + 1) if current else 1
        
        try:
            with self.db.transaction() as conn:
                cursor = conn.execute("""
                    INSERT INTO phases (number, title, status, description)
                    VALUES (?, ?, 'active', ?)
                """, (next_number, title, description))
                
                phase_id = cursor.lastrowid
                return self.get_phase(phase_id)
        except sqlite3.OperationalError as e:
            if 'disk' in str(e).lower():
                raise DiskFullError("phase creation", self.db.db_path)
            raise
    
    def rename_current_phase(self, new_title: str) -> Phase:
        """Rename the current active phase."""
        current = self.get_current_phase()
        if not current:
            raise ValueError("No active phase found")
        
        try:
            with self.db.transaction() as conn:
                conn.execute(
                    "UPDATE phases SET title = ? WHERE id = ?",
                    (new_title, current.id)
                )
            
            return self.get_phase(current.id)
        except sqlite3.OperationalError as e:
            if 'disk' in str(e).lower():
                raise DiskFullError("phase rename", self.db.db_path)
            raise
    
    def get_phase(self, phase_id: int) -> Optional[Phase]:
        """Get a phase by ID."""
        row = self.db.conn.execute(
            "SELECT * FROM phases WHERE id = ?", (phase_id,)
        ).fetchone()
        
        if row:
            return Phase(**dict(row))
        return None
    
    def list_phases(self) -> List[Phase]:
        """List all phases."""
        rows = self.db.conn.execute(
            "SELECT * FROM phases ORDER BY number DESC"
        ).fetchall()
        
        return [Phase(**dict(row)) for row in rows]
    
    def get_phase_summary(self, phase_id: int) -> Dict[str, Any]:
        """Get detailed summary of a phase."""
        phase = self.get_phase(phase_id)
        if not phase:
            return {}
        
        tasks = self.task_manager.list_tasks(phase_id=phase_id)
        
        summary = {
            'phase': asdict(phase),
            'task_count': len(tasks),
            'completed_tasks': len([t for t in tasks if t.status == 'completed']),
            'tasks_by_status': defaultdict(int)
        }
        
        for task in tasks:
            summary['tasks_by_status'][task.status] += 1
        
        return summary

# Enhanced Message Manager with corruption handling
class MessageManager:
    """Manages cross-context messaging."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def send_message(self, content: str, from_context: str,
                     to_context: Optional[str] = None,
                     priority: str = "normal",
                     tags: Optional[List[str]] = None) -> Message:
        """Send a message to another context."""
        if not content:
            raise ValueError("Message content cannot be empty")
        
        # Validate tags can be JSON serialized
        try:
            tags_json = safe_json_dumps(tags or [])
        except ValueError as e:
            raise ValueError(f"Message tags cannot be serialized: {e}")
        
        try:
            with self.db.transaction() as conn:
                cursor = conn.execute("""
                    INSERT INTO messages (content, from_context, to_context, priority, tags)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    content,
                    from_context,
                    to_context,
                    priority,
                    tags_json
                ))
                
                return self.get_message(cursor.lastrowid)
        except sqlite3.OperationalError as e:
            if 'disk' in str(e).lower():
                raise DiskFullError("message send", self.db.db_path)
            raise
    
    def get_message(self, message_id: int) -> Optional[Message]:
        """Get a message by ID."""
        row = self.db.conn.execute(
            "SELECT * FROM messages WHERE id = ?", (message_id,)
        ).fetchone()
        
        if row:
            msg = Message(**dict(row))
            if msg.tags and isinstance(msg.tags, str):
                msg.tags = safe_json_loads(msg.tags, default=[])
            return msg
        return None
    
    def list_messages(self, unread_only: bool = False,
                      to_context: Optional[str] = None) -> List[Message]:
        """List messages with optional filtering."""
        query = "SELECT * FROM messages WHERE 1=1"
        params = []
        
        if unread_only:
            query += " AND read_at IS NULL"
        
        if to_context:
            query += " AND (to_context = ? OR to_context IS NULL)"
            params.append(to_context)
        
        query += " ORDER BY priority DESC, created_at DESC"
        
        rows = self.db.conn.execute(query, params).fetchall()
        messages = []
        
        for row in rows:
            msg = Message(**dict(row))
            if msg.tags and isinstance(msg.tags, str):
                msg.tags = safe_json_loads(msg.tags, default=[])
            messages.append(msg)
        
        return messages
    
    def mark_as_read(self, message_id: int) -> bool:
        """Mark a message as read."""
        try:
            with self.db.transaction() as conn:
                conn.execute(
                    "UPDATE messages SET read_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (message_id,)
                )
            return True
        except sqlite3.OperationalError as e:
            if 'disk' in str(e).lower():
                raise DiskFullError("message update", self.db.db_path)
            raise
    
    def delete_message(self, message_id: int) -> bool:
        """Delete a message."""
        try:
            with self.db.transaction() as conn:
                conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
            return True
        except sqlite3.OperationalError as e:
            if 'disk' in str(e).lower():
                raise DiskFullError("message deletion", self.db.db_path)
            raise
    
    def cleanup_old_messages(self):
        """Remove messages older than retention period."""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(
            days=Config.MESSAGE_RETENTION_DAYS
        )
        
        try:
            with self.db.transaction() as conn:
                conn.execute(
                    "DELETE FROM messages WHERE created_at < ? AND read_at IS NOT NULL",
                    (cutoff_date,)
                )
        except sqlite3.OperationalError:
            pass  # Non-critical cleanup, ignore errors

# Secure Extension Sandbox
class SecureExtensionSandbox:
    """Hardened sandbox for extension execution with strict resource limits"""
    
    # Resource limits
    MEMORY_LIMIT_MB = 50
    EXECUTION_TIMEOUT_SECONDS = 5
    MAX_FILE_SIZE_MB = 10
    MAX_OPEN_FILES = 10
    
    def __init__(self):
        self.safe_builtins = self._create_safe_builtins()
        self.execution_count = 0
        
    def _create_safe_builtins(self) -> Dict[str, Any]:
        """Create comprehensive safe builtins subset"""
        return {
            # Safe type constructors
            'int': int, 'float': float, 'str': str, 'bool': bool,
            'list': list, 'tuple': tuple, 'dict': dict, 'set': set,
            'frozenset': frozenset, 'bytes': bytes, 'bytearray': bytearray,
            
            # Safe functions
            'len': len, 'range': range, 'enumerate': enumerate,
            'zip': zip, 'map': map, 'filter': filter,
            'sorted': sorted, 'reversed': reversed,
            'sum': sum, 'min': min, 'max': max,
            'abs': abs, 'round': round, 'pow': pow,
            'all': all, 'any': any,
            
            # String operations
            'chr': chr, 'ord': ord,
            
            # Type checking
            'isinstance': isinstance, 'issubclass': issubclass,
            'hasattr': hasattr, 'getattr': getattr,
            'type': type,
            
            # Limited I/O (stdout only)
            'print': self._safe_print,
            
            # Explicitly blocked
            '__import__': None,
            'eval': None,
            'exec': None,
            'compile': None,
            'open': None,
            'input': None,
            'breakpoint': None,
            'help': None,
            'dir': None,
            'globals': None,
            'locals': None,
            'vars': None,
        }
    
    def _safe_print(self, *args, **kwargs):
        """Limited print that prevents large outputs"""
        output = ' '.join(str(arg) for arg in args)
        if len(output) > 1000:  # Limit output size
            output = output[:997] + "..."
        print(output, **{k: v for k, v in kwargs.items() if k in ['end', 'sep']})
    
    @contextmanager
    def _resource_limits(self):
        """Apply resource limits for sandboxed execution"""
        if sys.platform != 'win32':  # Resource limits not available on Windows
            # Save original limits
            original_limits = {}
            
            try:
                # Memory limit (data segment)
                original_limits['data'] = resource.getrlimit(resource.RLIMIT_DATA)
                resource.setrlimit(resource.RLIMIT_DATA, 
                    (self.MEMORY_LIMIT_MB * 1024 * 1024, self.MEMORY_LIMIT_MB * 1024 * 1024))
                
                # File size limit
                original_limits['fsize'] = resource.getrlimit(resource.RLIMIT_FSIZE)
                resource.setrlimit(resource.RLIMIT_FSIZE,
                    (self.MAX_FILE_SIZE_MB * 1024 * 1024, self.MAX_FILE_SIZE_MB * 1024 * 1024))
                
                # Number of open files
                original_limits['nofile'] = resource.getrlimit(resource.RLIMIT_NOFILE)
                resource.setrlimit(resource.RLIMIT_NOFILE, 
                    (self.MAX_OPEN_FILES, self.MAX_OPEN_FILES))
                
                yield
                
            finally:
                # Restore original limits
                for limit_name, limit_value in original_limits.items():
                    limit_const = getattr(resource, f'RLIMIT_{limit_name.upper()}')
                    resource.setrlimit(limit_const, limit_value)
        else:
            # On Windows, we rely on subprocess isolation
            yield
    
    def _timeout_handler(self, signum, frame):
        """Handle execution timeout"""
        raise TimeoutError(f"Extension execution exceeded {self.EXECUTION_TIMEOUT_SECONDS}s limit")
    
    def execute_extension(self, code: str, context: dict) -> Tuple[bool, Any, str]:
        """Execute extension code with full sandboxing"""
        self.execution_count += 1
        
        # Use subprocess isolation for better security
        if self._should_use_subprocess():
            return self._execute_subprocess(code, context)
        else:
            return self._execute_inline(code, context)
    
    def _should_use_subprocess(self) -> bool:
        """Determine if subprocess isolation is available and recommended"""
        # Always use subprocess on Unix-like systems for better isolation
        return sys.platform != 'win32'
    
    def _execute_subprocess(self, code: str, context: dict) -> Tuple[bool, Any, str]:
        """Execute in isolated subprocess with strict limits"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write execution script
            script_path = os.path.join(tmpdir, 'extension.py')
            with open(script_path, 'w') as f:
                f.write(self._generate_subprocess_wrapper(code))
            
            # Write context
            context_path = os.path.join(tmpdir, 'context.json')
            with open(context_path, 'w') as f:
                json.dump(context, f)
            
            # Prepare environment with restrictions
            env = os.environ.copy()
            env['TMPDIR'] = tmpdir  # Restrict temp file location
            env['HOME'] = tmpdir    # Prevent home directory access
            env['PATH'] = ''        # No PATH access
            
            # Remove sensitive environment variables
            for key in list(env.keys()):
                if any(sensitive in key.upper() for sensitive in 
                       ['KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'API', 'CREDENTIAL']):
                    del env[key]
            
            try:
                # Run with timeout and capture output
                result = subprocess.run(
                    [sys.executable, '-u', script_path, context_path],
                    capture_output=True,
                    text=True,
                    timeout=self.EXECUTION_TIMEOUT_SECONDS,
                    env=env,
                    cwd=tmpdir  # Restrict working directory
                )
                
                if result.returncode == 0:
                    # Parse result
                    try:
                        output = json.loads(result.stdout)
                        return True, output.get('result'), output.get('output', '')
                    except json.JSONDecodeError:
                        return False, None, f"Invalid output: {result.stdout}"
                else:
                    return False, None, f"Extension error: {result.stderr}"
                    
            except subprocess.TimeoutExpired:
                return False, None, f"Extension execution timeout ({self.EXECUTION_TIMEOUT_SECONDS}s)"
            except Exception as e:
                return False, None, f"Subprocess execution failed: {str(e)}"
    
    def _generate_subprocess_wrapper(self, code: str) -> str:
        """Generate wrapper code for subprocess execution"""
        return f'''
import json
import sys
import signal

# Set up timeout handler
def timeout_handler(signum, frame):
    print(json.dumps({{"error": "Execution timeout"}}))
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({self.EXECUTION_TIMEOUT_SECONDS})

# Load context
with open(sys.argv[1], 'r') as f:
    context = json.load(f)

# Safe builtins
safe_builtins = {repr(self.safe_builtins)}

# Execution namespace
namespace = {{
    '__builtins__': safe_builtins,
    'context': context,
    'result': None,
    'output': []
}}

# Capture prints
original_print = print
def capture_print(*args, **kwargs):
    namespace['output'].append(' '.join(str(arg) for arg in args))
    
safe_builtins['print'] = capture_print

# Execute extension
try:
    exec(compile({repr(code)}, 'extension', 'exec'), namespace)
    result = {{
        'result': namespace.get('result'),
        'output': '\\n'.join(namespace['output'])
    }}
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
    sys.exit(1)
'''
    
    def _execute_inline(self, code: str, context: dict) -> Tuple[bool, Any, str]:
        """Execute inline with timeouts and resource limits"""
        # Set up timeout
        if hasattr(signal, 'SIGALRM'):  # Unix-like systems
            old_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.EXECUTION_TIMEOUT_SECONDS)
        
        output_buffer = []
        
        def capture_print(*args, **kwargs):
            output_buffer.append(' '.join(str(arg) for arg in args))
        
        # Create restricted namespace
        namespace = {
            '__builtins__': self.safe_builtins.copy(),
            'context': context.copy(),
            'result': None
        }
        namespace['__builtins__']['print'] = capture_print
        
        try:
            with self._resource_limits():
                # Parse and validate code
                tree = ast.parse(code)
                validator = ExtensionValidator()
                validator.visit(tree)
                
                # Execute in restricted namespace
                exec(compile(tree, 'extension', 'exec'), namespace)
                
                return True, namespace.get('result'), '\n'.join(output_buffer)
                
        except TimeoutError as e:
            return False, None, str(e)
        except Exception as e:
            return False, None, f"Extension error: {str(e)}"
        finally:
            # Cancel timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

class ExtensionValidator(ast.NodeVisitor):
    """AST validator to ensure extension code safety"""
    
    FORBIDDEN_NAMES = {
        '__import__', 'eval', 'exec', 'compile', 'open', 'input',
        'breakpoint', 'help', 'dir', 'globals', 'locals', 'vars',
        'setattr', 'delattr', '__dict__', '__class__', '__bases__',
        '__subclasses__', '__code__', '__closure__'
    }
    
    FORBIDDEN_MODULES = {
        'os', 'sys', 'subprocess', 'socket', 'requests', 'urllib',
        'http', 'ftplib', 'telnetlib', 'ssl', 'select', 'selectors',
        'asyncio', 'threading', 'multiprocessing', 'concurrent',
        'ctypes', 'cffi', 'importlib', 'pkgutil', 'inspect',
        'gc', 'weakref', 'pickle', 'marshal', 'shelve'
    }
    
    def visit_Import(self, node):
        """Block all imports"""
        raise ValueError("Import statements are not allowed in extensions")
    
    def visit_ImportFrom(self, node):
        """Block all from imports"""
        raise ValueError("Import statements are not allowed in extensions")
    
    def visit_Name(self, node):
        """Check for forbidden names"""
        if node.id in self.FORBIDDEN_NAMES:
            raise ValueError(f"Access to '{node.id}' is not allowed")
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Check for dangerous attributes"""
        if isinstance(node.attr, str):
            if node.attr.startswith('_'):
                raise ValueError(f"Access to private attributes is not allowed")
            if node.attr in self.FORBIDDEN_NAMES:
                raise ValueError(f"Access to '{node.attr}' is not allowed")
        self.generic_visit(node)

# Wizard State Manager
class WizardStateManager:
    """Manages wizard state persistence and recovery"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.current_session = None
        self.recovery_cache = {}
    
    def start_wizard(self, wizard_name: str, user_context: dict) -> str:
        """Start a new wizard session with persistence"""
        # Generate session ID
        session_id = self._generate_session_id(wizard_name, user_context)
        
        # Check for existing incomplete session
        existing = self._find_incomplete_session(wizard_name, user_context)
        if existing:
            return existing['session_id']
        
        # Create new session
        initial_state = {
            'wizard_name': wizard_name,
            'user_context': user_context,
            'current_step': 0,
            'step_data': {},
            'history': [],
            'started_at': datetime.datetime.now().isoformat()
        }
        
        expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
        
        self.db.conn.execute('''
            INSERT INTO wizard_states 
            (session_id, wizard_name, current_step, state_data, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, wizard_name, 0, self._serialize_state(initial_state), expires_at))
        self.db.conn.commit()
        
        self.current_session = session_id
        return session_id
    
    def save_step(self, session_id: str, step_name: str, 
                  step_data: Any, next_step: int):
        """Save wizard step progress"""
        # Load current state
        state = self.load_state(session_id)
        if not state:
            raise ValueError(f"Invalid session: {session_id}")
        
        # Update state
        state['step_data'][step_name] = step_data
        state['current_step'] = next_step
        state['history'].append({
            'step': step_name,
            'data': step_data,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        # Save to database
        self.db.conn.execute('''
            UPDATE wizard_states 
            SET state_data = ?, current_step = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (self._serialize_state(state), next_step, session_id))
        self.db.conn.commit()
        
        # Update cache
        self.recovery_cache[session_id] = state
    
    def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load wizard state from persistence"""
        # Check cache first
        if session_id in self.recovery_cache:
            return self.recovery_cache[session_id]
        
        # Load from database
        result = self.db.conn.execute('''
            SELECT state_data, completed, expires_at
            FROM wizard_states
            WHERE session_id = ?
        ''', (session_id,)).fetchone()
        
        if not result:
            return None
        
        state_data, completed, expires_at = result
        
        # Check expiration
        if not completed and datetime.datetime.fromisoformat(expires_at) < datetime.datetime.now():
            self.cleanup_session(session_id)
            return None
        
        # Deserialize and cache
        state = self._deserialize_state(state_data)
        self.recovery_cache[session_id] = state
        return state
    
    def complete_wizard(self, session_id: str, result: Dict[str, Any]):
        """Mark wizard as completed"""
        state = self.load_state(session_id)
        if not state:
            return
        
        state['completed_at'] = datetime.datetime.now().isoformat()
        state['result'] = result
        
        self.db.conn.execute('''
            UPDATE wizard_states
            SET state_data = ?, completed = 1, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (self._serialize_state(state), session_id))
        self.db.conn.commit()
        
        # Remove from cache
        self.recovery_cache.pop(session_id, None)
    
    def cleanup_session(self, session_id: str):
        """Clean up wizard session"""
        self.db.conn.execute('DELETE FROM wizard_states WHERE session_id = ?', 
                       (session_id,))
        self.db.conn.commit()
        self.recovery_cache.pop(session_id, None)
    
    def find_resumable_sessions(self, wizard_name: str, 
                               user_context: dict) -> List[Dict[str, Any]]:
        """Find sessions that can be resumed"""
        results = self.db.conn.execute('''
            SELECT session_id, state_data, updated_at
            FROM wizard_states
            WHERE wizard_name = ? 
                AND completed = 0 
                AND expires_at > datetime('now')
            ORDER BY updated_at DESC
            LIMIT 5
        ''', (wizard_name,)).fetchall()
        
        resumable = []
        for session_id, state_data, updated_at in results:
            state = self._deserialize_state(state_data)
            # Check if context matches (allows resuming)
            if self._contexts_match(state['user_context'], user_context):
                resumable.append({
                    'session_id': session_id,
                    'updated_at': updated_at,
                    'current_step': state['current_step'],
                    'progress': len(state['step_data'])
                })
        
        return resumable
    
    def _generate_session_id(self, wizard_name: str, context: dict) -> str:
        """Generate unique session ID"""
        # Include timestamp for uniqueness
        data = f"{wizard_name}:{str(context)}:{datetime.datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _serialize_state(self, state: Dict[str, Any]) -> str:
        """Serialize state for storage"""
        return base64.b64encode(pickle.dumps(state)).decode('utf-8')
    
    def _deserialize_state(self, state_data: str) -> Dict[str, Any]:
        """Deserialize state from storage"""
        return pickle.loads(base64.b64decode(state_data.encode('utf-8')))
    
    def _contexts_match(self, saved_context: dict, new_context: dict) -> bool:
        """Check if contexts are similar enough to resume"""
        # Compare key fields that matter for resumption
        important_keys = ['phase', 'user_role', 'project_id']
        for key in important_keys:
            if key in saved_context and key in new_context:
                if saved_context[key] != new_context[key]:
                    return False
        return True
    
    def _find_incomplete_session(self, wizard_name: str, 
                                user_context: dict) -> Optional[dict]:
        """Find most recent incomplete session"""
        sessions = self.find_resumable_sessions(wizard_name, user_context)
        return sessions[0] if sessions else None
    
    def cleanup_expired(self):
        """Clean up expired sessions"""
        self.db.conn.execute('''
            DELETE FROM wizard_states
            WHERE completed = 0 AND expires_at < datetime('now')
        ''')
        self.db.conn.commit()

# CLI Interface (enhanced with error handling)
class CLI:
    """Command-line interface handler."""
    
    def __init__(self):
        try:
            self.db = DatabaseManager()
            self.task_manager = TaskManager(self.db)
            self.phase_manager = PhaseManager(self.db, self.task_manager)
            self.message_manager = MessageManager(self.db)
            self.sandbox = SecureExtensionSandbox()
            self.state_manager = WizardStateManager(self.db)
            
            # Store repository info
            repo_detector = RepositoryDetectorFactory.create()
            repo_info = repo_detector.detect()
            
            for key, value in repo_info.items():
                self.db.conn.execute("""
                    INSERT OR REPLACE INTO repository_info (key, value)
                    VALUES (?, ?)
                """, (key, str(value)))
            self.db.conn.commit()
            
        except DiskFullError as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")
            print("Please free up disk space and try again.")
            sys.exit(1)
    
    def run(self, args: Optional[List[str]] = None):
        """Main entry point for CLI."""
        parser = self._create_parser()
        
        try:
            parsed_args = parser.parse_args(args)
            
            # Execute command
            if hasattr(parsed_args, 'func'):
                parsed_args.func(parsed_args)
            else:
                # No command specified - show interactive menu for LLMs
                self._interactive_menu()
                
        except DiskFullError as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")
            print("Tip: Check disk space with 'df -h' command")
        except NetworkTimeoutError as e:
            print(f"{Colors.RED}Network Error: {e}{Colors.RESET}")
            print("Tip: Check your network connection")
        except InvalidEncodingError as e:
            print(f"{Colors.RED}Encoding Error: {e}{Colors.RESET}")
            print("Tip: Ensure your input uses valid UTF-8 encoding")
        except CorruptedDataError as e:
            print(f"{Colors.RED}Data Corruption: {e}{Colors.RESET}")
            print("Tip: Try running database backup/restore")
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")
            if os.environ.get('DEBUG'):
                traceback.print_exc()
            sys.exit(1)
        finally:
            self.db.close()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with all commands."""
        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        parser.add_argument(
            '--version', action='version',
            version=f'%(prog)s {__version__}'
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        
        # Task commands
        task_parser = subparsers.add_parser('task', help='Task management')
        task_subparsers = task_parser.add_subparsers(dest='task_command')
        
        # task add
        add_parser = task_subparsers.add_parser('add', help='Add new task')
        add_parser.add_argument('description', help='Task description')
        add_parser.add_argument('--priority', type=int, default=3,
                                choices=[1, 2, 3, 4, 5],
                                help='Task priority (1=lowest, 5=highest)')
        add_parser.add_argument('--assignee', help='Assign to user/context')
        add_parser.set_defaults(func=self._cmd_task_add)
        
        # task list
        list_parser = task_subparsers.add_parser('list', help='List tasks')
        list_parser.add_argument('--status', choices=['pending', 'in_progress', 'review', 'completed'],
                                 help='Filter by status')
        list_parser.add_argument('--all', action='store_true',
                                 help='Show all tasks including completed')
        list_parser.set_defaults(func=self._cmd_task_list)
        
        # task start
        start_parser = task_subparsers.add_parser('start', help='Start working on task')
        start_parser.add_argument('task_id', type=int, help='Task ID')
        start_parser.set_defaults(func=self._cmd_task_start)
        
        # task finish
        finish_parser = task_subparsers.add_parser('finish', help='Send task to review')
        finish_parser.add_argument('task_id', type=int, help='Task ID')
        finish_parser.add_argument('--comment', help='Review comment')
        finish_parser.set_defaults(func=self._cmd_task_finish)
        
        # task approve
        approve_parser = task_subparsers.add_parser('approve', help='Approve reviewed task')
        approve_parser.add_argument('task_id', type=int, help='Task ID')
        approve_parser.set_defaults(func=self._cmd_task_approve)
        
        # task reject
        reject_parser = task_subparsers.add_parser('reject', help='Reject reviewed task')
        reject_parser.add_argument('task_id', type=int, help='Task ID')
        reject_parser.add_argument('--reason', help='Rejection reason')
        reject_parser.set_defaults(func=self._cmd_task_reject)
        
        # Phase commands
        phase_parser = subparsers.add_parser('phase', help='Phase management')
        phase_subparsers = phase_parser.add_subparsers(dest='phase_command')
        
        # phase new
        new_phase_parser = phase_subparsers.add_parser('new', help='Start new phase')
        new_phase_parser.add_argument('title', help='Phase title')
        new_phase_parser.add_argument('--description', help='Phase description')
        new_phase_parser.set_defaults(func=self._cmd_phase_new)
        
        # phase rename
        rename_parser = phase_subparsers.add_parser('rename', help='Rename current phase')
        rename_parser.add_argument('title', help='New phase title')
        rename_parser.set_defaults(func=self._cmd_phase_rename)
        
        # phase list
        phase_list_parser = phase_subparsers.add_parser('list', help='List all phases')
        phase_list_parser.set_defaults(func=self._cmd_phase_list)
        
        # Message commands
        msg_parser = subparsers.add_parser('message', help='Message management')
        msg_subparsers = msg_parser.add_subparsers(dest='msg_command')
        
        # message send
        send_parser = msg_subparsers.add_parser('send', help='Send message')
        send_parser.add_argument('content', help='Message content')
        send_parser.add_argument('--from', dest='from_context', default='CLI',
                                 help='Sender context')
        send_parser.add_argument('--to', dest='to_context',
                                 help='Recipient context (optional)')
        send_parser.add_argument('--priority', default='normal',
                                 choices=['low', 'normal', 'high', 'urgent'],
                                 help='Message priority')
        send_parser.add_argument('--tags', nargs='+', help='Message tags')
        send_parser.set_defaults(func=self._cmd_message_send)
        
        # message list
        msg_list_parser = msg_subparsers.add_parser('list', help='List messages')
        msg_list_parser.add_argument('--unread', action='store_true',
                                     help='Show only unread messages')
        msg_list_parser.set_defaults(func=self._cmd_message_list)
        
        # message read
        read_parser = msg_subparsers.add_parser('read', help='Read message')
        read_parser.add_argument('message_id', type=int, help='Message ID')
        read_parser.set_defaults(func=self._cmd_message_read)
        
        # Status command
        status_parser = subparsers.add_parser('status', help='Show overall status')
        status_parser.set_defaults(func=self._cmd_status)
        
        # Backup command
        backup_parser = subparsers.add_parser('backup', help='Backup database')
        backup_parser.set_defaults(func=self._cmd_backup)
        
        return parser
    
    def _interactive_menu(self):
        """Interactive menu designed for LLM operation."""
        self._print_header()
        
        print(f"\n{Colors.CYAN}Welcome to PyTask v{__version__}!{Colors.RESET}")
        print("This is the interactive mode designed for LLM operation.")
        print("\nI'll guide you through your options step by step.")
        
        # Platform info
        print(f"\n{Colors.BOLD}Platform Info:{Colors.RESET}")
        print(f"Python: {sys.version.split()[0]}")
        print(f"OS: {platform.system()} {platform.release()}")
        print(f"Terminal: {terminal.color_support.name} color support")
        
        # Check for unread messages
        unread = self.message_manager.list_messages(unread_only=True)
        if unread:
            print(f"\n{Colors.RED}{Colors.BOLD}{terminal.symbols['info']} You have {len(unread)} unread message(s)!{Colors.RESET}")
            print(f"Type {Colors.CYAN}1{Colors.RESET} to read messages")
        
        # Show current status
        stats = self.task_manager.get_task_statistics()
        phase = self.phase_manager.get_current_phase()
        
        print(f"\n{Colors.BOLD}Current Status:{Colors.RESET}")
        print(f"Phase: {phase.title if phase else 'None'}")
        print(f"Tasks: {stats['pending']} pending, {stats['in_progress']} active, "
              f"{stats['review']} in review, {stats['completed']} completed")
        
        # Menu options
        print(f"\n{Colors.BOLD}What would you like to do?{Colors.RESET}")
        print(f"\n{Colors.YELLOW}Task Management:{Colors.RESET}")
        print("1. Read messages (if any)")
        print("2. View all active tasks")
        print("3. Add a new task")
        print("4. Start working on a task")
        print("5. Finish current task (send to review)")
        print("6. Review and approve tasks")
        
        print(f"\n{Colors.MAGENTA}Phase Management:{Colors.RESET}")
        print("7. View current phase details")
        print("8. Start a new phase (if board is clear)")
        
        print(f"\n{Colors.GREEN}Other Options:{Colors.RESET}")
        print("9. Show detailed status report")
        print("10. Leave a message for the next LLM")
        print("11. Create database backup")
        print("12. Exit")
        
        print(f"\n{Colors.CYAN}Enter your choice (1-12):{Colors.RESET} ", end='')
        sys.stdout.flush()
        
        # In non-interactive mode, just show the menu and exit
        if not sys.stdin.isatty():
            print("\n(Running in non-interactive mode. Use command-line arguments instead.)")
            return
        
        try:
            choice = input().strip()
            self._handle_menu_choice(choice)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
    
    def _handle_menu_choice(self, choice: str):
        """Handle interactive menu choice."""
        actions = {
            '1': self._interactive_read_messages,
            '2': self._interactive_list_tasks,
            '3': self._interactive_add_task,
            '4': self._interactive_start_task,
            '5': self._interactive_finish_task,
            '6': self._interactive_review_tasks,
            '7': self._interactive_phase_details,
            '8': self._interactive_new_phase,
            '9': self._interactive_status_report,
            '10': self._interactive_leave_message,
            '11': self._interactive_backup,
            '12': lambda: print("Goodbye!")
        }
        
        action = actions.get(choice)
        if action:
            action()
        else:
            print(f"{Colors.RED}Invalid choice. Please try again.{Colors.RESET}")
            self._interactive_menu()
    
    def _print_header(self):
        """Print phase header."""
        phase = self.phase_manager.get_current_phase()
        if phase:
            print(f"\n{Colors.INVERSE}{Colors.BOLD} Phase {phase.number}: {phase.title} {Colors.RESET}\n")
    
    # Command implementations
    def _cmd_task_add(self, args):
        """Add new task command."""
        task = self.task_manager.create_task(
            description=args.description,
            priority=args.priority,
            assignee=args.assignee
        )
        print(f"{Colors.GREEN}{terminal.symbols['check']} Task #{task.id} added: {task.description}{Colors.RESET}")
    
    def _cmd_task_list(self, args):
        """List tasks command."""
        if args.all:
            tasks = self.task_manager.list_tasks()
        else:
            # Show only active tasks by default
            tasks = [t for t in self.task_manager.list_tasks()
                     if t.status != TaskStatus.COMPLETED.value]
        
        if args.status:
            tasks = [t for t in tasks if t.status == args.status]
        
        # Group by status
        by_status = defaultdict(list)
        for task in tasks:
            by_status[task.status].append(task)
        
        # Display
        for status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, 
                       TaskStatus.REVIEW, TaskStatus.COMPLETED]:
            if status.value in by_status:
                color = {
                    TaskStatus.PENDING: Colors.BLUE,
                    TaskStatus.IN_PROGRESS: Colors.YELLOW,
                    TaskStatus.REVIEW: Colors.MAGENTA,
                    TaskStatus.COMPLETED: Colors.GREEN
                }[status]
                
                print(f"\n{color}{Colors.BOLD}{terminal.symbols['bullet']} {status.value.replace('_', ' ').title()} "
                      f"({len(by_status[status.value])}){Colors.RESET}")
                
                for task in by_status[status.value]:
                    icon = {
                        TaskStatus.PENDING: "",
                        TaskStatus.IN_PROGRESS: terminal.symbols['arrow'],
                        TaskStatus.REVIEW: terminal.symbols['info'],
                        TaskStatus.COMPLETED: terminal.symbols['check']
                    }[status]
                    
                    print(f"  {color}#{task.id}{Colors.RESET} {icon} {task.description}")
                    if task.assignee:
                        print(f"     Assignee: {task.assignee}")
    
    def _cmd_task_start(self, args):
        """Start task command."""
        task = self.task_manager.update_task_status(
            args.task_id, TaskStatus.IN_PROGRESS.value
        )
        print(f"{Colors.YELLOW}{terminal.symbols['arrow']} Task #{task.id} started: {task.description}{Colors.RESET}")
    
    def _cmd_task_finish(self, args):
        """Finish task command."""
        task = self.task_manager.update_task_status(
            args.task_id, TaskStatus.REVIEW.value, args.comment
        )
        print(f"{Colors.MAGENTA}{terminal.symbols['info']} Task #{task.id} sent to review{Colors.RESET}")
    
    def _cmd_task_approve(self, args):
        """Approve task command."""
        task = self.task_manager.update_task_status(
            args.task_id, TaskStatus.COMPLETED.value
        )
        print(f"{Colors.GREEN}{terminal.symbols['check']} Task #{task.id} approved and completed{Colors.RESET}")
    
    def _cmd_task_reject(self, args):
        """Reject task command."""
        task = self.task_manager.update_task_status(
            args.task_id, TaskStatus.PENDING.value,
            args.reason or "Needs more work"
        )
        print(f"{Colors.RED}{terminal.symbols['cross']} Task #{task.id} rejected{Colors.RESET}")
    
    def _cmd_phase_new(self, args):
        """Create new phase command."""
        try:
            phase = self.phase_manager.create_phase(args.title, args.description)
            print(f"{Colors.GREEN}{terminal.symbols['check']} Started Phase {phase.number}: {phase.title}{Colors.RESET}")
        except ValueError as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")
            
            # Provide helpful guidance
            stats = self.task_manager.get_task_statistics()
            if stats['active'] > 0:
                print("\nActive tasks must be completed first:")
                self._cmd_task_list(argparse.Namespace(all=False, status=None))
            elif stats['total'] == 0:
                print("\nYou need to add tasks to the current phase first.")
                print(f"Use: {Colors.CYAN}task add \"description\"{Colors.RESET}")
    
    def _cmd_phase_rename(self, args):
        """Rename current phase command."""
        phase = self.phase_manager.rename_current_phase(args.title)
        print(f"{Colors.GREEN}{terminal.symbols['check']} Renamed phase to: Phase {phase.number}: {phase.title}{Colors.RESET}")
    
    def _cmd_phase_list(self, args):
        """List all phases command."""
        phases = self.phase_manager.list_phases()
        
        for phase in phases:
            summary = self.phase_manager.get_phase_summary(phase.id)
            status_icon = terminal.symbols['check'] if phase.status == "completed" else terminal.symbols['arrow']
            
            print(f"\n{Colors.BOLD}{status_icon} Phase {phase.number}: {phase.title}{Colors.RESET}")
            print(f"   Status: {phase.status}")
            print(f"   Tasks: {summary['task_count']} total, "
                  f"{summary['completed_tasks']} completed")
            
            if phase.description:
                print(f"   Description: {phase.description}")
    
    def _cmd_message_send(self, args):
        """Send message command."""
        message = self.message_manager.send_message(
            content=args.content,
            from_context=args.from_context,
            to_context=args.to_context,
            priority=args.priority,
            tags=args.tags
        )
        print(f"{Colors.GREEN}{terminal.symbols['check']} Message sent (ID: {message.id}){Colors.RESET}")
    
    def _cmd_message_list(self, args):
        """List messages command."""
        messages = self.message_manager.list_messages(unread_only=args.unread)
        
        if not messages:
            print("No messages found.")
            return
        
        for msg in messages:
            icon = terminal.symbols['info'] if msg.read_at is None else terminal.symbols['check']
            priority_color = {
                'low': Colors.BLUE,
                'normal': Colors.RESET,
                'high': Colors.YELLOW,
                'urgent': Colors.RED
            }[msg.priority]
            
            print(f"\n{icon} Message #{msg.id} [{priority_color}{msg.priority}{Colors.RESET}]")
            print(f"   From: {msg.from_context}")
            if msg.to_context:
                print(f"   To: {msg.to_context}")
            print(f"   Date: {msg.created_at}")
            if msg.tags:
                print(f"   Tags: {', '.join(msg.tags)}")
            print(f"   {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}")
    
    def _cmd_message_read(self, args):
        """Read message command."""
        message = self.message_manager.get_message(args.message_id)
        if not message:
            print(f"{Colors.RED}Message not found{Colors.RESET}")
            return
        
        # Display message
        print(f"\n{Colors.CYAN}{Colors.BOLD}{terminal.symbols['info']} Message #{message.id}{Colors.RESET}")
        print(f"{Colors.BOLD}From:{Colors.RESET} {message.from_context}")
        if message.to_context:
            print(f"{Colors.BOLD}To:{Colors.RESET} {message.to_context}")
        print(f"{Colors.BOLD}Date:{Colors.RESET} {message.created_at}")
        print(f"{Colors.BOLD}Priority:{Colors.RESET} {message.priority}")
        if message.tags:
            print(f"{Colors.BOLD}Tags:{Colors.RESET} {', '.join(message.tags)}")
        print(f"{Colors.BOLD}{'-' * 50}{Colors.RESET}")
        print(message.content)
        print(f"{Colors.BOLD}{'-' * 50}{Colors.RESET}")
        
        # Mark as read
        self.message_manager.mark_as_read(args.message_id)
    
    def _cmd_status(self, args):
        """Show status command."""
        # Repository info
        repo_info = {}
        rows = self.db.conn.execute("SELECT key, value FROM repository_info").fetchall()
        for row in rows:
            repo_info[row['key']] = row['value']
        
        print(f"{Colors.BOLD}Repository Information:{Colors.RESET}")
        print(f"Type: {repo_info.get('type', 'unknown')}")
        print(f"Root: {repo_info.get('root', 'unknown')}")
        if repo_info.get('type') != 'none':
            if repo_info.get('branch'):
                print(f"Branch: {repo_info.get('branch', 'unknown')}")
            if repo_info.get('url'):
                print(f"URL: {repo_info.get('url', 'unknown')}")
            print(f"Clean: {repo_info.get('clean', 'unknown')}")
        if repo_info.get('error'):
            print(f"Error: {repo_info.get('error')}")
        
        # Disk space
        try:
            stat = shutil.disk_usage('.')
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            print(f"\n{Colors.BOLD}Disk Space:{Colors.RESET}")
            print(f"Free: {free_gb:.1f}GB / {total_gb:.1f}GB ({stat.free/stat.total*100:.1f}% free)")
        except:
            pass
        
        # Phase info
        phase = self.phase_manager.get_current_phase()
        print(f"\n{Colors.BOLD}Current Phase:{Colors.RESET}")
        if phase:
            print(f"Phase {phase.number}: {phase.title}")
            summary = self.phase_manager.get_phase_summary(phase.id)
            print(f"Tasks: {summary['task_count']} total, "
                  f"{summary['completed_tasks']} completed")
        
        # Task statistics
        stats = self.task_manager.get_task_statistics()
        print(f"\n{Colors.BOLD}Task Statistics:{Colors.RESET}")
        print(f"Total: {stats['total']}")
        print(f"Pending: {stats['pending']}")
        print(f"In Progress: {stats['in_progress']}")
        print(f"In Review: {stats['review']}")
        print(f"Completed: {stats['completed']}")
        
        # Messages
        unread = self.message_manager.list_messages(unread_only=True)
        total_messages = len(self.message_manager.list_messages())
        print(f"\n{Colors.BOLD}Messages:{Colors.RESET}")
        print(f"Total: {total_messages}, Unread: {len(unread)}")
        
        # Suggestions
        print(f"\n{Colors.BOLD}Suggested Next Steps:{Colors.RESET}")
        if unread:
            print(f"{terminal.symbols['bullet']} Read your {len(unread)} unread message(s)")
        if stats['review'] > 0:
            print(f"{terminal.symbols['bullet']} Review {stats['review']} task(s) awaiting approval")
        if stats['in_progress'] == 0 and stats['pending'] > 0:
            print(f"{terminal.symbols['bullet']} Start working on one of {stats['pending']} pending task(s)")
        if stats['total'] == stats['completed'] and stats['total'] > 0:
            print("{terminal.symbols['bullet']} Consider starting a new phase")
    
    def _cmd_backup(self, args):
        """Create database backup."""
        try:
            backup_path = self.db.backup()
            print(f"{Colors.GREEN}{terminal.symbols['check']} Backup created: {backup_path}{Colors.RESET}")
        except DiskFullError as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")
            print("Please free up disk space and try again.")
    
    # Interactive implementations
    def _interactive_read_messages(self):
        """Interactive message reading."""
        messages = self.message_manager.list_messages(unread_only=True)
        if not messages:
            print("No unread messages.")
            return
        
        for msg in messages:
            self._cmd_message_read(argparse.Namespace(message_id=msg.id))
            print(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            input()
    
    def _interactive_list_tasks(self):
        """Interactive task listing."""
        self._cmd_task_list(argparse.Namespace(all=False, status=None))
    
    def _interactive_add_task(self):
        """Interactive task addition."""
        print(f"\n{Colors.CYAN}Adding a new task{Colors.RESET}")
        print("What needs to be done?")
        description = input("> ").strip()
        
        if description:
            task = self.task_manager.create_task(description)
            print(f"{Colors.GREEN}{terminal.symbols['check']} Task #{task.id} added!{Colors.RESET}")
    
    def _interactive_start_task(self):
        """Interactive task start."""
        pending = self.task_manager.list_tasks(status=TaskStatus.PENDING.value)
        if not pending:
            print("No pending tasks to start.")
            return
        
        print(f"\n{Colors.CYAN}Which task would you like to start?{Colors.RESET}")
        for task in pending:
            print(f"  #{task.id} - {task.description}")
        
        task_id = input("\nEnter task ID: ").strip()
        if task_id.isdigit():
            self._cmd_task_start(argparse.Namespace(task_id=int(task_id)))
    
    def _interactive_finish_task(self):
        """Interactive task finish."""
        in_progress = self.task_manager.list_tasks(status=TaskStatus.IN_PROGRESS.value)
        if not in_progress:
            print("No tasks in progress to finish.")
            return
        
        print(f"\n{Colors.CYAN}Which task would you like to finish?{Colors.RESET}")
        for task in in_progress:
            print(f"  #{task.id} - {task.description}")
        
        task_id = input("\nEnter task ID: ").strip()
        if task_id.isdigit():
            comment = input("Any comments for review? (optional): ").strip()
            self._cmd_task_finish(argparse.Namespace(
                task_id=int(task_id),
                comment=comment if comment else None
            ))
    
    def _interactive_review_tasks(self):
        """Interactive task review."""
        review_tasks = self.task_manager.list_tasks(status=TaskStatus.REVIEW.value)
        if not review_tasks:
            print("No tasks pending review.")
            return
        
        for task in review_tasks:
            print(f"\n{Colors.MAGENTA}Reviewing Task #{task.id}{Colors.RESET}")
            print(f"Description: {task.description}")
            if task.review_comment:
                print(f"Comment: {task.review_comment}")
            if task.commit_hash:
                print(f"Commit: {task.commit_hash[:8]}")
            
            action = input("\nApprove (a) or Reject (r)? ").strip().lower()
            if action == 'a':
                self._cmd_task_approve(argparse.Namespace(task_id=task.id))
            elif action == 'r':
                reason = input("Rejection reason: ").strip()
                self._cmd_task_reject(argparse.Namespace(
                    task_id=task.id,
                    reason=reason if reason else None
                ))
    
    def _interactive_phase_details(self):
        """Show current phase details."""
        phase = self.phase_manager.get_current_phase()
        if phase:
            summary = self.phase_manager.get_phase_summary(phase.id)
            print(f"\n{Colors.BOLD}Phase {phase.number}: {phase.title}{Colors.RESET}")
            print(f"Status: {phase.status}")
            print(f"Started: {phase.created_at}")
            print(f"\nTasks: {summary['task_count']} total")
            for status, count in summary['tasks_by_status'].items():
                print(f"  {status}: {count}")
    
    def _interactive_new_phase(self):
        """Interactive new phase creation."""
        # Check if we can create a new phase
        stats = self.task_manager.get_task_statistics()
        if stats['active'] > 0:
            print(f"{Colors.RED}Cannot start new phase with active tasks.{Colors.RESET}")
            return
        
        print(f"\n{Colors.CYAN}Starting a new phase{Colors.RESET}")
        title = input("Phase title: ").strip()
        description = input("Phase description (optional): ").strip()
        
        if title:
            self._cmd_phase_new(argparse.Namespace(
                title=title,
                description=description if description else None
            ))
    
    def _interactive_status_report(self):
        """Show detailed status report."""
        self._cmd_status(argparse.Namespace())
    
    def _interactive_leave_message(self):
        """Leave a message for the next LLM."""
        print(f"\n{Colors.CYAN}Leave a message for the next LLM{Colors.RESET}")
        print("Your message will help the next context understand what's happening.")
        
        content = input("Message: ").strip()
        if content:
            message = self.message_manager.send_message(
                content=content,
                from_context=os.environ.get('USER', 'Human'),
                priority='normal'
            )
            print(f"{Colors.GREEN}{terminal.symbols['check']} Message saved!{Colors.RESET}")
    
    def _interactive_backup(self):
        """Create database backup interactively."""
        print(f"\n{Colors.CYAN}Creating database backup...{Colors.RESET}")
        self._cmd_backup(argparse.Namespace())


# Entry point
def main():
    """Main entry point."""
    try:
        cli = CLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        if os.environ.get('DEBUG'):
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()