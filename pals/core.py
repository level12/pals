import hashlib
import logging
import struct

import sqlalchemy as sa


log = logging.getLogger(__name__)

__all__ = [
    'Locker',
    'AcquireFailure',
]


class AcquireFailure(Exception):
    pass


class Locker:
    """
        A Locker instance is intended to be an app-level lock factory.

        It holds the name of the application (so lock names are namespaced and less likely to
        collide) and the SQLAlchemy engine instance (and therefore the connection pool).
    """
    def __init__(self, app_name, db_url=None, blocking_default=True, acquire_timeout_default=30000,
            create_engine_callable=None):
        self.app_name = app_name
        self.blocking_default = blocking_default
        self.acquire_timeout_default = acquire_timeout_default

        if create_engine_callable:
            self.engine = create_engine_callable()
        else:
            self.engine = sa.create_engine(db_url)

        @sa.event.listens_for(self.engine, 'checkin')
        def on_conn_checkin(dbapi_connection, connection_record):
            """
                This function will be called when a connection is checked back into the connection
                pool.  That should happen when .close() is called on it or when the connection
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

    def _lock_name(self, name):
        if self.app_name is None:
            return name

        return '{}.{}'.format(self.app_name, name)

    def _lock_num(self, name):
        """
            PostgreSQL requires lock ids to be integers.  It accepts bigints which gives us
            64 bits to work with.  Hash the lock name to an integer.
        """
        name = self._lock_name(name)

        name_hash = hashlib.sha1(name.encode('utf-8'))

        # Convert the hash to an integer value in the range of a PostgreSQL bigint
        num, = struct.unpack('q', name_hash.digest()[:8])

        return num

    def lock(self, name, **kwargs):
        lock_num = self._lock_num(name)
        kwargs.setdefault('blocking', self.blocking_default)
        kwargs.setdefault('acquire_timeout', self.acquire_timeout_default)
        return Lock(self.engine.connect(), lock_num, **kwargs)


class Lock:
    def __init__(self, engine, lock_num, blocking=None, acquire_timeout=None):
        self.engine = engine
        self.conn = None
        self.lock_num = lock_num
        self.blocking = blocking
        self.acquire_timeout = acquire_timeout

    def acquire(self, blocking=None, acquire_timeout=None):
        blocking = blocking if blocking is not None else self.blocking
        acquire_timeout = acquire_timeout or self.acquire_timeout

        if self.conn is None:
            self.conn = self.engine.connect()

        if blocking:
            timeout_sql = sa.text('set lock_timeout = :timeout')
            self.conn.execute(timeout_sql, timeout=acquire_timeout)

            lock_sql = sa.text('select pg_advisory_lock(:lock_num)')
        else:
            lock_sql = sa.text('select pg_try_advisory_lock(:lock_num)')

        try:
            result = self.conn.execute(lock_sql, lock_num=self.lock_num)
            retval = result.scalar()
            log.debug('Lock result was: %r', retval)
            # At least on PG 10.6, pg_advisory_lock() returns an empty string
            # when it acquires the lock.  pg_try_advisory_lock() returns True.
            # If pg_try_advisory_lock() fails, it returns False.
            return retval in (True, '')
        except sa.exc.OperationalError as e:
            if 'lock timeout' not in str(e):
                raise
            log.debug('Lock acquire failed due to timeout')
            return False

    def release(self):
        if self.conn is None:
            return False

        sql = sa.text('select pg_advisory_unlock(:lock_num)')
        result = self.conn.execute(sql, lock_num=self.lock_num)
        self.conn.close()
        self.conn = None
        return result.scalar()

    def __enter__(self):
        if not self.acquire():
            raise AcquireFailure
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __del__(self):
        # Do everything we can to release resources and the connection to avoid accidentally holding
        # a lock indefinitely if .release() is forgotten.
        try:
            self.release()
        except Exception:
            # Sometimes this will fail if the connection has gone away before the gc runs.  Since
            # Python is just going to print the exception and we can't do anything about it,
            # suppress the exception to keep erroneous noise out of stderr.
            pass
        try:
            self.conn.close()
        except Exception:
            # ditto
            pass
        del self.conn
