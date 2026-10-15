#!/usr/bin/env fish

set repo_root (cd (dirname (status --current-filename))/..; pwd)
cd "$repo_root"

if not command -q python3
    echo "python3 is required to refresh the ArtCraft manifest." >&2
    exit 1
end

echo "Refreshing ArtCraft release manifest..."
python3 scripts/update.py $argv
set exit_code $status

if test $exit_code -ne 0
    echo "Update finished with errors; see output above." >&2
    exit $exit_code
end

echo "Manifest update complete."
