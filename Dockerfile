FROM buildpack-deps:focal as base


# ---------------------------
# Install OS packages
# necessary to build the
# other stages.
# ---------------------------

RUN set -x \
    # && echo deb http://archive.ubuntu.com/ubuntu universe multiverse >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    # ... for princexml:
    gdebi fonts-stix libcurl4 \
    # ... for bakery-scripts
    build-essential libicu-dev pkg-config libmagic1 \
    mime-support wget curl xsltproc lsb-release git \
    imagemagick icc-profiles-free curl unzip \
    # ... for neb:
    python3 python3-pip python3-venv build-essential wget openjdk-11-jre-headless libmagic1 mime-support \
    # ... for mathify:
    libpangocairo-1.0-0 libxcomposite1 libxcursor1 libxdamage1 libxi6 libxext6 libcups2 libxrandr2 \
    libatk1.0-0 libgtk-3-0 libx11-xcb1 libnss3 libxss1 libasound2 \
    libxcb-dri3-0 libdrm2 libgbm1 \
    # ... for cnx-easybake:
    build-essential libicu-dev pkg-config python3-dev


# ---------------------------
# Install princexml
# ---------------------------

ENV PRINCE_VERSION=12.5.1-1
ENV PRINCE_UBUNTU_BUILD=20.04

RUN wget --directory-prefix=/tmp/ https://www.princexml.com/download/prince_${PRINCE_VERSION}_ubuntu${PRINCE_UBUNTU_BUILD}_amd64.deb

RUN gdebi --non-interactive /tmp/prince_${PRINCE_VERSION}_ubuntu${PRINCE_UBUNTU_BUILD}_amd64.deb

# ---------------------------
# Install jq and Pandoc
# ---------------------------
ENV JQ_VERSION='1.6'
ENV PANDOC_VERSION='2.11.3.2'

RUN wget --no-check-certificate https://raw.githubusercontent.com/stedolan/jq/master/sig/jq-release.key -O /tmp/jq-release.key && \
    wget --no-check-certificate https://raw.githubusercontent.com/stedolan/jq/master/sig/v${JQ_VERSION}/jq-linux64.asc -O /tmp/jq-linux64.asc && \
    wget --no-check-certificate https://github.com/stedolan/jq/releases/download/jq-${JQ_VERSION}/jq-linux64 -O /tmp/jq-linux64 && \
    gpg --import /tmp/jq-release.key && \
    gpg --verify /tmp/jq-linux64.asc /tmp/jq-linux64 && \
    cp /tmp/jq-linux64 /usr/bin/jq && \
    chmod +x /usr/bin/jq && \
    rm -f /tmp/jq-release.key && \
    rm -f /tmp/jq-linux64.asc && \
    rm -f /tmp/jq-linux64

RUN wget https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-1-amd64.deb -O /tmp/pandoc.deb && \
    dpkg -i /tmp/pandoc.deb && \
    rm -f /tmp/pandoc.deb


# Remove unnecessary apt and temp files
RUN apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


# ---------------------------
# Install ruby
# ---------------------------

ENV RUBY_VERSION=2.6.6

RUN curl -fsSL https://rvm.io/mpapis.asc | gpg --import - \
    && curl -fsSL https://rvm.io/pkuczynski.asc | gpg --import - \
    && curl -fsSL https://get.rvm.io | bash -s stable \
    && bash -lc " \
        rvm requirements \
        && rvm install ${RUBY_VERSION} \
        && rvm use ${RUBY_VERSION} --default \
        && rvm rubygems current \
        && gem install bundler --no-document" # \
    # && echo '[[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm" # Load RVM into a shell session *as a function*' >> /home/gitpod/.bashrc.d/70-ruby
RUN echo "rvm_gems_path=/workspace/.rvm" > ~/.rvmrc


# ---------------------------
# Install node
# ---------------------------

# Source: https://github.com/gitpod-io/workspace-images/blob/master/full/Dockerfile#L139
ENV NODE_VERSION=14.16.1
RUN curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.37.2/install.sh | PROFILE=/dev/null bash \
    && bash -c ". $HOME/.nvm/nvm.sh \
        && nvm install $NODE_VERSION \
        && nvm alias default $NODE_VERSION \
        && npm install -g typescript yarn node-gyp"
    # && echo ". ~/.nvm/nvm-lazy.sh"  >> /home/gitpod/.bashrc.d/50-node

ENV PATH=$PATH:/root/.nvm/versions/node/v$NODE_VERSION/bin/


# -----------------------
# Create Virtualenv
# -----------------------

