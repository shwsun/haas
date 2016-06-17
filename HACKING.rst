The first time you start working in the repository, set up a clean test
environment (Before you start make sure that you have setup a database
to be used by for HaaS. HaaS supports SQLIte and PostgreSQL databases.
You should setup either of the two before you start further. Details to
setup a database can be found in INSTALL.rst)::

  virtualenv .venv

Next, each time you start working, enter the environment::

  source .venv/bin/activate

Then, proceed with installing the HaaS and its dependencies into the virtual
environment::

  pip install -e .

On systems with older versions of ``pip``, such as Debian Wheezy and Ubuntu
12.04, this install will fail with the following error::

  AttributeError: 'NoneType' object has no attribute 'skip_requirements_regex'

Fix this by upgrading ``pip`` within the virtual environment::

  pip install --upgrade pip

Versions of python prior to 2.7 don't have importlib as part of their
standard library, but it is possible to install it separately. If you're
using python 2.6 (which is what is available on CentOS 6, for example),
you may need to run::

  pip install importlib

You may get an error 'psycopg2 package not found' when you do 'haas-admin db create'
in the next step if you are using PostgreSQL database. You may need to run::

  pip install psycopg2

`testing.md <docs/testing.md>`_ contains more information about testing HaaS.
`migrations.md <docs/migrations.md>`_ dicsusses working with database migrations
and schema changes.

Configuring HaaS
================

Now the ``haas`` executable should be in your path.  First, create a
configuration file ``haas.cfg``. There are two examples for you to work from,
``examples/haas.cfg.dev-no-hardware``, which is oriented towards development, and
``examples/haas.cfg`` which is more production oriented.  These config
files are well commented; read them carefully.

HaaS can be configured to not perform state-changing operations on nodes,
headnodes and networks, allowing developers to run and test parts of a haas
server without requiring physical hardware. To suppress actual node and headnode
operations, set ``dry_run = True`` in the ``[devel]`` section. For suppressing
actual network switch operations, use the ``mock`` switch driver.

Next initialize the database with the required tables, with ``haas-admin db create``.
Run the server with ``haas serve`` and ``haas serve_networks`` in separate
terminals.  Finally, ``haas help`` lists the various API commands one can use.
Here is an example session, testing ``headnode_delete_hnic``::

  haas project_create proj
  haas headnode_create hn proj
  haas headnode_create_hnic hn hn-eth0
  haas headnode_delete_hnic hn hn-eth0

Additionally, before each commit, run the automated test suite with ``py.test
tests/unit``. If at all possible, run the deployment tests as well (``py.test
tests/deployment``), but this requires access to a sepcialized setup, so if the
patch is sufficiently unintrusive it may be acceptable to skip this step.
