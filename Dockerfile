FROM buildpack-deps:jammy as base

# ---------------------------
# Install Adobe color mapping files
# ---------------------------
FROM base as adobe-colors-stage
RUN set -x \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    unzip
RUN curl -o /tmp/AdobeICCProfiles.zip https://download.adobe.com/pub/adobe/iccprofiles/win/AdobeICCProfilesCS4Win_end-user.zip \
    && unzip -o -j "/tmp/AdobeICCProfiles.zip" "Adobe ICC Profiles (end-user)/CMYK/USWebCoatedSWOP.icc" -d /adobe-icc/

# ---------------------------
# Install princexml
# ---------------------------
FROM base as princexml-stage
# Remember to run `dpkg -I prince_...deb` and add the dependencies above because they are not copied out of this stage
ENV PRINCE_VERSION=15-1
ENV PRINCE_UBUNTU_BUILD=22.04
RUN set -x \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    gdebi
RUN wget --directory-prefix=/tmp/ https://www.princexml.com/download/prince_${PRINCE_VERSION}_ubuntu${PRINCE_UBUNTU_BUILD}_$(dpkg --print-architecture).deb
RUN gdebi --non-interactive /tmp/prince_${PRINCE_VERSION}_ubuntu${PRINCE_UBUNTU_BUILD}_$(dpkg --print-architecture).deb

# ---------------------------
# Install jq
# ---------------------------
FROM base as build-jq-stage
ENV JQ_VERSION='1.6'
RUN wget --no-check-certificate https://raw.githubusercontent.com/jqlang/jq/master/sig/jq-release-old.key -O /tmp/jq-release.key \
    && wget --no-check-certificate https://raw.githubusercontent.com/jqlang/jq/master/sig/v${JQ_VERSION}/jq-linux64.asc -O /tmp/jq-linux64.asc \
    && wget --no-check-certificate https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}/jq-linux64 -O /tmp/jq-linux64 \
    && gpg --import /tmp/jq-release.key \
    && gpg --verify /tmp/jq-linux64.asc /tmp/jq-linux64 \
    && cp /tmp/jq-linux64 /usr/bin/jq \
    && chmod +x /usr/bin/jq \
    ;

# ---------------------------
# Install Pandoc
# ---------------------------
FROM base as pandoc-stage
ENV PANDOC_VERSION='3.1.2'
RUN wget https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-1-$(dpkg --print-architecture).deb -O /tmp/pandoc.deb \
    && dpkg -i /tmp/pandoc.deb \
    && rm -f /tmp/pandoc.deb \
    ;

# ---------------------------
# Install Python, NodeJS, and Java
# ---------------------------
FROM base as base-with-langs
ENV NODE_VERSION=18
RUN set -x \
    && apt-get update \
    && apt-get install -y ca-certificates curl gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | \
        gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_VERSION.x nodistro main" | \
        tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        openjdk-11-jre-headless \
        python3 \
        python3-pip \
        nodejs \
    ;


# ---------------------------
# Install mathify
# ---------------------------
FROM base-with-langs as build-mathify-stage
COPY ./mathify/package.json ./mathify/package-lock.json /workspace/enki/mathify/
RUN npm --prefix=/workspace/enki/mathify ci
COPY ./mathify/typeset /workspace/enki/mathify/typeset

# ---------------------------
# Install bakery-js
# ---------------------------
FROM base-with-langs as build-bakery-js-stage
# Install dependencies first
COPY ./bakery-js/package.json ./bakery-js/package-lock.json /workspace/enki/bakery-js/
RUN npm --prefix=/workspace/enki/bakery-js install

COPY ./bakery-js/bin/ /workspace/enki/bakery-js/bin/
COPY ./bakery-js/src/ /workspace/enki/bakery-js/src/
COPY ./bakery-js/schemas/ /workspace/enki/bakery-js/schemas/
COPY ./bakery-js/tsconfig*.json /workspace/enki/bakery-js/
RUN npm --prefix=/workspace/enki/bakery-js run build


