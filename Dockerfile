FROM buildpack-deps:focal


# ---------------------------
# Install OS dependencies
# ---------------------------

RUN set -x \
    # && echo deb http://archive.ubuntu.com/ubuntu universe multiverse >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    # ... for princexml:
    gdebi fonts-stix libcurl4 \
    # ... for neb:
    python3 python3-pip build-essential wget openjdk-11-jre-headless libmagic1 mime-support \
    # ... for mathify:
    libpangocairo-1.0-0 libxcomposite1 libxcursor1 libxdamage1 libxi6 libxext6 libcups2 libxrandr2 libatk1.0-0 libgtk-3-0 libx11-xcb1 libnss3 libxss1 libasound2 \
    # ... for cnx-easybake:
    build-essential libicu-dev pkg-config python3-dev


# ---------------------------
# Install princexml
# ---------------------------

ENV PRINCE_VERSION=12.5.1-1
ENV PRINCE_UBUNTU_BUILD=20.04

ADD https://www.princexml.com/download/prince_${PRINCE_VERSION}_ubuntu${PRINCE_UBUNTU_BUILD}_amd64.deb /tmp/

RUN gdebi --non-interactive /tmp/prince_${PRINCE_VERSION}_ubuntu${PRINCE_UBUNTU_BUILD}_amd64.deb

# Remove unnecessary apt and temp files
RUN apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


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


# ---------------------------
# Install ruby
# ---------------------------

RUN curl -fsSL https://rvm.io/mpapis.asc | gpg --import - \
    && curl -fsSL https://rvm.io/pkuczynski.asc | gpg --import - \
    && curl -fsSL https://get.rvm.io | bash -s stable \
    && bash -lc " \
        rvm requirements \
        && rvm install 2.6.6 \
        && rvm use 2.6.6 --default \
        && rvm rubygems current \
        && gem install bundler --no-document \
        && gem install solargraph --no-document" # \
    # && echo '[[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm" # Load RVM into a shell session *as a function*' >> /home/gitpod/.bashrc.d/70-ruby
RUN echo "rvm_gems_path=/workspace/.rvm" > ~/.rvmrc


# ---------------------------
# Install mathify
# ---------------------------

COPY ./mathify/package.json ./mathify/package-lock.json /mathify/
WORKDIR /mathify/
# RUN . $HOME/.nvm/nvm.sh && npm ci
RUN PATH=$PATH:$HOME/.nvm/versions/node/v14.16.1/bin/ npm ci
# # COPY ./.dockerfiles/docker-entrypoint.sh /usr/local/bin/


# ---------------------------
# Install neb
# ---------------------------

COPY ./nebuchadnezzar/ /nebuchadnezzar/
WORKDIR /nebuchadnezzar/
# Install Python Dependencies
RUN set -x \
    && pip3 install -U pip setuptools wheel \
    && pip3 install -r ./requirements/lint.txt \
                   -r ./requirements/test.txt \
                   -r ./requirements/main.txt

# Install neb
RUN pip3 install -e .


# ---------------------------
# Install cnx-easybake
# ---------------------------

COPY ./cnx-easybake/ /cnx-easybake/
WORKDIR /cnx-easybake/
RUN python3 -m pip install -r requirements/main.txt -r requirements/test.txt

# # COPY ./ /src/
RUN python3 -m pip install -e "."


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
# Add the entrypoint
# ---------------------------
COPY ./.dockerfiles/docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]
