# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
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

.PHONY: help Makefile serve livehtml test

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
