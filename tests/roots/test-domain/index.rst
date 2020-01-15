.. package:: foo 1.3.37
   :license: WTFPL
   :deps: - bar OR baz
          - qux
   :build-deps: - quux
   :sources: - http: http://example.com/src1.tar.xz
               gpgsig: http://example.com/src1.tar.xz.sig
               gpgkey: src1-key.gpg
             - http: http://example.com/src2.patch
               sha256sum: DEADBEEFDEADBEEFDEADBEEFDEADBEEF
             - git: git://example.com/src3.git
               branch: branch_or_tag
             - git: https://example.com/src4.git
               commit: deadbeef
   :bootstrap:

.. buildstep::

   $ foo block 1 command 1

.. buildstep::

   $ foo block 2 command 1
   foo block 2 command 1 expected output
   # foo block 2 command 2 line 1 \
   > foo block 2 command 2 line 2
   foo block 2 command 2 expected output line 1
   foo block 2 command 2 expected output line 2

.. package:: bar 31.3.37

.. buildstep::

   $ bar

.. package:: baz

.. package:: qux

.. package:: quux
