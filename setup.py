import os.path as osp
from setuptools import setup, find_packages

cdir = osp.abspath(osp.dirname(__file__))
README = open(osp.join(cdir, 'readme.rst')).read()
CHANGELOG = open(osp.join(cdir, 'changelog.rst')).read()

version_fpath = osp.join(cdir, 'pals', 'version.py')
version_globals = {}
with open(version_fpath) as fo:
    exec(fo.read(), version_globals)

setup(
    name="PALs",
    version=version_globals['VERSION'],
    description="Easy distributed locking using PostgreSQL Advisory Locks.",
    long_description='\n\n'.join((README, CHANGELOG)),
    long_description_content_type='text/x-rst',
    author="Randy Syring",
    author_email="randy.syring@level12.io",
    url='https://github.com/level12/pals',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    license='BSD-3-Clause',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'sqlalchemy',
    ]
)
