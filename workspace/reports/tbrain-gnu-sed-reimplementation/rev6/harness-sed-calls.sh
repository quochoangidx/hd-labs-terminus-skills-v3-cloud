printf "[1.5, \"o\", \"x\"]
" > /tmp/r.cast; grep -E "^\[[0-9]+\.[0-9]+," /tmp/r.cast | tail -n 1 | sed -E "s/^\[([0-9]+\.[0-9]+),.*/\1/"; echo "pipeline status ${PIPESTATUS[2]}"; node_major="$(echo v22.1.0 | sed "s/^v//" | cut -d. -f1)"; echo "node major=[$node_major]"; command -v sed || { echo "no sed on PATH"; exit 127; }
