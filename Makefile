COMMAND_SRC := $(CURDIR)/commands/spotify-scan.md
COMMAND_DST := $(HOME)/.claude/commands/spotify-scan.md
CONFIG_DIR  := $(HOME)/.config/sptfy

.PHONY: install uninstall status

install: ## Create symlink and config directory
	@mkdir -p $(CONFIG_DIR)
	@chmod 700 $(CONFIG_DIR)
	@mkdir -p $(dir $(COMMAND_DST))
	@ln -sf $(COMMAND_SRC) $(COMMAND_DST)
	@echo "Installed:"
	@echo "  Symlink: $(COMMAND_DST) -> $(COMMAND_SRC)"
	@echo "  Config dir: $(CONFIG_DIR)"
	@echo ""
	@echo "Next: create a Spotify app at https://developer.spotify.com/dashboard"
	@echo "  Set redirect URI to http://localhost:8765/callback"
	@echo "  Then run: python3 spotify_auth.py login --client-id <YOUR_CLIENT_ID>"

uninstall: ## Remove symlink (does not delete config/tokens)
	@rm -f $(COMMAND_DST)
	@echo "Removed symlink: $(COMMAND_DST)"
	@echo "Config and tokens in $(CONFIG_DIR) were NOT deleted."
	@echo "To fully clean up: rm -rf $(CONFIG_DIR)"

status: ## Show install status
	@echo "Command symlink:"
	@if [ -L "$(COMMAND_DST)" ]; then \
		echo "  $(COMMAND_DST) -> $$(readlink $(COMMAND_DST))"; \
	else \
		echo "  Not installed"; \
	fi
	@echo "Config directory:"
	@if [ -d "$(CONFIG_DIR)" ]; then \
		echo "  $(CONFIG_DIR) exists"; \
		ls -la $(CONFIG_DIR)/ 2>/dev/null || true; \
	else \
		echo "  Not created"; \
	fi
	@echo "Auth status:"
	@python3 $(CURDIR)/spotify_auth.py status 2>/dev/null || echo "  Not configured"
