.. _configuration:

Configuration
#############


See `Pyramid settings documentation <http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/environment.html>`_.


.. _configuration-environment:

Environment variables
=====================

In order to ease deployment or testing strategies, *Cliquet* reads settings
from environment variables, in addition to ``.ini`` files.

For example, ``cliquet.storage_backend`` is read from environment variable
``CLIQUET_STORAGE_BACKEND`` if defined, else from application ``.ini``, else
from internal defaults.


Project info
============

.. code-block:: ini

    cliquet.project_name = project
    cliquet.project_docs = https://project.rtfd.org/
    # cliquet.project_version = 1.0


Feature settings
================

.. code-block:: ini

    # Limit number of batch operations per request
    # cliquet.batch_max_requests = 25

    # Disable DELETE on collection
    # cliquet.delete_collection_enabled = false

    # Force pagination *(recommended)*
    # cliquet.paginate_by = 200

    # Custom record id generator class
    # cliquet.id_generator = cliquet.storage.generators.UUID4


Deployment
==========

.. code-block:: ini

    # cliquet.backoff = 10
    cliquet.retry_after_seconds = 30


Scheme, host and port
:::::::::::::::::::::

By default *Cliquet* does not enforce requests scheme, host and port. It relies
on WSGI specification and the related stack configuration. Tuning this becomes
necessary when the application runs behind proxies or load balancers.

Most implementations, like *uwsgi*, provide configuration variables to adjust it
properly.

However if, for some reasons, this had to be enforced at the application level,
the following settings can be set:

.. code-block:: ini

    # cliquet.http_scheme = https
    # cliquet.http_host = production.server:7777


Check the ``url`` value returned in the hello view.


Deprecation
:::::::::::

Activate the :ref:`service deprecation <api-versioning>`. If the date specified
in ``eos`` is in the future, an alert will be sent to clients. If it's in
the past, the service will be declared as decomissionned.

.. code-block:: ini

    # cliquet.eos = 2015-01-22
    # cliquet.eos_message = "Client is too old"
    # cliquet.eos_url = http://website/info-shutdown.html



Logging with Heka
:::::::::::::::::

Mozilla Services standard logging format can be enabled using:

.. code-block:: ini

    cliquet.logging_renderer = cliquet.logs.MozillaHekaRenderer


With the following configuration, all logs are redirected to standard output
(See `12factor app <http://12factor.net/logs>`_):

.. code-block:: ini

    [loggers]
    keys = root

    [handlers]
    keys = console

    [formatters]
    keys = heka

    [logger_root]
    level = INFO
    handlers = console
    formatter = heka

    [handler_console]
    class = StreamHandler
    args = (sys.stdout,)
    level = NOTSET

    [formatter_heka]
    format = %(message)s


Handling exceptions with Sentry
:::::::::::::::::::::::::::::::

Requires the ``raven`` package, or *Cliquet* installed with
``pip install cliquet[monitoring]``.

Sentry logging can be enabled, `as explained in official documentation
<http://raven.readthedocs.org/en/latest/integrations/pyramid.html#logger-setup>`_.

.. note::

    The application sends an *INFO* message on startup, mainly for setup check.


Monitoring with StatsD
::::::::::::::::::::::

Requires the ``statsd`` package, or *Cliquet* installed with
``pip install cliquet[monitoring]``.

StatsD metrics can be enabled (disabled by default):

.. code-block:: ini

    cliquet.statsd_url = udp://localhost:8125
    # cliquet.statsd_prefix = cliquet.project_name


Monitoring with New Relic
:::::::::::::::::::::::::

Requires the ``newrelic`` package, or *Cliquet* installed with
``pip install cliquet[monitoring]``.

Enable middlewares as described :ref:`here <configuration-middlewares>`.

New-Relic can be enabled (disabled by default):

.. code-block:: ini

    cliquet.newrelic_config = /location/of/newrelic.ini
    cliquet.newrelic_env = prod


.. _configuration-storage:

Storage
=======

.. code-block:: ini

    cliquet.storage_backend = cliquet.storage.redis
    cliquet.storage_url = redis://localhost:6379/1

    # Safety limit while fetching from storage
    # cliquet.storage_max_fetch_size = 10000

    # Control number of pooled connections
    # cliquet.storage_pool_size = 50

