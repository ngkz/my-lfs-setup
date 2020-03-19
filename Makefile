# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    = -j auto
SPHINXBUILD   = sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

livehtml:
	sphinx-autobuild \
		-b html \
		-i ".git/*" \
		-i "$(BUILDDIR)/*" \
		-i ".pytest_cache/*" \
		-i .gitignore \
		-i "tests/*" \
		-i Makefile \
		-i requirements.txt \
		$(SPHINXOPTS) \
		"$(SOURCEDIR)" \
		"$(BUILDDIR)/html"

test:
	pytest tests/

coverage:
	coverage run --source=_ext --branch -m pytest tests/
	coverage report --skip-covered --skip-empty
	coverage html -d _build/coverage_html

system:
	@$(SPHINXBUILD) \
		-M system \
		"$(SOURCEDIR)" \
		"$(BUILDDIR)" \
		$(if $(ROOTFS),-Df2lfs_rootfs_path=$(ROOTFS),) \
		$(if $(findstring y,$(BOOTSTRAP)),-Df2lfs_bootstrap=True,) \
		$(SPHINXOPTS) \
		$(O)

clean: Makefile
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	coverage erase

.PHONY: help Makefile serve livehtml test coverage system

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
