# LCOV_EXCL_START
for xhtmlfile in $(find ${IO_DISASSEMBLE_LINKED} -name '*.xhtml')
do
    say "XHTML-validating ${xhtmlfile}"
    try java -cp $XHTML_VALIDATOR_ROOT/xhtml-validator.jar org.openstax.xml.Main "$xhtmlfile" duplicate-id broken-link
done
# LCOV_EXCL_STOP
