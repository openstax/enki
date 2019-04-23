FROM python:3.6-jessie

COPY requirements /tmp/requirements

# Install Python Dependencies
RUN set -x \
    && pip install -U pip setuptools wheel \
    && pip install -r /tmp/requirements/lint.txt \
                   -r /tmp/requirements/test.txt \
                   -r /tmp/requirements/main.txt

# Copy the project into the container
COPY . /app/

# Set the working directory for our app
WORKDIR /app/

# Install neb
RUN pip install -e .

