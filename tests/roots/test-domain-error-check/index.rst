.. buildstep directive
.. buildstep before package definition
.. buildstep::

    $ foo

.. package:: foo 0.0.0

.. unexpected command continuation line
.. buildstep::

   > foo

.. unexpected expected output
.. buildstep::

    foo

.. empty buildstep
.. buildstep::

.. package directive
.. no arguments
.. package::

.. superfluous arguments
.. package:: bar 0.0.0 qux

.. invalid package name
.. package:: OR
.. package:: "!^@'&%$#`"

.. dependency parser: malformed YAML
.. package:: bar
   :deps: {

.. dependency parser: not a list
.. package:: bar
   :deps: {}

.. dependency parser: dependency name must be string
.. package:: bar
   :deps: - {}
.. dependency parser: invalid dependency name
.. package:: bar
   :deps: - OR
.. package:: bar
   :deps: - "@^'&"
.. dependency parser: or condition
.. package:: bar
   :deps: - A B

.. build-deps
.. package:: bar
   :build-deps: {

.. source parser: malformed YAML
.. package:: bar
   :sources: {

.. source parser: not a list
.. package:: bar
   :sources: {}

.. source parser: source entry must be a hash
.. package:: bar
   :sources: - a

.. source parser: only one source url allowed
.. package:: bar
   :sources:
    - http: a
      git: a

.. source parser: no source url
.. package:: bar
   :sources: - {}

.. source parser: unexpected key (http)
.. package:: bar
   :sources:
    - http: a
      branch: a

.. source parser: unexpected key (git)
.. package:: bar
   :sources:
    - git: a
      sha256sum: a

.. duplicate package names
.. package:: baz
.. package:: baz
