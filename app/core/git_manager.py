"""
Lutervyn IDE - Git Manager
Wraps git CLI commands for source control integration.
"""

import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class GitFileStatus:
    """Represents a single file's git status."""
    path: str               # relative path from repo root
    abs_path: str            # absolute path
    index_status: str        # status in staging area  (X)
    work_status: str         # status in working tree  (Y)
    old_path: str = ""       # original path for renames

    @property
    def display_status(self) -> str:
        """Single-letter status for display (like VS Code)."""
        # Staged status
        if self.index_status in ('A',):
            return 'A'
        if self.index_status in ('M',):
            return 'M'
        if self.index_status in ('D',):
            return 'D'
        if self.index_status in ('R',):
            return 'R'
        if self.index_status in ('C',):
            return 'C'
        # Working tree status
        if self.work_status == '?':
            return 'U'  # Untracked
        if self.work_status == 'M':
            return 'M'
        if self.work_status == 'D':
            return 'D'
        if self.work_status == 'A':
            return 'A'
        return '?'

    @property
    def is_staged(self) -> bool:
        return self.index_status not in (' ', '?', '!')

    @property
    def is_unstaged(self) -> bool:
        return self.work_status not in (' ', '!')

    @property
    def is_untracked(self) -> bool:
        return self.index_status == '?' and self.work_status == '?'

    @property
    def is_conflict(self) -> bool:
        return self.index_status == 'U' or self.work_status == 'U'


@dataclass
class GitBranchInfo:
    name: str
    is_current: bool = False
    tracking: str = ""
    ahead: int = 0
    behind: int = 0


@dataclass
class GitStashEntry:
    index: int
    message: str


@dataclass
class GitLogEntry:
    hash: str
    short_hash: str
    author: str
    date: str
    message: str


