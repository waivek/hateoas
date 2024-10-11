import os
import psutil
from typing import Optional

# Functional Core

def is_pid_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    return psutil.pid_exists(pid)

def is_lock_stale(pid: int) -> bool:
    """Determine if a lock is stale based on its PID."""
    return not is_pid_running(pid)

# Imperative Shell

class LockManager:
    def __init__(self, lock_dir: str) -> None:
        self.lock_dir: str = lock_dir
        os.makedirs(lock_dir, exist_ok=True)

    def _get_lock_path(self, lock_name: str) -> str:
        return os.path.join(self.lock_dir, f"{lock_name}.lock")

    def acquire_lock(self, lock_name: str) -> bool:
        lock_path: str = self._get_lock_path(lock_name)
        pid: int = os.getpid()

        if os.path.exists(lock_path):
            with open(lock_path, 'r') as f:
                try:
                    locked_pid: int = int(f.read().strip())
                    if not is_lock_stale(locked_pid):
                        return False
                except ValueError:
                    pass  # Treat invalid PID as a stale lock

            # If we reach here, the lock is stale or invalid
            self.release_lock(lock_name)

        with open(lock_path, 'w') as f:
            f.write(str(pid))
        return True

    def release_lock(self, lock_name: str) -> None:
        lock_path: str = self._get_lock_path(lock_name)
        if os.path.exists(lock_path):
            os.remove(lock_path)

    def is_locked(self, lock_name: str) -> bool:
        lock_path: str = self._get_lock_path(lock_name)
        if not os.path.exists(lock_path):
            return False
        with open(lock_path, 'r') as f:
            try:
                locked_pid: int = int(f.read().strip())
                return is_pid_running(locked_pid)
            except ValueError:
                return False  # Invalid PID in lock file

    def get_lock_owner(self, lock_name: str) -> Optional[int]:
        lock_path: str = self._get_lock_path(lock_name)
        if not os.path.exists(lock_path):
            return None
        with open(lock_path, 'r') as f:
            try:
                locked_pid: int = int(f.read().strip())
                return locked_pid if is_pid_running(locked_pid) else None
            except ValueError:
                return None
