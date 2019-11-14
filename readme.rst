.. default-role:: code

PostgreSQL Advisory Locks (PALs)
################################

.. image:: https://circleci.com/gh/level12/pals.svg?style=shield
    :target: https://circleci.com/gh/level12/pals
.. image:: https://codecov.io/gh/level12/pals/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/level12/pals


Introduction
============

PALs makes it easy to use `PostgreSQL Advisory Locks`_ to do distributed application level
locking.

Do not confuse this type of locking with table or row locking in PostgreSQL.  It's not the same
thing.

Distributed application level locking can be implemented by using Redis, Memcache, ZeroMQ and
others.  But for those who are already using PostgreSQL, setup & management of another service is
unnecessary.

.. _PostgreSQL Advisory Locks: https://www.postgresql.org/docs/current/static/explicit-locking.html


Usage
========

Install with::

    pip install PALs

Then usage is as follows:

.. code:: python

    import datetime as dt
    import pals

    # Think of the Locker instance as a Lock factory.
    locker = pals.Locker('my-app-name', 'postgresql://user:pass@server/dbname')

    lock1 = locker.lock('my-lock')
    lock2 = locker.lock('my-lock')

    # The first acquire works
    assert lock1.acquire() is True

    # Non blocking version should fail immediately
    assert lock2.acquire(blocking=False) is False

    # Blocking version should fail after a short time
    start = dt.datetime.now()
    acquired = lock2.acquire(acquire_timeout=300)
    waited_ms = duration(start)

    assert acquired is False
    assert waited_ms >= 300 and waited_ms < 350

    # Release the lock
    lock1.release()

    # Non-blocking usage pattern
    if not lock1.acquire(blocking=False):
        # Aquire returned False, indicating we did not get the lock.
        return
    try:
        # do your work here
    finally:
        lock1.release()

    # If you want to block, you can use a context manager:
    try:
        with lock1:
            # Do your work here
            pass
    except pals.AcquireFailure:
        # This indicates the aquire_timeout was reached before the lock could be aquired.
        pass

Docs
========

Just this readme, the code, and tests.  It a small project, should be easy to understand.

Feel free to open an issue with questions.

Running Tests Locally
=====================

Setup Database Connection
-------------------------

We have provided a docker-compose file to ease running the tests::

    $ docker-compose up -d
    $ export PALS_DB_URL=postgresql://postgres:password@localhost:54321/postgres


Run the Tests
-------------

With tox::

    $ tox

Or, manually (assuming an activated virtualenv)::

    $ pip install -r requirements/dev.txt
    $ pip install -e .
    $ pytest pals/tests/


Lock Releasing & Expiration
---------------------------

Unlike locking systems built on cache services like Memcache and Redis, whose keys can be expired
by the service, there is no faculty for expiring an advisory lock in PostgreSQL.  If a client
holds a lock and then sleeps/hangs for mins/hours/days, no other client will be able to get that
lock until the client releases it.  This actually seems like a good thing to us, if a lock is
acquired, it should be kept until released.

But what about accidental failures to release the lock?

1. If a developer uses `lock.acquire()` but doesn't later call `lock.release()`?
2. If code inside a lock accidentally throws an exception (and .release() is not called)?
3. If the process running the application crashes or the process' server dies?

PALs helps #1 and #2 above in a few different ways:

* Locks work as context managers.  Use them as much as possible to guarantee a lock is released.
* Locks release their lock when garbage collected.
* PALs uses a dedicated SQLAlchemy connection pool.  When a connection is returned to the pool,
  either because a connection `.close()` is called or due to garbage collection of the connection,
  PALs issues a `pg_advisory_unlock_all()`.  It should therefore be impossible for an idle
  connection in the pool to ever still be holding a lock.

Regarding #3 above, `pg_advisory_unlock_all()` is implicitly invoked by PostgreSQL whenever a
connection (a.k.a session) ends, even if the client disconnects ungracefully.  So if a process
crashes or otherwise disappears, PostgreSQL should notice and remove all locks held by that
connection/session.

The possibility could exist that PostgreSQL does not detect a connection has closed and keeps
a lock open indefinitely.  However, in manual testing using `scripts/hang.py` no way was found
to end the Python process without PostgreSQL detecting it.


See Also
==========

* https://vladmihalcea.com/how-do-postgresql-advisory-locks-work/
* https://github.com/binded/advisory-lock
* https://github.com/vaidik/sherlock
* https://github.com/Xof/django-pglocks

