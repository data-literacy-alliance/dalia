#!/bin/sh
set -e
set -x

#
# Create or replace database configuration files
#
mkdir -p $FUSEKI_BASE/configuration
cp $CONFIG_TEMPLATES_DIR/config.ttl $FUSEKI_BASE
cp $CONFIG_TEMPLATES_DIR/dalia.ttl $FUSEKI_BASE/configuration
cp $CONFIG_TEMPLATES_DIR/ontologies.ttl $FUSEKI_BASE/configuration

#
# Create "dalia" dataset if it does not already exist, insert RDF data from
# $DALIA_DATA_DIR and build a text index for it.
#
# if [ ! -d "$FUSEKI_BASE/databases/dalia" ]; then
#   find $DALIA_DATA_DIR \( -iname "*.ttl" -o -iname "*.rdf" -o -iname "*.owl" \) -type f -exec $SCRIPTS_DIR/load.sh $FUSEKI_BASE/configuration/dalia.ttl {} \;
#   $SCRIPTS_DIR/textindex.sh $FUSEKI_BASE/configuration/dalia.ttl
# fi

ARCHIVE_DIR="$DALIA_DATA_DIR/archive"
mkdir -p "$ARCHIVE_DIR"

# DALIA_FILES=$(find "$DALIA_DATA_DIR" \( -iname "*.ttl" -o -iname "*.rdf" -o -iname "*.owl" \) -type f)
# DALIA_FILES=$(find "$DALIA_DATA_DIR" -path "$DALIA_DATA_DIR/archive" -prune -o \( -iname "*.ttl" -o -iname "*.rdf" -o -iname "*.owl" \) -type f -print)
DALIA_FILES=$(find "$DALIA_DATA_DIR" \( -path "$DALIA_DATA_DIR/archive" -o -path "$DALIA_DATA_DIR/ontology" \) -prune -o \( -iname "*.ttl" -o -iname "*.rdf" -o -iname "*.owl" \) -type f -print)

if [ -n "$DALIA_FILES" ]; then
  echo "✔ Found RDF files for DALIA — proceeding with loading."

  for file in $DALIA_FILES; do
    filename=$(basename "$file")
    archived_file="$ARCHIVE_DIR/$filename"

    if [ -f "$archived_file" ]; then
      echo "🔁 File already archived: $filename → skipping load, replacing archive copy"
      rm -f "$archived_file"
      mv "$file" "$archived_file"
    else
      echo "📄 Loading DALIA file: $file"
      "$SCRIPTS_DIR/load.sh" "$FUSEKI_BASE/configuration/dalia.ttl" "$file"

      if [ $? -eq 0 ]; then
        echo "✅ Loaded: $file → archiving"
        mv "$file" "$archived_file"
      else
        echo "❌ Failed to load: $file → not moved"
      fi
    fi
  done

  echo "🧠 Building DALIA text index..."
  "$SCRIPTS_DIR/textindex.sh" "$FUSEKI_BASE/configuration/dalia.ttl"
else
  echo "⚠️ No RDF files found for DALIA."
fi


#
# (Re-)create "ontologies" dataset, insert RDF data from $ONTOLOGIES_DIR and build
# a text index for it.
#

# rm -Rf $FUSEKI_BASE/databases/ontologies
# if [ ! -d "$FUSEKI_BASE/databases/ontologies" ]; then
#   find $ONTOLOGIES_DIR \( -iname "*.ttl" -o -iname "*.rdf" -o -iname "*.owl" -o -iname "*.rdf.gz" \) -type f -exec $SCRIPTS_DIR/load.sh $FUSEKI_BASE/configuration/ontologies.ttl {} \;
#   $SCRIPTS_DIR/textindex.sh $FUSEKI_BASE/configuration/ontologies.ttl
# fi

ARCHIVE_DIR="$ONTOLOGIES_DIR/archive"
mkdir -p "$ARCHIVE_DIR"

# ONTO_FILES=$(find "$ONTOLOGIES_DIR" \( -iname "*.ttl" -o -iname "*.rdf" -o -iname "*.owl" -o -iname "*.rdf.gz" \) -type f)
ONTO_FILES=$(find "$ONTOLOGIES_DIR" -path "$ONTOLOGIES_DIR/archive" -prune -o \( -iname "*.ttl" -o -iname "*.rdf" -o -iname "*.owl" -o -iname "*.rdf.gz" \) -type f -print)

if [ -n "$ONTO_FILES" ]; then
  echo "✔ Found RDF files for ONTOLOGIES — proceeding with loading."

  for file in $ONTO_FILES; do
    filename=$(basename "$file")
    archived_file="$ARCHIVE_DIR/$filename"

    if [ -f "$archived_file" ]; then
      echo "🔁 File already archived: $filename → skipping load, replacing archive copy"
      rm -f "$archived_file"
      mv "$file" "$archived_file"
    else
      echo "📄 Loading ONTOLOGY file: $file"
      "$SCRIPTS_DIR/load.sh" "$FUSEKI_BASE/configuration/ontologies.ttl" "$file"

      if [ $? -eq 0 ]; then
        echo "✅ Loaded: $file → archiving"
        mv "$file" "$archived_file"
      else
        echo "❌ Failed to load: $file → not moved"
      fi
    fi
  done

  echo "🧠 Building ONTOLOGIES text index..."
  "$SCRIPTS_DIR/textindex.sh" "$FUSEKI_BASE/configuration/ontologies.ttl"
else
  echo "⚠️ No RDF files found for ONTOLOGIES."
fi


#
# Make sure the fuseki user owns $FUSEKI_BASE
#
chown -R fuseki:fuseki $FUSEKI_BASE

# NOTE: Periodic compaction was removed because it causes tasks to pile up
# and block queries. Run compaction manually when needed:
# curl -X POST "http://localhost:3030/$/compact/dalia?deleteOld=true"

exec "$@"
