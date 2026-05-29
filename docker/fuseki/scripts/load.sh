#!/bin/sh
if [ "$#" -lt 2 ]; then
    echo "Loads RDF data files into a TDB2 dataset" >&2
    echo "Usage:" >&2
    echo "$0 <TDB2 assembler description> <file> [<file> ...]" >&2
    exit 1
fi

ASSEMBLER=$1
shift
FILES="$@"

# ✅ Check if the assembler config file exists
if [ ! -f "$ASSEMBLER" ]; then
    echo "❌ Configuration file not found: $ASSEMBLER" >&2
    exit 2
fi

#
# See https://jena.apache.org/documentation/tdb2/tdb2_cmds.html#tdb2tdbloader
# for a description of tdb2.tdbloader.
#
java -cp $FUSEKI_HOME/fuseki-server.jar tdb2.tdbloader --desc=$ASSEMBLER $FILES
# tdb2.tdbloader --desc="$ASSEMBLER" $FILES
