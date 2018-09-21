PostgreSQL Locks (PLocks)
#########################

.. image:: https://circleci.com/gh/level12/plocks.svg?style=shield
    :target: https://circleci.com/gh/level12/plocks
.. image:: https://codecov.io/gh/level12/plocks/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/level12/plocks


Introduction
---------------

PLocks makes it easy to use `PostgreSQL Advisory Locks`_ to do distributed application level
locking.

Do not confuse this type of locking with table or row locking in PostgreSQL.  It's not the same
thing.

Distributed application level locking can be implimented by using Redis, memcache, ZeroMQ and
others.  But for those who already using PostgreSQL, setup & management of another service is
unnecessary.

See also:

* https://vladmihalcea.com/how-do-postgresql-advisory-locks-work/
* https://github.com/binded/advisory-lock
* https://github.com/vaidik/sherlock
* https://github.com/Xof/django-pglocks

.. _PostgreSQL Advisory Locks: https://www.postgresql.org/docs/current/static/explicit-locking.html


Usage
--------------

For now, see the tests.
