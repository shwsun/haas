# Copyright 2013-2015 Massachusetts Open Cloud Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the
# License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS
# IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.  See the License for the specific language
# governing permissions and limitations under the License.

from setuptools import setup, find_packages
from os.path import dirname, join
readme_file = 'README.rst'

def _get_readme():
    with open(join(dirname(__file__), readme_file)) as f:
        return f.read()

setup(name='haas',
      version='0.2rc2',
      maintainer='Developers of the HaaS Project at MOC',
      maintainer_email='haas-dev-list@bu.edu',
      url='https://github.com/CCI-MOC/haas',
      description='A bare-metal isolation service that automates allocation and management ' \
                  'of non-virtualized compute resources across mutually untrusting ' \
                  'and incompatible provisioning systems.',
      long_description=_get_readme(),
      license='Apache 2.0',
      classifiers=['Development Status :: 4 - Beta',
                   'Intended Audience :: Developers',
                   'Intended Audience :: System Administrators', 
                   'Intended Audience :: Science/Research', 
                   'Topic :: System :: Cloud :: Installation/Setup',
                   'Topic :: System :: Systems Administration :: Clustering :: Utilities ',
                   'License :: OSI Approved :: Apache Software License, version 2.0',
                   'Environment :: Console',
                   'Environment :: Web Environment',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python',
                  ],
      keywords='cloud bare-metal setuptools data-center isolation',

      packages=find_packages(),
      # TODO: we should merge scripts into entry_points, below.
      scripts=['scripts/haas', 'scripts/create_bridges'],
      entry_points={
          'console_scripts': ['haas-admin=haas.commands.admin:main'],
      },
      package_data={
          'haas': [
              'migrations/env.py',
              'migrations/alembic.ini',
              'migrations/script.py.mako',
              'migrations/versions/*.py',
          ],
          'haas.ext.obm': ['migrations/*/*.py'],
          'haas.ext.switches': ['migrations/*/*.py'],
      },
      zip_safe=False,  # migrations folder needs to be extracted to work.

      # A note on version constraints: most python packages follow some version
      # of [semver][1], and the [python packaging guide][2] recommends this. We
      # assume this scheme unless a package indicates something else.
      #
      # The pocoo.org packages (Werkzeug, Flask...) seem to follow the
      # patch-level release semantics for their 0.x releases, even though the
      # semver spec doesn't require it.
      #
      # Our general policy is this: if we can use the semver semantics to
      # derive compatibility information, we specify a minimum version that
      # we've tested against, with an upper bound that guarantees backwards
      # compatibility according to semver. If we can't (either because the
      # package doesn't follow semver, or is 0.x and thus has no
      # compatibility guarantees), we pin the exact version.
      #
      # [1]: http://semver.org
      # [2]: https://packaging.python.org/en/latest/distributing/#choosing-a-versioning-scheme
      install_requires=['Flask-SQLAlchemy>=2.1,<3.0',
                        'Flask-Migrate>=1.8,<2.0',
                        'Flask-Script>=2.0.5,<3.0',
                        'Werkzeug>=0.9.4,<0.10',
                        'Flask>=0.10.1,<0.11',
                        'schema==0.3.1',
                        'importlib>=1.0.3,<2.0',
                        'passlib>=1.6.2,<2.0',
                        'pexpect>=3.3,<4.0',
                        'requests>=2.4.1,<3.0',
                        'pytest>=2.6.2,<3.0',
                        'pytest-cov>=1.8.0,<2.0',
                        'pytest-xdist>=1.14,<2.0',
                        'requests_mock>=1.0.0,<2.0',
                        'lxml>=3.6.0,<4.0',
                        ])
