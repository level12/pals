"""
    If you run this file and monitor connections on your PostgreSQL server, you should see a backend
    process dedicated to this lock:

        select
            stat.datname
            , stat.pid
            , stat.usename
            , stat.application_name
            , stat.state
            , locks.mode as lockmode
            , stat.query
        from pg_stat_activity stat
        left join pg_locks locks
            on locks.pid = stat.pid
        where locktype = 'advisory'

    Then kill the Python process running this file in any way you want and make sure the PostgreSQL
    pid with the lock goes away:

    1) press any key and exit
    2) CTRL-C
    3) kill -9 <pid>
"""
import os

import pals

locker = pals.Locker('pals-hang', 'postgresql://postgres:password@localhost:54321/postgres')

lock = locker.lock('hang')
lock.acquire()
print('My pid is: ', os.getpid())
input('Lock acquired, press any key to exit: ')
