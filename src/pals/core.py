from contextlib import suppress
import hashlib
import logging
import struct

import sqlalchemy as sa


log = logging.getLogger(__name__)

__all__ = [
    'AcquireFailure',
    'Locker',
]


class AcquireFailure(Exception):
    def __init__(self, name, message):
        self.name = name
        self.message = message

    def __str__(self):
        return f'Lock acquire failed for "{self.name}". {self.message}.'


class Locker:
    """
    A Locker instance is intended to be an app-level lock factory.

    It holds the name of the application (so lock names are namespaced and less likely to
    collide) and the SQLAlchemy engine instance (and therefore the connection pool).

    If `unlock_all_on_checkin` is true (default), it will defensively do a
    unlock all operation when connections are given back to the connection
    pool. It is unlikely that a lock is left un-released (esp when using
    the context manager), but this step adds safety.
    The operation comes with some cost, so it may be desireable to disable
    in high-frequency use cases. Users should monitor locks in this case
    and recycle connections regularly.
    """

    def __init__(
        self,
        app_name,
        db_url=None,
        blocking_default=True,
        acquire_timeout_default=30000,
        create_engine_callable=None,
        unlock_all_on_checkin=True,
    ):
        self.app_name = app_name
        self.blocking_default = blocking_default
        self.acquire_timeout_default = acquire_timeout_default

        if create_engine_callable:
            self.engine = create_engine_callable()
        else:
            self.engine = sa.create_engine(db_url)

        if unlock_all_on_checkin:
            sa.event.listen(self.engine, 'checkin', self.on_conn_checkin)

    def on_conn_checkin(self, dbapi_connection, connection_record):
        """
        This method will be called when a connection is checked back into the connection
        pool and `unlock_all_on_checkin` is true. A connection is checked
        in to the pool when .close() is called on it or when the connection
        proxy goes out of scope and is garbage collected.
        """
        if dbapi_connection is None:
            # This may occur in rare circumstances where the connection is already closed or an
            # error occurred while connecting to the database. In these cases any held locks
            # should already be released when the connection terminated.
            return

        with dbapi_connection.cursor() as cur:
            # If the connection is "closed" we want all locks to be cleaned up since this
            # connection is going to be recycled.  This step is to take extra care that we don't
            # accidentally leave a lock acquired.
            cur.execute('select pg_advisory_unlock_all()')
        # Connections in the pool should not have an open transaction, therefore we need to roll
        # back before returning the connection because the execute above might have triggered an
        # automatic BEGIN.
        dbapi_connection.rollback()

    def _lock_name(self, name):
        if self.app_name is None:
            return name

        return f'{self.app_name}.{name}'

    def _lock_num(self, name):
        """
        PostgreSQL requires lock ids to be integers.  It accepts bigints which gives us
        64 bits to work with.  Hash the lock name to an integer.
        """
        name = self._lock_name(name)

        name_hash = hashlib.sha1(name.encode('utf-8'))

        # Convert the hash to an integer value in the range of a PostgreSQL bigint
        (num,) = struct.unpack('q', name_hash.digest()[:8])

        return num

    def lock(self, name, **kwargs):
        lock_num = self._lock_num(name)
        name = self._lock_name(name)
        kwargs.setdefault('blocking', self.blocking_default)
        kwargs.setdefault('acquire_timeout', self.acquire_timeout_default)
        return Lock(self.engine, lock_num, name, **kwargs)


class Lock:
    def __init__(self, engine, lock_num, name, blocking=None, acquire_timeout=None, shared=False):
        self.engine = engine
        self.conn = None
        self.lock_num = lock_num
        self.name = name
        self.blocking = blocking
        self.acquire_timeout = acquire_timeout
        self.shared_suffix = '_shared' if shared else ''

    def _acquire(self, blocking=None, acquire_timeout=None) -> bool:
        blocking = blocking if blocking is not None else self.blocking
        acquire_timeout = acquire_timeout or self.acquire_timeout

        if self.conn is None:
            self.conn = self.engine.connect()

        if blocking:
            timeout_sql = sa.text("select set_config('lock_timeout', :timeout :: text, false)")
            with self.conn.begin():
                self.conn.execute(timeout_sql, {'timeout': acquire_timeout})

            lock_sql = sa.text(f'select pg_advisory_lock{self.shared_suffix}(:lock_num)')
        else:
            lock_sql = sa.text(f'select pg_try_advisory_lock{self.shared_suffix}(:lock_num)')

        try:
            with self.conn.begin():
                result = self.conn.execute(lock_sql, {'lock_num': self.lock_num})
            retval = result.scalar()
            log.debug('Lock result was: %r', retval)
            # At least on PG 10.6, pg_advisory_lock() returns an empty string
            # when it acquires the lock.  pg_try_advisory_lock() returns True.
            # If pg_try_advisory_lock() fails, it returns False.
            if retval in (True, ''):
                return True
            else:
                raise AcquireFailure(self.name, f'result was: {retval}')
        except sa.exc.OperationalError as e:
            if 'lock timeout' not in str(e):
                raise
            log.debug('Lock acquire failed due to timeout')
            raise AcquireFailure(self.name, 'Failed due to timeout') from None

    def acquire(self, blocking=None, acquire_timeout=None) -> bool:
        try:
            return self._acquire(blocking=blocking, acquire_timeout=acquire_timeout)
        except AcquireFailure:
            return False

    def release(self):
        if self.conn is None:
            return False

        sql = sa.text(f'select pg_advisory_unlock{self.shared_suffix}(:lock_num)')
        with self.conn.begin():
            result = self.conn.execute(sql, {'lock_num': self.lock_num})
        try:
            return result.scalar()
        finally:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self._acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __del__(self):
        # Do everything we can to release resources and the connection to avoid accidentally holding
        # a lock indefinitely if .release() is forgotten.
        with suppress(Exception):
            self.release()
        # Sometimes this will fail if the connection has gone away before the gc runs. Since Python
        # would only print the exception and we cannot recover, suppress erroneous stderr noise.
        with suppress(Exception):
            self.conn.close()
        del self.conn