COPY ./poet/package.json ./poet/package-lock.json ./poet/tsconfig*.json /workspace/enki/poet/
# Maybe don't need the client files
COPY ./poet/client/package.json ./poet/client/package-lock.json /workspace/enki/poet/client/
COPY ./poet/server/package.json ./poet/server/package-lock.json /workspace/enki/poet/server/

RUN npm --prefix=/workspace/enki/poet install

COPY ./poet/server/src/ /workspace/enki/poet/server/src/
COPY ./poet/common/src/ /workspace/enki/poet/common/src/
COPY ./poet/server/tsconfig*.json /workspace/enki/poet/server/
COPY ./poet/server/webpack.config.js /workspace/enki/poet/server/

# Just for notes: cd /workspace/enki/poet && ./node_modules/.bin/ts-node server/src/model/_cli.ts validate /tmp/build/0000000/_attic/IO_FETCHED
# RUN npm --prefix=/workspace/enki/poet run build:server


# ===========================
# Install Python Packages
# ===========================

# TODO: Decouple node by moving the bakery javascript stuff into bakery-js

# ---------------------------
# Install neb and bakery-scripts
# ---------------------------
FROM base-with-langs AS build-python-stage
RUN set -x \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    python3-dev libgit2-dev

# Install dependencies
COPY ./nebuchadnezzar/requirements /workspace/enki/nebuchadnezzar/requirements
COPY ./bakery-src/scripts/requirements.txt /workspace/enki/bakery-src/scripts/

RUN pip3 install \
    -r /workspace/enki/nebuchadnezzar/requirements/main.txt \
    -r /workspace/enki/bakery-src/scripts/requirements.txt

