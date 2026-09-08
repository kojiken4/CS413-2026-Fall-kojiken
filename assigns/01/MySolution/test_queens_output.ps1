Set-Location $PSScriptRoot
# Strip Windows carriage returns before passing commands to Bash.
wsl -d Ubuntu -- bash -c ('
set -e                                                      # stops execution upon nonzero exitcode
patscc -o queens queens.dats                                # compile ats program
./queens > queens-ats-output.txt
echo "Saved ATS output" 
python3 queens.py > queens-py-output.txt
echo "Saved Python output"
diff -u queens-ats-output.txt queens-py-output.txt
echo "PASS: outputs match"                                  # will only print if above line returned exitcode 0 (due to set -e)
' -replace "`r", "")

exit $LASTEXITCODE  # Return WSL's exit code from PowerShell.
