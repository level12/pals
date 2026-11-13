# PostgreSQL Advisory Locks (PALs)

[![nox](https://github.com/level12/pals/actions/workflows/nox.yaml/badge.svg)](https://github.com/level12/pals/actions/workflows/nox.yaml)
[![codecov](https://codecov.io/gh/level12/pals/branch/master/graph/badge.svg)](https://codecov.io/gh/level12/pals)

PALs makes it easy to use [PostgreSQL advisory locks][advisory-locks] for distributed,
application-level locking.

Do not confuse this type of locking with table or row locking in PostgreSQL. Distributed
application-level locking can also be implemented with Redis, Memcache, ZeroMQ, and other
services. For applications already using PostgreSQL, PALs avoids setting up and managing
another service.


## Usage

Install with:

```shell
pip install PALs
```

Then use a `Locker` as a lock factory:

```python
import datetime as dt

import pals

locker = pals.Locker('my-app-name', 'postgresql://user:pass@server/dbname')

lock1 = locker.lock('my-lock')
lock2 = locker.lock('my-lock')

assert lock1.acquire() is True
assert lock2.acquire(blocking=False) is False

start = dt.datetime.now()
acquired = lock2.acquire(acquire_timeout=300)
waited_ms = (dt.datetime.now() - start).total_seconds() * 1000
assert acquired is False
assert 300 <= waited_ms < 350

lock1.release()

if lock1.acquire(blocking=False):
    try:
        # Do your work here.
        pass
    finally:
        lock1.release()

try:
    with lock1:
        # Do your work here.
        pass
except pals.AcquireFailure:
    # The acquire timeout was reached before the lock was acquired.
    pass
```


## Lock releasing and expiration

Unlike locking systems backed by cache services, PostgreSQL advisory locks do not expire.
If a client holds a lock and then sleeps or hangs, no other client can acquire the lock
until it is released.

PALs helps prevent accidental lock retention in several ways:

- Locks work as context managers, which guarantees release when the context exits.
- Locks release their connection when garbage collected.
- By default, PALs calls `pg_advisory_unlock_all()` whenever a connection returns to its
  dedicated SQLAlchemy pool.

PostgreSQL also invokes `pg_advisory_unlock_all()` when a session ends, including an
ungraceful client disconnect. The extra pool check-in call has a cost and can be disabled
with `unlock_all_on_checkin=False` for high-frequency workloads. Applications that disable
it should monitor locks and recycle connections regularly.


## Development

The project structure and tooling derive from [Coppy]. To set up and test the project:

1. Install the [Coppy host dependencies], including Mise and uv.
2. Start PostgreSQL with `docker compose up -d`.
3. Set `PALS_DB_URL=postgresql://postgres:password@localhost:54321/postgres`.
4. Run `uv sync` and `prek install`.
5. Run `nox` to test Python 3.12 through 3.14 and execute the project checks.

Use `mise run version show` to show the current version and `mise run version -- --help`
for the version-management commands. See [Updating a Coppy project] before applying
template updates.

The implementation and tests are intentionally compact. See [changelog.rst](changelog.rst)
for release history.


## See also

- [How do PostgreSQL advisory locks work?](https://vladmihalcea.com/how-do-postgresql-advisory-locks-work/)
- [binded/advisory-lock](https://github.com/binded/advisory-lock)
- [vaidik/sherlock](https://github.com/vaidik/sherlock)
- [Xof/django-pglocks](https://github.com/Xof/django-pglocks)

[advisory-locks]: https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS
[Coppy]: https://github.com/level12/coppy
[Coppy host dependencies]: https://github.com/level12/coppy/wiki/Mise
[Updating a Coppy project]: https://github.com/level12/coppy/wiki#updating-a-project
