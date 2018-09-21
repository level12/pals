import gc
import random
import string

import pytest

import plocks


locker = plocks.Locker('plocker-tests', 'postgresql://rsyring@/test')


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
        names = [random_str(max(6, x % 25)) for x in range(5000)]
        assert len(set(names)) == 5000
        nums = [locker._lock_num(name) for name in names]
        assert len(set(nums)) == 5000


class TestLock:

    def test_same_lock_fails_aquire(self):
        lock1 = locker.lock('test_it')
        lock2 = locker.lock('test_it')

        assert lock1.aquire() is True

        # Non blocking version should fail immediately.  Use `is` test to make sure we get the
        # correct return value.
        assert lock2.aquire(blocking=False) is False

        # Blocking version should fail after a couple loops
        aquired, retries = lock2.aquire(retry_delay=100, retry_timeout=300, return_retries=True)
        assert aquired is False
        assert retries in (2, 3)

    def test_different_lock_name_both_aquire(self):
        lock1 = locker.lock('test_it')
        lock2 = locker.lock('test_it2')

        assert lock1.aquire() is True
        assert lock2.aquire() is True

    def test_lock_after_release_aquires(self):
        lock1 = locker.lock('test_it')
        lock2 = locker.lock('test_it')

        assert lock1.aquire() is True
        assert lock1.release() is True
        assert lock2.aquire() is True

    def test_class_params_used(self):
        """
            If blocking & retry params are set on the class, make sure they are passed through and
            used correctly.
        """
        lock1 = locker.lock('test_it')
        lock2 = locker.lock('test_it', blocking=False)
        lock3 = locker.lock('test_it', retry_delay=100, retry_timeout=300)

        assert lock1.aquire() is True

        # Make sure the blocking param applies
        aquired, retries = lock2.aquire(return_retries=True)
        assert aquired is False
        assert retries == 0

        # Make sure the retry params apply
        aquired, retries = lock3.aquire(return_retries=True)
        assert aquired is False
        assert retries in (2, 3)

    def test_context_manager(self):
        lock2 = locker.lock('test_it', blocking=False)

        with locker.lock('test_it'):
            assert lock2.aquire() is False

        # Outside the lock should have been released and we can get it now
        assert lock2.aquire()

    def test_context_manager_failure_to_aquire(self):
        """
            By default, we want a context manager's failure to aquire to be a hard error so that
            a developer doesn't have to remember to explicilty check the return value of aquire
            when using a with statement.
        """
        lock2 = locker.lock('test_it', blocking=False)
        assert lock2.aquire() is True

        with pytest.raises(plocks.AquireFailure):
            with locker.lock('test_it'):
                pass  # we should never hit this line

    def test_gc_lock_release(self):
        lock1 = locker.lock('test_it')
        lock1.aquire()
        del lock1
        gc.collect()

        assert locker.lock('test_it', blocking=False).aquire()
