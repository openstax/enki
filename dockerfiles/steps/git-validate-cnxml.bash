check_input_dir IO_FETCHED

# Validate collections and modules without failing fast
failure=false

try-coverage /workspace/enki/venv/bin/validate-collxml $IO_FETCHED/collections/*.xml || failure=true
try-coverage /workspace/enki/venv/bin/validate-cnxml $IO_FETCHED/modules/**/*.cnxml || failure=true

if $failure; then
    exit 1 # LCOV_EXCL_LINE
fi        
