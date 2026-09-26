# ai-generated: 85% - Claude Code drafted, reviewed by the author

"""Shared HTTP client setup for the own-tests suite (Stretch S3)."""

import os

BASE_URL = os.environ.get("SVCDESK_URL", "http://svcdesk:8080")