See :ref:`storage backend documentation <storage>` for more details.


Cache
=====

.. code-block:: ini

    cliquet.cache_backend = cliquet.cache.redis
    cliquet.cache_url = redis://localhost:6379/0

    # Control number of pooled connections
    # cliquet.storage_pool_size = 50

See :ref:`cache backend documentation <cache>` for more details.


.. _configuration-authentication:

Authentication
==============

Since user identification is hashed in storage, a secret key is required
in configuration:

.. code-block:: ini

    # cliquet.userid_hmac_secret = b4c96a8692291d88fe5a97dd91846eb4


Authentication setup
::::::::::::::::::::

*Cliquet* relies on :github:`pyramid multiauth <mozilla-service/pyramid_multiauth>`_
to initialize authentication.

Therefore, any authentication policy can be specified through configuration.

For example, using the following example, *Basic Auth*, *Persona* and *IP Auth*
are enabled:

.. code-block:: ini

    multiauth.policies = basicauth pyramid_persona ipauth

    multiauth.policy.ipauth.use = pyramid_ipauth.IPAuthentictionPolicy
    multiauth.policy.ipauth.ipaddrs = 192.168.0.*
    multiauth.policy.ipauth.userid = LAN-user
    multiauth.policy.ipauth.principals = trusted


Similarly, any authorization policies and group finder function can be
specified through configuration in order to deeply customize permissions
handling and authorizations.


Basic Auth
::::::::::

``basicauth`` is mentioned among ``multiauth.policies`` by default.

.. code-block:: ini

    multiauth.policies = basicauth

By default, it uses an internal *Basic Auth* policy bundled with *Cliquet*.

In order to replace it by another one:

.. code-block:: ini

    multiauth.policies = basicauth
    multiauth.policy.basicauth.use = myproject.authn.BasicAuthPolicy


Custom Authentication
:::::::::::::::::::::

Using the various `Pyramid authentication packages
<https://github.com/ITCase/awesome-pyramid#authentication>`_, it is possible
to plug any kind of authentication.

(*Github/Twitter example to be done*)


Firefox Accounts
::::::::::::::::

Enabling :term:`Firefox Accounts` consists in including ``cliquet_fxa`` in
configuration, mentioning ``fxa`` among policies and providing appropriate
values for OAuth2 client settings.

See :github:`mozilla-services/cliquet-fxa`.


Application profiling
=====================

It is possible to profile the application while its running. This is especially
useful when trying to find slowness in the application.

Enable middlewares as described :ref:`here <configuration-middlewares>`.

Update the configuration file with the following values:

.. code-block:: ini

    cliquet.profiler_enabled = true
    cliquet.profiler_dir = /tmp/profiling

Run a load test (*for example*):

::

    SERVER_URL=http://localhost:8000 make bench -e


Render execution graphs using GraphViz:

::

    sudo apt-get install graphviz

::

    pip install gprof2dot
    gprof2dot -f pstats POST.v1.batch.000176ms.1427458675.prof | dot -Tpng -o output.png


.. _configuration-middlewares:

Enable middleware
=================

In order to enable Cliquet middleware, wrap the application in the project ``main`` function:

.. code-block:: python
  :emphasize-lines: 4,5

  def main(global_config, **settings):
      config = Configurator(settings=settings)
      cliquet.initialize(config, __version__)
      app = config.make_wsgi_app()
      return cliquet.install_middlewares(app)


Initialization sequence
=======================

In order to control what part of *Cliquet* should be run during application
startup, or add custom initialization steps from configuration, it is
possible to change the ``initialization_sequence`` setting.

.. warning::

    This is considered as a dangerous zone and should be used with caution.

    Later, a better formalism should be introduced to easily allow addition
    or removal of steps, without repeating the whole list and without relying
    on internal functions location.


.. code-block:: ini

    cliquet.initialization_sequence = cliquet.initialization.setup_json_serializer
                                      cliquet.initialization.setup_logging
                                      cliquet.initialization.setup_storage
                                      cliquet.initialization.setup_cache
                                      cliquet.initialization.setup_requests_scheme
                                      cliquet.initialization.setup_version_redirection
                                      cliquet.initialization.setup_deprecation
                                      cliquet.initialization.setup_authentication
                                      cliquet.initialization.setup_backoff
                                      cliquet.initialization.setup_stats
