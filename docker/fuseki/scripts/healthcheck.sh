#!/bin/sh
#
# Health check of Fuseki.
#
# Exit codes:
# - 0 for healthy
# - 1 for not healthy
#

# checks Fuseki's ping endpoint
check_fuseki() {
  (curl --fail --silent http://127.0.0.1:3030/$/ping > /dev/null)

  # return exit code of curl call
  return $?
}

check_fuseki || exit 1
