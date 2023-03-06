Changelog
=========

0.3.4 released 2023-03-06
-------------------------

- support SQLAlchemy 2.0 (6879081_)

.. _6879081: https://github.com/level12/pals/commit/6879081


0.3.3 released 2023-01-06
-------------------------

- add additional info to AcquireFailure exception (6d81db9_)

.. _6d81db9: https://github.com/level12/pals/commit/6d81db9


0.3.2 released 2021-02-01
-------------------------

- Support shared advisory locks (thanks to @absalon-james) (ba2fe21_)

.. _ba2fe21: https://github.com/level12/pals/commit/ba2fe21


0.3.1 released 2020-09-03
-------------------------

- readme: update postgresql link (260bf75_)
- Handle case where a DB connection is returned to the pool which is already closed (5d730c9_)
- Fix a couple of typos in comments (da2b8af_)
- readme improvements (4efba90_)
- CI: fix coverage upload (52daa27_)
- Fix CI: bump CI python to v3.7 and postgres to v11 (23b3028_)

.. _260bf75: https://github.com/level12/pals/commit/260bf75
.. _5d730c9: https://github.com/level12/pals/commit/5d730c9
.. _da2b8af: https://github.com/level12/pals/commit/da2b8af
.. _4efba90: https://github.com/level12/pals/commit/4efba90
.. _52daa27: https://github.com/level12/pals/commit/52daa27
.. _23b3028: https://github.com/level12/pals/commit/23b3028


0.3.0 released 2019-11-13
-------------------------

Enhancements
~~~~~~~~~~~~

- Add acquire timeout and blocking defaults at Locker level (681c3ba_)
- Adjust default lock timeout from 1s to 30s (5a0963b_)

Project Cleanup
~~~~~~~~~~~~~~~

- adjust flake8 ignore and other tox project warning (ee123fc_)
- fix comment in test (0d8eb98_)
- Additional readme updates (0786766_)
- update locked dependencies (f5743a6_)
- Remove Python 3.5 from CI (b63c71a_)
- Cleaned up the readme code example a bit and added more references (dabb497_)
- Update setup.py to use SPDX license identifier (b811a99_)
- remove Pipefiles (0637f39_)
- move to using piptools for dependency management (af2e91f_)

.. _ee123fc: https://github.com/level12/pals/commit/ee123fc
.. _681c3ba: https://github.com/level12/pals/commit/681c3ba
.. _5a0963b: https://github.com/level12/pals/commit/5a0963b
.. _0d8eb98: https://github.com/level12/pals/commit/0d8eb98
.. _0786766: https://github.com/level12/pals/commit/0786766
.. _f5743a6: https://github.com/level12/pals/commit/f5743a6
.. _b63c71a: https://github.com/level12/pals/commit/b63c71a
.. _dabb497: https://github.com/level12/pals/commit/dabb497
.. _b811a99: https://github.com/level12/pals/commit/b811a99
.. _0637f39: https://github.com/level12/pals/commit/0637f39
.. _af2e91f: https://github.com/level12/pals/commit/af2e91f


0.2.0 released 2019-03-07
-------------------------

- Fix misspelling of "acquire" (737763f_)

.. _737763f: https://github.com/level12/pals/commit/737763f


0.1.0 released 2019-02-22
-------------------------

- Use `lock_timeout` setting to expire blocking calls (d0216ce_)
- fix tox (1b0ffe2_)
- rename to PALs (95d5a3c_)
- improve readme (e8dd6f2_)
- move tests file to better location (a153af5_)
- add flake8 dep (3909c95_)
- fix tests so they work locally too (7102294_)
- get circleci working (28f16d2_)
- suppress exceptions in Lock __del__ (e29c1ce_)
- Add hang.py script (3372ef0_)
- fix packaging stuff, update readme (cebd976_)
- initial commit (871b877_)

.. _d0216ce: https://github.com/level12/pals/commit/d0216ce
.. _1b0ffe2: https://github.com/level12/pals/commit/1b0ffe2
.. _95d5a3c: https://github.com/level12/pals/commit/95d5a3c
.. _e8dd6f2: https://github.com/level12/pals/commit/e8dd6f2
.. _a153af5: https://github.com/level12/pals/commit/a153af5
.. _3909c95: https://github.com/level12/pals/commit/3909c95
.. _7102294: https://github.com/level12/pals/commit/7102294
.. _28f16d2: https://github.com/level12/pals/commit/28f16d2
.. _e29c1ce: https://github.com/level12/pals/commit/e29c1ce
.. _3372ef0: https://github.com/level12/pals/commit/3372ef0
.. _cebd976: https://github.com/level12/pals/commit/cebd976
.. _871b877: https://github.com/level12/pals/commit/871b877

