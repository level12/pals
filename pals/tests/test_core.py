import datetime as dt
import gc
import os
import random
import string

import pytest

import pals

# Default URL will work for CI tests
db_url = os.environ.get('PALS_DB_URL', 'postgresql://postgres:password@localhost/postgres')


def random_str(length):
    return ''.join(random.choice(string.printable) for _ in range(25))


class TestLocker:

    def test_lock_num_generation(self):
        """
            Create 5000 random strings of varying lengths, convert them to their lock number, and
            make sure we still have 5000 unique numbers.  Given that any application using locking
            is probably going to have, at most, locks numbering in the tens or very low hundreds,
            this seems like an ok way to test that the method we are using to convert our strings
            into numbers is unlikely to have accidental collisions.
        """
        locker = pals.Locker('TestLocker', db_url)

        names = [random_str(max(6, x % 25)) for x in range(5000)]
        assert len(set(names)) == 5000
        nums = [locker._lock_num(name) for name in names]
        assert len(set(nums)) == 5000

    def test_locker_defaults(self):
        lock = pals.Locker('foo', db_url).lock('a')
        assert lock.blocking is True
        assert lock.acquire_timeout == 30000

        lock = pals.Locker('bar', db_url, blocking_default=False, acquire_timeout_default=1000) \
            .lock('a')
        assert lock.blocking is False
        assert lock.acquire_timeout == 1000


def duration(started_at):
    duration = dt.datetime.now() - started_at
    secs = duration.total_seconds()
    # in milliseconds
    return secs * 1000


class TestLock:
    locker = pals.Locker('TestLock', db_url, acquire_timeout_default=1000)

    def test_same_lock_fails_acquire(self):
        lock1 = self.locker.lock('test_it')
        lock2 = self.locker.lock('test_it')

        try:
            assert lock1.acquire() is True

            # Non blocking version should fail immediately.  Use `is` test to make sure we get the
            # correct return value.
            assert lock2.acquire(blocking=False) is False

            # Blocking version should fail after a short time
            start = dt.datetime.now()
            acquired = lock2.acquire(acquire_timeout=300)
            waited_ms = duration(start)

            assert acquired is False
            assert waited_ms >= 300 and waited_ms < 350
        finally:
            lock1.release()

    def test_different_lock_name_both_acquire(self):
        lock1 = self.locker.lock('test_it')
        lock2 = self.locker.lock('test_it2')

        try:
            assert lock1.acquire() is True
            assert lock2.acquire() is True
        finally:
            lock1.release()
            lock2.release()

    def test_lock_after_release_acquires(self):
        lock1 = self.locker.lock('test_it')
        lock2 = self.locker.lock('test_it')

        try:
            assert lock1.acquire() is True
            assert lock1.release() is True
            assert lock2.acquire() is True
        finally:
            lock1.release()
            lock2.release()

    def test_class_params_used(self):
        """
            If blocking & timeout params are set on the class, make sure they are passed through and
            used correctly.
        """
        lock1 = self.locker.lock('test_it')
        lock2 = self.locker.lock('test_it', blocking=False)
        lock3 = self.locker.lock('test_it', acquire_timeout=300)

        try:
            assert lock1.acquire() is True

            # Make sure the blocking param applies
            acquired = lock2.acquire()
            assert acquired is False

            # Make sure the retry params apply
            start = dt.datetime.now()
            acquired = lock3.acquire()
            waited_ms = duration(start)
            assert acquired is False
            assert waited_ms >= 300 and waited_ms < 350
        finally:
            lock1.release()
            lock2.release()
            lock3.release()

    def test_context_manager(self):
        lock2 = self.locker.lock('test_it', blocking=False)
        try:
            with self.locker.lock('test_it'):
                assert lock2.acquire() is False

            # Outside the lock should have been released and we can get it now
            assert lock2.acquire()
        finally:
            lock2.release()

    def test_context_manager_failure_to_acquire(self):
        """
            By default, we want a context manager's failure to acquire to be a hard error so that
            a developer doesn't have to remember to explicilty check the return value of acquire
            when using a with statement.
        """
        lock2 = self.locker.lock('test_it', blocking=False)
        assert lock2.acquire() is True

        with pytest.raises(pals.AcquireFailure):
            with self.locker.lock('test_it'):
                pass  # we should never hit this line

    def test_gc_lock_release(self):
        lock1 = self.locker.lock('test_it')
        lock1.acquire()
        del lock1
        gc.collect()

        assert self.locker.lock('test_it', blocking=False).acquire()
