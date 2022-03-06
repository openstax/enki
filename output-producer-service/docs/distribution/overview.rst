.. _distribution-pipeline-overview:


########
Overview
########

The Distribution Pipeline generates JSON files corresponding to the page and book
contents. The source repository contains schemas for the
`book <https://github.com/openstax/output-producer-service/blob/master/bakery/src/scripts/book-schema.json>`_
and `page <https://github.com/openstax/output-producer-service/blob/master/bakery/src/scripts/page-schema.json>`_
structures. In addition, the pipeline generates XHTML files that reflect the ``content``
field of the corresponding JSON as a convenience for development and QA.

Work for the Distribution Pipeline is defined using a JSON file that can be accessed
via a URL. Specifically, production pipelines will use the `approved-books.json <https://github.com/openstax/content-manager-approved-books/blob/master/approved-books.json>`_
file in the `content-managers-approved-books <https://github.com/openstax/content-manager-approved-books>`_
repository. For development or QA, one can use a file that conforms to the `schema <https://github.com/openstax/content-manager-approved-books/blob/master/schema.json>`_
and hosted anywhere (e.g. an alternative GitHub repo, S3, etc.).

The pipeline itself is implemented as two jobs:

1. ``feeder``: Decides what should be built based upon the entries in the accepted books JSON list and current state in S3
2. ``bakery``: Series of tasks to build a single book

The ``feeder`` job is invoked periodically by a time resource configured with a
desired tick interval in the pipeline. It will submit multiple book entries (up
to some configured limit) by writing to a versioned S3 file. Each write will be a
JSON object with the required book parameters.

The ``bakery`` job is triggered by the S3 resource. When there are multiple
versions of the file available, Concourse will run concurrent builds of this job.
Each job will write a .complete file to S3 which the ``feeder`` job can use to
identify books that have been already built.

.. seqdiag::

  seqdiag {
      activation = none;
      "Pipeline\n(Feeder job)" -> "S3 versioned file" [label = 'Write multiple versions based upon accepted books JSON'];
      "S3 versioned file" -> "Pipeline\n(Bakery job)" [label = 'S3 triggers Bakery job with book per version'];
      "Pipeline\n(Bakery job)" -> "S3 .complete file\n(per book)" [label = 'Write .complete file on success'];
  }

******************
Gatekeeper service
******************

The above captures the general design of the Distribution Pipeline. In staging
and production deployments we also incorporate a `Gatekeeper bucket / service <https://github.com/openstax/unified-deployment/blob/master/apps/web_hosting_content_s3/cfn/gatekeeper_bucket.yml>`_
as a protection mechanism to provide immutability of files served to end users.
Specifically, instead of configuring a pipeline to write directly to the bucket
which gets used as the CloudFront origin, we configure it to write to an intermediate
Gatekeeper bucket. Each PUT to this bucket results in the triggering of a Lambda function
through S3 events which determines whether to copy the file to the ``primary``
bucket. It is possible for the Lambda function to get invoked multiple times for
the same file because:

* The same ``resource`` file / key gets written multiple times by independent builds (e.g. two books which share resources fire close enough together in time that the file existence checks return a false negative due to eventual consistency)

* Multiple events get emitted for the same S3 file version (this is possible since Amazon S3 event notifications are designed to be delivered at least once versus only once)

These multiple invocations along with the fact that copies to the ``primary``
bucket are gated upon the file being detected as not present means we cannot
guarantee a file will never be written twice to the primary. Instead, the guarantee
provided by the Gatekeeper is files are immutable and won't be overwritten once
reads to it are consistent. Said differently, it's possible for files in the
``primary`` bucket to have more than one version, but no additional versions can
be created once consistency is reached.

Note: The version issues are (currently) limited to resource files which themselves
have names generated using the hash of contents. Therefore, even though a file may
have multiple versions, it is very unlikely that the two versions are different.
