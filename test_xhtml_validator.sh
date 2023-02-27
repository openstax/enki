#!/bin/zsh
# jv8
for xhtmlfile in $(find data/finances/_attic/IO_JSONIFIED -name "*@*.xhtml")
do
    if ! grep -q '<nav id="toc">' "$xhtmlfile"; then
        echo $xhtmlfile
        java -cp xhtml-validator/build/libs/xhtml-validator.jar org.openstax.xml.Main - all < $xhtmlfile || failure=true
        # java -cp xhtml-validator/build/libs/xhtml-validator.jar org.openstax.xml.Main - broken-link || failure=true
    fi
done