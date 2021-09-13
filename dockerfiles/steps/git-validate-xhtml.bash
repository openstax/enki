# LCOV_EXCL_START
while IFS= read -r -d '' xhtmlfile
do
    say "XHTML-validating $xhtmlfile"
    try java -cp $XHTML_VALIDATOR_ROOT/xhtml-validator.jar org.openstax.xml.Main - duplicate-id broken-link < "$xhtmlfile"
done <   <(find $IO_DISASSEMBLE_LINKED -name '*.xhtml' -print0)
# LCOV_EXCL_STOP
