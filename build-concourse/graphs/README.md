
```mermaid
graph TB
    Misc-Resources -- s3-git-queue --> git-dequeue-book
    step-bake -- baked --> step-epub
    step-bake -- baked --> step-pdf
    step-bake -- baked --> step-postbake
    step-disassemble -- disassemble-linked --> step-docx
    step-disassemble -- disassemble-linked --> step-epub
    step-disassemble -- disassemble-linked --> step-jsonify
    step-docx -- docx --> step-docx-meta
    step-fetch -- fetched --> step-bake
    step-fetch -- fetched --> step-epub
    step-fetch -- fetched --> step-jsonify
    step-fetch -- fetched --> step-postbake
    step-fetch -- fetched --> step-prebake
    step-jsonify -- jsonified --> step-docx
    step-jsonify -- jsonified --> step-upload-book
    step-pdf -- artifacts --> step-pdf-meta
    step-postbake -- bake-meta --> step-disassemble
    step-postbake -- linked --> step-disassemble
    step-postbake -- linked --> step-pdf
    step-prebake -- assembled --> step-bake
    step-prebake -- assemble-meta --> step-postbake
    step-prebake -- fetch-meta --> step-docx
    step-prebake -- fetch-meta --> step-pdf
    step-prebake -- resources --> step-bake
    step-prebake -- resources --> step-docx
    step-prebake -- resources --> step-epub
    step-prebake -- resources --> step-jsonify
    step-prebake -- resources --> step-pdf
    step-prebake -- resources --> step-upload-book
```
