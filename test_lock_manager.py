import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from typing import Generator
from lock_manager import LockManager, is_lock_stale

@pytest.fixture
def lock_manager() -> Generator[LockManager, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield LockManager(temp_dir)

def test_acquire_and_release_lock(lock_manager: LockManager) -> None:
    assert lock_manager.acquire_lock("test_lock")
    assert lock_manager.is_locked("test_lock")
    lock_manager.release_lock("test_lock")
    assert not lock_manager.is_locked("test_lock")

def test_acquire_existing_lock(lock_manager: LockManager) -> None:
    assert lock_manager.acquire_lock("test_lock")
    assert not lock_manager.acquire_lock("test_lock")

@patch('lock_manager.is_pid_running')
def test_stale_lock_recovery(mock_is_pid_running: MagicMock, lock_manager: LockManager) -> None:
    # Simulate a stale lock
    mock_is_pid_running.return_value = False
    lock_manager.acquire_lock("test_lock")

    # Another process should be able to acquire the lock
    assert lock_manager.acquire_lock("test_lock")

def test_multiple_locks(lock_manager: LockManager) -> None:
    assert lock_manager.acquire_lock("lock1")
    assert lock_manager.acquire_lock("lock2")
    assert lock_manager.is_locked("lock1")
    assert lock_manager.is_locked("lock2")
    lock_manager.release_lock("lock1")
    assert not lock_manager.is_locked("lock1")
    assert lock_manager.is_locked("lock2")

def test_get_lock_owner(lock_manager: LockManager) -> None:
    lock_manager.acquire_lock("test_lock")
    assert lock_manager.get_lock_owner("test_lock") == os.getpid()
    lock_manager.release_lock("test_lock")
    assert lock_manager.get_lock_owner("test_lock") is None

@patch('lock_manager.is_pid_running')
@pytest.mark.parametrize("pid_running,expected", [
    (True, False),
    (False, True)
])
def test_is_lock_stale(mock_is_pid_running: MagicMock, pid_running: bool, expected: bool) -> None:
    mock_is_pid_running.return_value = pid_running
    assert is_lock_stale(1234) == expected
    # if is_pid_running returns True, then is_lcok stale returns False, which matches expected
    # vice-versa

def test_invalid_lock_file(lock_manager: LockManager) -> None:
    lock_path: str = lock_manager._get_lock_path("invalid_lock")
    with open(lock_path, 'w') as f:
        f.write("invalid_pid")

    # Should treat invalid lock file as not locked
    assert not lock_manager.is_locked("invalid_lock")

    # Should be able to acquire lock with invalid lock file
    assert lock_manager.acquire_lock("invalid_lock")

@patch('lock_manager.is_pid_running')
def test_concurrent_lock_attempts(mock_is_pid_running: MagicMock, lock_manager: LockManager) -> None:
    mock_is_pid_running.return_value = True

    # Simulate two processes trying to acquire the same lock
    assert lock_manager.acquire_lock("concurrent_lock")
    assert not lock_manager.acquire_lock("concurrent_lock")

    # Simulate the first process ending
    mock_is_pid_running.return_value = False

    # Now the second process should be able to acquire the lock
    assert lock_manager.acquire_lock("concurrent_lock")