# Install scripts
COPY ./nebuchadnezzar/ /workspace/enki/nebuchadnezzar/
COPY ./bakery-src/scripts/*.py ./bakery-src/scripts/*.js ./bakery-src/scripts/*.json /workspace/enki/bakery-src/scripts/
COPY ./bakery-src/scripts/gdoc/ /workspace/enki/bakery-src/scripts/gdoc/
COPY ./bakery-src/scripts/ppt/ /workspace/enki/bakery-src/scripts/ppt/
RUN pip3 install /workspace/enki/nebuchadnezzar/ /workspace/enki/bakery-src/scripts/.

RUN npm --prefix /workspace/enki/bakery-src/scripts install --production /workspace/enki/bakery-src/scripts


# ================
# Java
# ================

# ---------------------------
# Build xhtml-validator jar
# ---------------------------
FROM base-with-langs AS build-xhtml-validator-stage
COPY ./xhtml-validator/ /workspace/enki/xhtml-validator/

# Issues with gradle daemon on Apple M1 chips.
ENV GRADLE_OPTS=-Dorg.gradle.daemon=false
RUN cd /workspace/enki/xhtml-validator && ./gradlew jar


# ---------------------------
# Build kcov
# ---------------------------
FROM base AS build-kcov-stage

RUN git clone https://github.com/SimonKagstrom/kcov /kcov-src/

RUN apt-get update \
    && apt-get install -y \
        binutils-dev \
        build-essential \
        cmake \
        git \
        libcurl4-openssl-dev \
        libdw-dev \
        libiberty-dev \
        libssl-dev \
        ninja-build \
        python3 \
        zlib1g-dev \
        ;

RUN mkdir /kcov-src/build \
    && cd /kcov-src/build \
    && cmake -G 'Ninja' .. \
    && cmake --build . \
    && cmake --build . --target install \
    ;

# ---------------------------
# Build jo
# ---------------------------
FROM base as build-jo-stage

ENV JO_VERSION=1.4
RUN curl https://codeload.github.com/jpmens/jo/tar.gz/refs/tags/$JO_VERSION > jo-source.tar.gz \
    && tar -xvzf jo-source.tar.gz \
    && cd ./jo-$JO_VERSION \
    && autoreconf -i \
    && ./configure \
    && make check \
    && make install \
    ;

# ===========================
# The Final Stage
# ===========================
FROM base-with-langs as runner

# ---------------------------
# Install OS packages
# necessary to build the
# other stages.
# ---------------------------

RUN set -x \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    # ... for docker-entrypoint
    gosu \
    # ... for princexml:
    fonts-stix libcurl4 \
    libaom3 libavif13 libc6 libcurl4 libfontconfig1 libfreetype6 libgif7 libjpeg8 liblcms2-2 libpng16-16 libssl3 libtiff5 libwebp7 libwebpdemux2 libxml2 zlib1g \
    # ... for bakery-scripts
    pkg-config libmagic1 \
    mime-support wget xsltproc lsb-release git \
    imagemagick icc-profiles-free curl unzip \
    libgit2-dev \
    wkhtmltopdf \
    # ... for neb:
    wget libmagic1 mime-support \
    # ... for mathify:
    libpangocairo-1.0-0 libxcomposite1 libxcursor1 libxdamage1 libxi6 libxext6 libcups2 libxrandr2 \
    libatk1.0-0 libgtk-3-0 libx11-xcb1 libnss3 libxss1 libasound2 \
    libxcb-dri3-0 libdrm2 libgbm1 \
    # ... for cnx-easybake:
    build-essential pkg-config \
    # ---------------------------
    # Dependencies that are not needed to prepare
    # the other steps but are necessary to run the code.
    # ---------------------------
    libdw-dev \
    libxtst6 \
    # ... for parsing XML files: https://github.com/openstax/content-synchronizer/pull/7
    xmlstarlet \
    # ... for zipping docx files
    zip \
    # For debugging
    vim \
    nano \
    ;

# Remove unnecessary apt and temp files
RUN apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


# ---------------------------
# Install the Concourse Resource
# ---------------------------

WORKDIR /workspace/enki/corgi-concourse-resource/
COPY ./corgi-concourse-resource /workspace/enki/corgi-concourse-resource/
RUN set -x \
    && pip3 install /workspace/enki/corgi-concourse-resource/. \
    && mkdir -p /opt/resource \
    && for script in check in out; do ln -s $(which $script) /opt/resource/; done

# ---------------------------
# Install epub validator
# ---------------------------

ENV EPUB_VALIDATOR_VERSION=5.0.0
RUN mkdir /workspace/enki/epub-validator \
    && cd /workspace/enki/epub-validator \
    && curl --location --output epubvalidator.zip https://github.com/w3c/epubcheck/releases/download/v$EPUB_VALIDATOR_VERSION/epubcheck-$EPUB_VALIDATOR_VERSION.zip \
    && unzip epubvalidator.zip \
    ;

# ---------------------------
# Install ruby
# ---------------------------
ENV RUBY_VERSION=3.2.2

RUN curl -fsSL https://rvm.io/mpapis.asc | gpg --import - \
    && curl -fsSL https://rvm.io/pkuczynski.asc | gpg --import - \
    && curl -fsSL https://get.rvm.io | bash -s stable \
    && bash -lc " \
        rvm requirements \
        && rvm install ${RUBY_VERSION} \
        && rvm use ${RUBY_VERSION} --default \
        && rvm rubygems current \
        && gem install bundler --no-document"
RUN echo "rvm_gems_path=/workspace/.rvm" > ~/.rvmrc
ENV PATH=$PATH:/usr/local/rvm/rubies/ruby-${RUBY_VERSION}/bin/
ENV GEM_HOME=/usr/local/rvm/gems/ruby-${RUBY_VERSION}
ENV GEM_PATH=/usr/local/rvm/gems/ruby-${RUBY_VERSION}:/usr/local/rvm/gems/ruby-${RUBY_VERSION}@global

# ---------------------------
# Install recipes
# ---------------------------

COPY ./cookbook/ /workspace/enki/cookbook/
RUN cd /workspace/enki/cookbook \
    && gem install bundler --no-document \
    && gem install byebug --no-document \
    && bundle install \
    && bundle config set no-cache 'true' \
    && bundle config set silence_root_warning 'true'

COPY ./cookbook/ /workspace/enki/cookbook/

# ---------------------------
# Copy the stages over
# ---------------------------

ENV PROJECT_ROOT=/workspace/enki

COPY --from=adobe-colors-stage /adobe-icc/ /usr/share/color/icc/
COPY --from=princexml-stage /usr/bin/prince /usr/bin/
COPY --from=princexml-stage /usr/lib/prince /usr/lib/prince
COPY --from=build-jq-stage /usr/bin/jq /usr/bin/jq
COPY --from=pandoc-stage /usr/bin/pandoc /usr/bin


COPY --from=build-jo-stage /usr/local/bin/jo /usr/local/bin/jo
COPY --from=build-kcov-stage /usr/local/bin/kcov* /usr/local/bin/
COPY --from=build-kcov-stage /usr/local/share/doc/kcov /usr/local/share/doc/kcov

COPY --from=build-xhtml-validator-stage /workspace/enki/xhtml-validator/build/libs/xhtml-validator.jar /workspace/enki/xhtml-validator/build/libs/xhtml-validator.jar
COPY --from=build-bakery-js-stage /workspace/enki/bakery-js/ /workspace/enki/bakery-js/
COPY --from=build-mathify-stage /workspace/enki/mathify/ /workspace/enki/mathify/
COPY --from=build-python-stage /workspace/enki/bakery-src/scripts /workspace/enki/bakery-src/scripts
COPY --from=build-python-stage /workspace/enki/bakery-src/scripts/gdoc /workspace/enki/bakery-src/scripts/gdoc
COPY --from=build-python-stage /workspace/enki/bakery-src/scripts/ppt /workspace/enki/bakery-src/scripts/ppt
COPY --from=build-python-stage /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=build-python-stage \
    /usr/local/bin/neb \
    /usr/local/bin/download-exercise-images \
    /usr/local/bin/assemble-meta \
    /usr/local/bin/link-extras \
    /usr/local/bin/link-single \
    /usr/local/bin/bake-meta \
    /usr/local/bin/disassemble \
    /usr/local/bin/jsonify \
    /usr/local/bin/check-feed \
    /usr/local/bin/copy-resources-s3 \
    /usr/local/bin/gdocify \
    /usr/local/bin/upload-docx \
    /usr/local/bin/mathmltable2png \
    /usr/local/bin/fetch-map-resources \
    /usr/local/bin/fetch-update-meta \
    /usr/local/bin/patch-same-book-links \
    /usr/local/bin/link-rex \
    /usr/local/bin/pptify \
    /usr/local/bin/aws \
    /usr/local/bin/

COPY --from=build-bakery-js-stage /workspace/enki/poet/ /workspace/enki/poet/


# Copy ce-styles
COPY ./ce-styles/styles/output/ /workspace/enki/ce-styles/styles/output/


ENV PATH=$PATH:/dockerfiles/
COPY ./dockerfiles/fix-perms /usr/bin/
COPY ./dockerfiles/10-fix-perms.sh /etc/entrypoint.d/
COPY ./dockerfiles/steps /dockerfiles/steps
COPY ./dockerfiles/entrypointd.sh \
    ./dockerfiles/docker-entrypoint.sh \
    ./dockerfiles/docker-entrypoint-with-kcov.sh \
    ./dockerfiles/enki-in-container \
    /dockerfiles/

COPY ./step-config.json $PROJECT_ROOT

WORKDIR /tmp/build/0000000/

RUN useradd --create-home -u 5000 app
ENV RUN_AS="app:app"

ENV ORIG_ENTRYPOINT='/dockerfiles/docker-entrypoint-with-kcov.sh'
ENTRYPOINT ["/dockerfiles/entrypointd.sh"]
HEALTHCHECK CMD /dockerfiles/healthcheckd.sh