RUN python3 -m venv /opt/venv && \
  . /opt/venv/bin/activate && \
  pip3 install --no-cache-dir -U 'pip<20'


# -----------------------
# Install bakery-scripts
# -----------------------

FROM base as build-bakery-scripts-stage

ENV BAKERY_SCRIPTS_ROOT=./output-producer-service/bakery/src/scripts

COPY ${BAKERY_SCRIPTS_ROOT}/requirements.txt /bakery-scripts/scripts/
WORKDIR /bakery-scripts/

RUN . /opt/venv/bin/activate && pip3 install -r scripts/requirements.txt

COPY ${BAKERY_SCRIPTS_ROOT}/*.py ${BAKERY_SCRIPTS_ROOT}/*.js ${BAKERY_SCRIPTS_ROOT}/*.json /bakery-scripts/scripts/
COPY ${BAKERY_SCRIPTS_ROOT}/gdoc/ /bakery-scripts/gdoc/

RUN . /opt/venv/bin/activate && pip3 install /bakery-scripts/scripts/.
RUN npm --prefix /bakery-scripts/scripts install --production /bakery-scripts/scripts

# TODO: Move this into bakery-scripts/scripts/package.json
RUN npm install pm2@4.5.0



# ---------------------------
# Install mathify
# ---------------------------

FROM base as build-mathify-stage

COPY ./mathify/package.json ./mathify/package-lock.json /mathify/
WORKDIR /mathify/
RUN npm ci
COPY ./mathify/typeset /mathify/typeset

# ---------------------------
# Install neb
# ---------------------------

FROM base as build-neb-stage

COPY ./nebuchadnezzar/requirements /nebuchadnezzar/requirements
WORKDIR /nebuchadnezzar/
# Install Python Dependencies
RUN set -x \
    && . /opt/venv/bin/activate \
    && pip3 install -U setuptools wheel \
    && pip3 install -r ./requirements/main.txt

COPY ./nebuchadnezzar/ /nebuchadnezzar/

# Install neb
RUN . /opt/venv/bin/activate \
    && pip3 install .


# ---------------------------
# Install cnx-easybake
# ---------------------------
FROM base AS build-easybake-stage

COPY ./cnx-easybake/requirements/main.txt /cnx-easybake/requirements/
WORKDIR /cnx-easybake/
RUN . /opt/venv/bin/activate && python3 -m pip install -r requirements/main.txt

COPY ./cnx-easybake/ /cnx-easybake/
RUN . /opt/venv/bin/activate && python3 -m pip install "."


# ---------------------------
# Install xhtml-validator jar
# ---------------------------
FROM base AS build-xhtml-validator-stage
COPY ./xhtml-validator/ /xhtml-validator/
WORKDIR /xhtml-validator

RUN ./gradlew jar
# FROM validator/validator:20.3.16


# ===========================
# The Final Stage
# ===========================
FROM base as runner

# ---------------------------
# Install dependencies that
# are not needed to prepare
# the other steps.
# ---------------------------
RUN set -x \
    ### Git ###
    add-apt-repository -y ppa:git-core/ppa \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        git


# ---------------------------
# Install recipes
# ---------------------------

COPY ./recipes/ /recipes/
WORKDIR /recipes/

RUN bash -lc " \
    gem install bundler --no-document && \
    gem install byebug --no-document && \
    bundle config set no-cache 'true' && \
    bundle config set silence_root_warning 'true'"

RUN bash -lc " \
    ./scripts/install_used_gem_versions"


# ---------------------------
# Copy the stages over
# ---------------------------
COPY --from=build-xhtml-validator-stage /xhtml-validator/build/libs/xhtml-validator.jar /xhtml-validator/
COPY --from=build-easybake-stage /opt/venv/ /opt/venv/
COPY --from=build-mathify-stage /mathify/ /mathify/
COPY --from=build-mathify-stage /opt/venv/ /opt/venv/
COPY --from=build-bakery-scripts-stage /opt/venv/ /opt/venv/
COPY --from=build-bakery-scripts-stage /bakery-scripts/scripts /bakery-scripts/scripts
COPY --from=build-neb-stage /opt/venv/ /opt/venv/

# Copy cnx-recipes styles
COPY ./cnx-recipes/recipes/output/ /cnx-recipes-recipes-output/
COPY ./cnx-recipes/styles/output/ /cnx-recipes-styles-output/

COPY ./docker-entrypoint.sh /usr/local/bin/


ENTRYPOINT ["docker-entrypoint.sh"]
