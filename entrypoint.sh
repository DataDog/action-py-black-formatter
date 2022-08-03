#!/bin/bash
set -e # Increase bash strictness

GIT_HASH_HEAD_REF="$(git rev-parse HEAD)"
# deepen git history just enough from a shallow clone
while [ -z $( git merge-base origin/${INPUT_BLACK_MAIN_BRANCH} "$GIT_HASH_HEAD_REF") ]; do
    git fetch -q --deepen=10 origin ${INPUT_BLACK_MAIN_BRANCH} "$GIT_HASH_HEAD_REF";
done
# get changed files
git diff --diff-filter=d --name-only "$(git merge-base origin/${INPUT_BLACK_MAIN_BRANCH} "$GIT_HASH_HEAD_REF")".."$GIT_HASH_HEAD_REF" > /tmp/files_changed.txt
# Then filter the list to contain just feature flag file changes
cat /tmp/files_changed.txt | { grep "*.py$" || true; } > /tmp/changed_python_files.txt
# print these out
cat /tmp/changed_python_files.txt
# Then run the script to find invalid feature flag configurations


set -o pipefail

# If no arguments are given use current working directory
black_args=(".")
if [[ "$#" -eq 0 && "${INPUT_BLACK_ARGS}" != "" ]]; then
  black_args+=(${INPUT_BLACK_ARGS})
elif [[ "$#" -ne 0 && "${INPUT_BLACK_ARGS}" != "" ]]; then
  black_args+=($* ${INPUT_BLACK_ARGS})
elif [[ "$#" -ne 0 && "${INPUT_BLACK_ARGS}" == "" ]]; then
  black_args+=($*)
else
  # Default (if no args provided).
  black_args+=("--check" "--diff")
fi

# Check if formatting was requested
regex='\s+(--diff|--check)\s?'
if [[ "${black_args[*]}" =~ $regex ]]; then
  formatting="false"
  black_print_str="Checking"
else
  formatting="true"
  black_print_str="Formatting"
fi

# Check if '-q' or `--quiet` flags are present
quiet="false"
black_args_tmp=()
for item in "${black_args[@]}"; do
  if [[ "${item}" != "-q" && "${item}" != "--quiet" ]]; then
    black_args_tmp+=("${item}")
  else
    # Remove `quiet` related flags
    # NOTE: Prevents us from checking if files were formatted
    if [[ "${formatting}" != 'true' ]]; then
      black_args_tmp+=("${item}")
    fi
    quiet="true"
  fi
done

black_exit_val="0"
echo "[action-black] ${black_print_str} python code using the black formatter..."
black_output="$(cat /tmp/changed_python_files.txt | xargs black ${black_args_tmp[*]} 2>&1)" || black_exit_val="$?"
if [[ "${quiet}" != 'true' ]]; then
  echo "${black_output}"
fi

# Check for black errors
if [[ "${formatting}" != "true" ]]; then
  echo "::set-output name=is_formatted::false"
  if [[ "${black_exit_val}" -eq "0" ]]; then
    black_error="false"
  elif [[ "${black_exit_val}" -eq "1" ]]; then
    black_error="true"
  elif [[ "${black_exit_val}" -eq "123" ]]; then
    black_error="true"
    echo "[action-black] ERROR: Black found a syntax error when checking the" \
      "files (error code: ${black_exit_val})."
  else
    echo "[action-black] ERROR: Something went wrong while trying to run the" \
      "black formatter (error code: ${black_exit_val})."
    exit 1
  fi
else
  # Check if black formatted files
  regex='\s?[0-9]+\sfiles?\sreformatted(\.|,)\s?'
  if [[ "${black_output[*]}" =~ $regex ]]; then
    echo "::set-output name=is_formatted::true"
  else
    echo "::set-output name=is_formatted::false"
  fi

  # Check if error was encountered
  if [[ "${black_exit_val}" -eq "0" ]]; then
    black_error="false"
  elif [[ "${black_exit_val}" -eq "123" ]]; then
    black_error="true"
    echo "[action-black] ERROR: Black found a syntax error when checking the" \
      "files (error code: ${black_exit_val})."
  else
    echo "::set-output name=is_formatted::false"
    echo "[action-black] ERROR: Something went wrong while trying to run the" \
      "black formatter (error code: ${black_exit_val})."
    exit 1
  fi
fi

# Throw error if an error occurred and fail_on_error is true
if [[ "${INPUT_FAIL_ON_ERROR,,}" = 'true' && "${black_error}" = 'true' ]]; then
  exit 1
fi
