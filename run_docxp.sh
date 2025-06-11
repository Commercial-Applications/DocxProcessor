#!/bin/bash
#
docx-processor --config ./config.yaml \
--source-dir ./docs_in \
--dest-dir ./docs_out \
--log-file ./process.log \
--workers 10 \
-v \
run