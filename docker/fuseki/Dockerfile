# Base image: https://github.com/adoptium/containers/blob/main/21/jre/ubuntu/noble/Dockerfile
# FROM eclipse-temurin:21-jre
FROM docker.io/library/eclipse-temurin:21-jre

# Variable defined in the dalia-compose-build file
ARG BUILD_ENV
ENV BUILD_ENV=$BUILD_ENV

ARG FUSEKI_VERSION=5.3.0
ARG FUSEKI_SHA256=0d5647be9bd478930478dde180bcc14f568019a21f8f62ddb1e05c4ba5cf9fb9

# Environment variables for paths
ENV FUSEKI_HOME=/fuseki
ENV FUSEKI_BASE=/database
ENV CONFIG_TEMPLATES_DIR=/config-templates
ENV DALIA_DATA_DIR=/dalia_data
ENV ONTOLOGIES_DIR=${DALIA_DATA_DIR}/ontology
ENV SCRIPTS_DIR=/scripts

RUN \
    set -ex && \
# install additional packages
    apt-get update && \
    apt-get install -y wget curl tini gosu python3 && \
    rm -rf /var/lib/apt/lists/* && \
# add user that is going to run fuseki
    groupadd --gid=10001 fuseki && \
    useradd -g fuseki --uid 10000 --no-create-home fuseki

# Create directories if they don't exist
RUN mkdir -p ${FUSEKI_HOME} ${FUSEKI_BASE} ${DALIA_DATA_DIR} ${ONTOLOGIES_DIR} ${CONFIG_TEMPLATES_DIR} ${SCRIPTS_DIR}

#
# Download and install Fuseki
#
WORKDIR /tmp

RUN \
    set -ex && \
    FUSEKI_TGZ=apache-jena-fuseki-$FUSEKI_VERSION.tar.gz && \
    wget --no-verbose https://repo1.maven.org/maven2/org/apache/jena/apache-jena-fuseki/$FUSEKI_VERSION/$FUSEKI_TGZ && \
    echo "$FUSEKI_SHA256  $FUSEKI_TGZ" | sha256sum --status -c && \
    tar -xzf $FUSEKI_TGZ && \
    rm $FUSEKI_TGZ && \
    mv apache-jena-fuseki-$FUSEKI_VERSION/* $FUSEKI_HOME/

# Copy Fuseki from host (downloaded beforehand)
# COPY fuseki_source/apache-jena-fuseki-${FUSEKI_VERSION} ${FUSEKI_HOME}/apache-jena-fuseki-${FUSEKI_VERSION}

# Copy ontology TTL files and DALIA data
# WORKDIR ${ONTOLOGIES_DIR}
COPY dalia_data/ontology/ ${ONTOLOGIES_DIR}/
# COPY if files exist only
RUN if ls dalia_data/ontology/*.ttl 1> /dev/null 2>&1; then \
    cp dalia_data/ontology/*.ttl ${DALIA_DATA_DIR}/ ; \
fi


#
# Deploy data to be loaded into the "dalia" dataset
#
WORKDIR ${DALIA_DATA_DIR}
# COPY dalia_data/*.ttl ${DALIA_DATA_DIR}/

# COPY if files exist only
RUN if ls dalia_data/*.ttl 1> /dev/null 2>&1; then \
    cp dalia_data/*.ttl ${DALIA_DATA_DIR}/ ; \
fi


# Copy config and scripts
# COPY config/ ${CONFIG_TEMPLATES_DIR}/
COPY database/configuration/*.ttl ${CONFIG_TEMPLATES_DIR}/
COPY database/config.ttl ${CONFIG_TEMPLATES_DIR}/
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
COPY scripts/load.sh ${SCRIPTS_DIR}/
COPY scripts/textindex.sh ${SCRIPTS_DIR}/
COPY scripts/compact_dalia.sh ${SCRIPTS_DIR}/
COPY scripts/healthcheck.sh ${SCRIPTS_DIR}/
COPY scripts/backup.py ${SCRIPTS_DIR}/

RUN chmod +x ${SCRIPTS_DIR}/*.sh

# Replaced with the dalia-compose.yml healthcheck configuration
# HEALTHCHECK \
#     --interval=5s \
#     --timeout=2s \
#     --start-period=120s \
#     CMD ${SCRIPTS_DIR}/healthcheck.sh

WORKDIR ${FUSEKI_HOME}

# Use it during the build to generate environment-specific content
# Important to prevent all images prod/dev/staging using the same ID
RUN echo "$BUILD_ENV" > /build_env_marker_${BUILD_ENV}

VOLUME ["${FUSEKI_HOME}", "${FUSEKI_BASE}", "${DALIA_DATA_DIR}"]

EXPOSE 3030

ENTRYPOINT ["/usr/bin/tini", "--", "sh", "/docker-entrypoint.sh"]

# JVM settings optimized for long-running server performance:
# - Xms=Xmx: Fixed heap size prevents resize pauses
# - G1GC: Low-latency garbage collector
# - AlwaysPreTouch: Pre-allocate memory at startup for consistent performance
# - MaxGCPauseMillis: Target max 200ms GC pauses
# - InitiatingHeapOccupancyPercent: Start GC at 35% to avoid memory pressure
# - G1ReservePercent: Reserve 15% for GC overhead
# - ParallelRefProcEnabled: Faster reference processing
ENV JVM_ARGS="-Xms2G -Xmx2G \
    -XX:+UseG1GC \
    -XX:MaxGCPauseMillis=200 \
    -XX:InitiatingHeapOccupancyPercent=45 \
    -XX:+ParallelRefProcEnabled \
    -XX:+ExplicitGCInvokesConcurrent"

# Query timeout: 90 seconds (90000ms) - hard limit to prevent runaway queries
# The --timeout flag enforces this at the Fuseki level
CMD ["sh", "-c", "gosu fuseki bash -c 'export JVM_ARGS=\"$JVM_ARGS\" && ./fuseki-server --timeout=90000 --verbose'"]
