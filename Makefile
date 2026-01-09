# make documentation

PACKAGE=$(notdir $(PWD))

LOGO="https://github.com/eudoxys/.github/blob/main/eudoxys_banner.png?raw=true"
LINK="https://www.eudoxys.com/"

docs: $(PACKAGE)/__init__.py
	echo Install $(PACKAGE)...
	pip install --upgrade pdoc
	pdoc $< -o $@ --logo $(LOGO) --mermaid --math --logo-link $(LINK)

$(PACKAGE)/__init__.py: $(filter-out $(PACKAGE)/__init__.py,$(wildcard $(PACKAGE)/*.py))
