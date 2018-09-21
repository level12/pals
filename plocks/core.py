import datetime as dt
import hashlib
import struct
import time

import sqlalchemy as sa


__all__ = [
    'Locker',
    'AquireFailure',
]


class AquireFailure(Exception):
    pass


class Locker:
    """
        A Locker instance is intended to be an app-level lock factory.

        It holds the name of the application (so lock names are namespaced and less likely to
        collide) and the SQLAlchemy engine instance (and therefore the connection pool).
    """
    def __init__(self, app_name, *args, **kwargs):
        self.engine = sa.create_engine(*args, **kwargs)
        self.app_name = app_name

        @sa.event.listens_for(self.engine, 'checkin')
        def on_conn_checkin(dbapi_connection, connection_record):
            """
                This function will be called when a connection is checked back into the connection
                pool.  That should happen when .close() is called on it or when the connection
                proxy goes out of scope and is garbage collected.
            """
            with dbapi_connection.cursor() as cur:
                # If the connection is "closed" we want all locks to be cleaned up since this
                # connection is going to be recycled.  This step is to take extra care that we don't
                # accidentally leave a lock aquired.
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
        return Lock(self.engine.connect(), lock_num, **kwargs)


class Lock:
    def __init__(self, conn, lock_num, blocking=True, retry_delay=200, retry_timeout=1000):
        self.conn = conn
        self.lock_num = lock_num
        self.blocking = blocking
        self.retry_delay = retry_delay
        self.retry_timeout = retry_timeout

    def aquire(self, blocking=None, retry_delay=None, retry_timeout=None, return_retries=False):
        blocking = blocking if blocking is not None else self.blocking
        retry_delay = retry_delay or self.retry_delay
        retry_timeout = retry_timeout or self.retry_timeout

        sql = sa.text('select pg_try_advisory_lock(:lock_num)')

        started_at = dt.datetime.utcnow()
        loop_count = 0
        while True:
            result = self.conn.execute(sql, lock_num=self.lock_num)
            aquired_lock = result.scalar()

            if aquired_lock or not blocking:
                # return retries is mostly intended for easier testing
                if return_retries:
                    return aquired_lock, loop_count
                return aquired_lock

            elapsed = dt.datetime.utcnow() - started_at
            elapsed_ms = elapsed.total_seconds() * 1000
            if elapsed_ms >= retry_timeout:
                # return retries is mostly intended for easier testing
                if return_retries:
                    return False, loop_count
                return False

            loop_count += 1

            # Sleep for the desired delay
            time.sleep(retry_delay / 1000.0)

    def release(self):
        sql = sa.text('select pg_advisory_unlock(:lock_num)')
        result = self.conn.execute(sql, lock_num=self.lock_num)
        return result.scalar()

    def __enter__(self):
        if not self.aquire():
            raise AquireFailure
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __del__(self):
        # Do everything we can to release resources and the connection to avoid accidently holding
        # a lock indefinetely if .release() is forgotten.
        self.release()
        self.conn.close()
        del self.conn