class GitManager:
    """Manages git operations for a workspace folder."""

    def __init__(self):
        self._repo_root: Optional[str] = None
        self._git_exe = "git"

    # ── Core helpers ──────────────────────────────────────────────

    def _run(self, args: List[str], cwd: str = None,
             check: bool = True, timeout: int = 15) -> subprocess.CompletedProcess:
        """Run a git command and return the result."""
        cmd = [self._git_exe] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self._repo_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            if check and result.returncode != 0:
                raise GitError(result.stderr.strip() or result.stdout.strip())
            return result
        except FileNotFoundError:
            raise GitError("Git is not installed or not in PATH.")
        except subprocess.TimeoutExpired:
            raise GitError("Git command timed out.")

    # ── Repository detection ──────────────────────────────────────

    def is_git_installed(self) -> bool:
        try:
            subprocess.run(
                [self._git_exe, "--version"],
                capture_output=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def detect_repo(self, folder: str) -> Optional[str]:
        """Detect git repo root for the given folder. Returns root path or None."""
        try:
            r = self._run(
                ["rev-parse", "--show-toplevel"],
                cwd=folder, check=False
            )
            if r.returncode == 0:
                root = r.stdout.strip().replace("/", os.sep)
                self._repo_root = root
                return root
        except GitError:
            pass
        return None

    def init_repo(self, folder: str) -> str:
        """Initialize a new git repository."""
        r = self._run(["init"], cwd=folder)
        self._repo_root = folder
        return r.stdout.strip()

    @property
    def repo_root(self) -> Optional[str]:
        return self._repo_root

    # ── Branch operations ─────────────────────────────────────────

    def current_branch(self) -> str:
        """Get the current branch name."""
        if not self._repo_root:
            return ""
        try:
            r = self._run(["branch", "--show-current"])
            name = r.stdout.strip()
            if not name:
                # Detached HEAD
                r2 = self._run(["rev-parse", "--short", "HEAD"], check=False)
                return f"HEAD detached at {r2.stdout.strip()}" if r2.returncode == 0 else "HEAD (no commits)"
            return name
        except GitError:
            return "main"

    def list_branches(self) -> List[GitBranchInfo]:
        """List all local branches."""
        if not self._repo_root:
            return []
        try:
            r = self._run(["branch", "-vv", "--no-color"])
            branches = []
            for line in r.stdout.splitlines():
                is_current = line.startswith("*")
                name = line[2:].split()[0]
                tracking = ""
                ahead, behind = 0, 0
                if "[" in line:
                    bracket = line[line.index("[") + 1:line.index("]")]
                    parts = bracket.split(":")
                    tracking = parts[0].strip()
                    if len(parts) > 1:
                        info = parts[1].strip()
                        if "ahead" in info:
                            try:
                                ahead = int(info.split("ahead")[1].split(",")[0].strip())
                            except (ValueError, IndexError):
                                pass
                        if "behind" in info:
                            try:
                                behind = int(info.split("behind")[1].split(",")[0].strip().rstrip("]"))
                            except (ValueError, IndexError):
                                pass
                branches.append(GitBranchInfo(name, is_current, tracking, ahead, behind))
            return branches
        except GitError:
            return []

    def checkout_branch(self, branch_name: str):
        """Switch to a branch."""
        self._run(["checkout", branch_name])

    def create_branch(self, branch_name: str, checkout: bool = True):
        """Create a new branch."""
        if checkout:
            self._run(["checkout", "-b", branch_name])
        else:
            self._run(["branch", branch_name])

    # ── Status ────────────────────────────────────────────────────

    def status(self) -> List[GitFileStatus]:
        """Get working tree status (porcelain v1 format)."""
        if not self._repo_root:
            return []
        try:
            r = self._run(["status", "--porcelain", "-u"])
            files = []
            for line in r.stdout.splitlines():
                if len(line) < 4:
                    continue
                x = line[0]  # index status
                y = line[1]  # work tree status
                path = line[3:]

                old_path = ""
                if " -> " in path:
                    old_path, path = path.split(" -> ", 1)

                abs_path = os.path.join(self._repo_root, path.replace("/", os.sep))
                files.append(GitFileStatus(
                    path=path,
                    abs_path=abs_path,
                    index_status=x,
                    work_status=y,
                    old_path=old_path,
                ))
            return files
        except GitError:
            return []

    def get_staged_files(self) -> List[GitFileStatus]:
        """Get only staged files."""
        return [f for f in self.status() if f.is_staged]

    def get_unstaged_files(self) -> List[GitFileStatus]:
        """Get only unstaged (modified/deleted) files, excluding untracked."""
        return [f for f in self.status()
                if f.is_unstaged and not f.is_untracked]

    def get_untracked_files(self) -> List[GitFileStatus]:
        """Get only untracked files."""
        return [f for f in self.status() if f.is_untracked]

    # ── Staging ───────────────────────────────────────────────────

    def stage_file(self, path: str):
        """Stage a single file (git add)."""
        self._run(["add", "--", path])

    def stage_all(self):
        """Stage all changes."""
        self._run(["add", "-A"])

    def unstage_file(self, path: str):
        """Unstage a single file (git reset HEAD)."""
        self._run(["reset", "HEAD", "--", path], check=False)

    def unstage_all(self):
        """Unstage all staged files."""
        self._run(["reset", "HEAD"], check=False)

    # ── Discard ───────────────────────────────────────────────────

    def discard_file(self, path: str):
        """Discard changes for a tracked file (git checkout --)."""
        self._run(["checkout", "--", path])

    def discard_untracked(self, path: str):
        """Remove an untracked file."""
        abs_path = os.path.join(self._repo_root, path.replace("/", os.sep))
        if os.path.isfile(abs_path):
            os.remove(abs_path)
        elif os.path.isdir(abs_path):
            import shutil
            shutil.rmtree(abs_path, ignore_errors=True)

    # ── Commit ────────────────────────────────────────────────────

    def commit(self, message: str, amend: bool = False) -> str:
        """Create a commit. Returns the commit output."""
        args = ["commit", "-m", message]
        if amend:
            args.append("--amend")
        r = self._run(args)
        return r.stdout.strip()

    # ── Remote / Push / Pull ──────────────────────────────────────

    def get_remotes(self) -> List[str]:
        """List remote names."""
        try:
            r = self._run(["remote"])
            return [line.strip() for line in r.stdout.splitlines() if line.strip()]
        except GitError:
            return []

    def push(self, remote: str = "origin", branch: str = None,
             set_upstream: bool = False) -> str:
        """Push to remote."""
        args = ["push"]
        if set_upstream:
            args.append("-u")
        args.append(remote)
        if branch:
            args.append(branch)
        r = self._run(args, timeout=30)
        return (r.stdout + r.stderr).strip()

    def pull(self, remote: str = "origin", branch: str = None) -> str:
        """Pull from remote."""
        args = ["pull", remote]
        if branch:
            args.append(branch)
        r = self._run(args, timeout=30)
        return (r.stdout + r.stderr).strip()

    def fetch(self, remote: str = "origin") -> str:
        """Fetch from remote."""
        r = self._run(["fetch", remote], timeout=30)
        return (r.stdout + r.stderr).strip()

    # ── Diff ──────────────────────────────────────────────────────

    def diff_file(self, path: str, staged: bool = False) -> str:
        """Get diff for a single file."""
        args = ["diff"]
        if staged:
            args.append("--cached")
        args += ["--", path]
        r = self._run(args, check=False)
        return r.stdout

    def diff_stat(self) -> str:
        """Get a short diff stat."""
        r = self._run(["diff", "--stat"], check=False)
        return r.stdout

    # ── Log ───────────────────────────────────────────────────────

    def log(self, count: int = 20) -> List[GitLogEntry]:
        """Get recent commits."""
        try:
            r = self._run([
                "log", f"-{count}",
                "--format=%H%n%h%n%an%n%ar%n%s",
                "--no-color"
            ])
            entries = []
            lines = r.stdout.strip().split("\n")
            for i in range(0, len(lines) - 4, 5):
                entries.append(GitLogEntry(
                    hash=lines[i],
                    short_hash=lines[i + 1],
                    author=lines[i + 2],
                    date=lines[i + 3],
                    message=lines[i + 4],
                ))
            return entries
        except GitError:
            return []

    # ── Stash ─────────────────────────────────────────────────────

    def stash_push(self, message: str = "") -> str:
        args = ["stash", "push"]
        if message:
            args += ["-m", message]
        r = self._run(args)
        return r.stdout.strip()

    def stash_pop(self) -> str:
        r = self._run(["stash", "pop"])
        return r.stdout.strip()

    def stash_list(self) -> List[GitStashEntry]:
        try:
            r = self._run(["stash", "list"])
            entries = []
            for line in r.stdout.splitlines():
                if ":" in line:
                    idx = int(line.split("{")[1].split("}")[0])
                    msg = line.split(":", 2)[-1].strip()
                    entries.append(GitStashEntry(idx, msg))
            return entries
        except GitError:
            return []

    # ── Ahead/Behind ──────────────────────────────────────────────

    def ahead_behind(self) -> Tuple[int, int]:
        """Get ahead/behind count vs upstream."""
        try:
            r = self._run(["rev-list", "--left-right", "--count", "@{upstream}...HEAD"],
                          check=False)
            if r.returncode == 0:
                parts = r.stdout.strip().split()
                if len(parts) == 2:
                    return int(parts[1]), int(parts[0])  # ahead, behind
        except GitError:
            pass
        return 0, 0

    # ── Config ────────────────────────────────────────────────────

    def get_user_name(self) -> str:
        try:
            r = self._run(["config", "user.name"], check=False)
            return r.stdout.strip()
        except GitError:
            return ""

    def get_user_email(self) -> str:
        try:
            r = self._run(["config", "user.email"], check=False)
            return r.stdout.strip()
        except GitError:
            return ""


class GitError(Exception):
    """Custom exception for git errors."""
    pass
