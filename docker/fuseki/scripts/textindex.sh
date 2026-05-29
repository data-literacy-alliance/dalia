#!/bin/sh
if [ "$#" -lt 1 ]; then
    echo "Build a text index for a TDB2 dataset" >&2
    echo "Usage:" >&2
    echo "$0 <TDB2 assembler description>" >&2
    exit 1
fi

ASSEMBLER=$1

#
# See https://jena.apache.org/documentation/query/text-query.html#step-2---build-the-text-index
# for a description of jena.textindexer.
#
java -cp $FUSEKI_HOME/fuseki-server.jar jena.textindexer --desc=$ASSEMBLER
