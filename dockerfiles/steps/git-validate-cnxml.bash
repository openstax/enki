check_input_dir IO_FETCHED

# Validate collections and modules without failing fast
failure=false

validate-collxml $IO_FETCHED/collections/*.xml || failure=true
validate-cnxml $IO_FETCHED/modules/**/*.cnxml || failure=true

if $failure; then
    exit 1 # LCOV_EXCL_LINE
fi        
