#!/bin/sh

#
# Compacts the "dalia" dataset by calling its compact endpoint
# (https://jena.apache.org/documentation/fuseki2/fuseki-server-protocol.html#compact).
#
curl -X POST http://127.0.0.1:3030/$/compact/dalia?deleteOld=true
