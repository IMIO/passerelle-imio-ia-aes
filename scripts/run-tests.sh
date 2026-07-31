#!/bin/bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../.env" 2>/dev/null

DJANGO_SETTINGS_MODULE=passerelle.settings PASSERELLE_SETTINGS_FILE=tests/settings.py $PASSERELLE_ENV "$script_dir/../tests/"
