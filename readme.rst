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

.. code:: python

    # Think of the Locker instance as a Lock factory.
    locker = pals.Locker('my-app-name', 'postgresql://user:pass@server/dbname')

    lock1 = locker.lock('my-lock')
    lock2 = locker.lock('my-lock')

    # The first aquire works
    assert lock1.aquire() is True

    # Non blocking version should fail immediately
    assert lock2.aquire(blocking=False) is False

    # Blocking version will retry and eventually fail
    aquired, retries = lock2.aquire(return_retries=True)
    assert aquired is False
    assert retries > 4

    # You can set the retry parameters yourself if you don't like our defaults.
    lock2.aquire(retry_delay=100, retry_timeout=300)

    # They can also be set on the lock instance
    lock3 = locker.lock('my-lock', retry_delay=100, retry_timeout=300)

    # Release the lock
    lock1.release()

    # Recommended usage pattern:
    if not lock1.aquire():
        # Remember to check to make sure you got your lock
        return
    try:
        # do my work here
    finally:
        lock1.release()

    # But more recommended and easier is to use the lock as a context manager:
    with lock1:
        assert lock2.aquire() is False

    # Outside the context manager the lock should have been released and we can get it now
    assert lock2.aquire()

    # The context manager version will throw an exception if it fails to aquire the lock.  This
    # pattern was chosen because it feels symantically wrong to have to check to see if the lock
    # was actually aquired inside the context manager.  If the code inside is ran, the lock was
    # aquired.
    try:
        with lock1:
            # We won't get here because lock2 aquires the lock just above
            pass
    except pals.AquireFailure:
        pass


Running Tests Locally
=====================

Setup Database Connection
-------------------------

We have provided a docker-compose file, but you don't have to use it::

    $ docker-compose up -d
    $ export PALS_DB_URL=postgresql://postgres:password@localhost:54321/postgres

You can also put the environment variable in a .env file and pipenv will pick it up.

Run the Tests
-------------

With tox::

    $ tox

Or, manually::

    $ pipenv install --dev
    $ pipenv shell
    $ pytest pals/tests.py


Lock Releasing & Expiration
---------------------------

Unlike locking systems built on cache services like Memcache and Redis, whose keys can be expired
by the service, there is no faculty for expiring an advisory lock in PostgreSQL.  If a client
holds a lock and then sleeps/hangs for mins/hours/days, no other client will be able to get that
lock until the client releases it.  This actually seems like a good thing to us, if a lock is
acquired, it should be kept until released.

But what about accidental failures to release the lock?

1. If a developer uses `lock.aquire()` but doesn't later call `lock.release()`?
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

