EXECUTABLES = minios-configurator
APPLICATIONS = minios-configurator.desktop
POLICIES = dev.minios.configurator.policy

BINDIR = usr/bin
APPLICATIONSDIR = usr/share/applications
POLKITACTIONSDIR = usr/share/polkit-1/actions
LOCALEDIR = usr/share/locale

DOC_FILES = $(shell find doc -name "*.md")
MAN_FILES = $(patsubst doc/%.md, man/%.1, $(DOC_FILES))

PO_FILES  = $(shell find locale -name "*.po")
MO_FILES  = $(patsubst %.po,%.mo,$(PO_FILES))

# Build rules
ifeq (,$(findstring nodoc,$(DEB_BUILD_PROFILES)))
ifeq (,$(findstring nodoc,$(DEB_BUILD_OPTIONS)))
build: man
endif
endif
build: locale

# Compilation rules
man: $(MAN_FILES)

man/%.1: doc/%.md
	@echo "Generating man file for $<"
	mkdir -p $(@D)
	pandoc -s -t man $< -o $@

locale: $(MO_FILES)

%.mo: %.po
	@echo "Generating mo file for $<"
	msgfmt -o $@ $<
	chmod 644 $@

# Clean rule
clean:
	rm -rf man $(MO_FILES)

install: build
	install -d $(DESTDIR)/$(BINDIR) \
				$(DESTDIR)/$(APPLICATIONSDIR) \
				$(DESTDIR)/$(POLKITACTIONSDIR) \
				$(DESTDIR)/$(LOCALEDIR)

	cp $(EXECUTABLES) $(DESTDIR)/$(BINDIR)
	cp $(APPLICATIONS) $(DESTDIR)/$(APPLICATIONSDIR)
	cp $(POLICIES) $(DESTDIR)/$(POLKITACTIONSDIR)

	for MO_FILE in $(MO_FILES); do \
		LOCALE=$$(basename $$MO_FILE .mo); \
		echo "Copying mo file $$MO_FILE to $(DESTDIR)/usr/share/locale/$$LOCALE/LC_MESSAGES/minios-configurator.mo"; \
		install -Dm644 "$$MO_FILE" "$(DESTDIR)/usr/share/locale/$$LOCALE/LC_MESSAGES/minios-configurator.mo"; \
	done
