.. _pdf-pipeline-overview:

##############
Overview (WIP)
##############

The PDF system acts as a central location for users to create jobs and view
their status. When a user creates a job they are needing to produce an output
PDF for a book. A book is typically called a collection by Content
Managers and others that work directly with content.

When a job is created it will be placed in a queue. When the output pipeline is
ready it will read the necessary information from the job and begin producing
the PDF output. Upon completion, the job status will be updated with
a completed status and a link for the user to download the specified output.

.. blockdiag::

    blockdiag workflow {
       // Set labels to nodes
       A [label = "PDF Frontend UI"];
       B [label = "Create Job"];
       C [label = "Job Queued"];
       D [label = "Output Pipeline"];
       E [label = "Output URL"];
      A -> B -> C -> D -> E -> A;
    }