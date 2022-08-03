# Action-py-black-formatter GitHub Action

This is a fork of rickstaa/action-black so that we can backport an older version of black working. 

## Quickstart

In it's simplest form this action can be used to check/format your code using the black formatter.

```yaml
name: black-action
on: [push, pull_request]
jobs:
  linter_name:
    name: runner / black formatter
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: rickstaa/action-black@v1
        with:
          black_args: ". --check"
```

## Inputs

### `black_args`

**optional**: Black input arguments. Defaults to `. --check --diff`.

### `fail_on_error`

**optional**: Exit code when black formatting errors are found \[true, false]. Defaults to 'true'.

## Outputs

### `is_formatted`

Boolean specifying whether any files were formatted using the black formatter.

## Advanced use cases

### Annotate changes

This action can be combined with [reviewdog/action-suggester](https://github.com/reviewdog/action-suggester) also to annotate any possible changes (uses `git diff`).

```yaml
name: black-action
on: [push, pull_request]
jobs:
  linter_name:
    name: runner / black
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Check files using the black formatter
        uses: datadog/action-py-black-formatter@v1
        id: action_black
        with:
          black_args: "."
      - name: Annotate diff changes using reviewdog
        if: steps.action_black.outputs.is_formatted == 'true'
        uses: reviewdog/action-suggester@v1
        with:
          tool_name: blackfmt
```

### Commit changes or create a pull request

This action can be combined with [peter-evans/create-pull-request](https://github.com/peter-evans/create-pull-request) to also apply the annotated changes to the repository.

```yaml
name: black-action
on: [push, pull_request]
jobs:
  linter_name:
    name: runner / black
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Check files using the black formatter
        uses: datadog/action-py-black-formatter@v1
        id: action_black
        with:
          black_args: "."
      - name: Create Pull Request
        if: steps.action_black.outputs.is_formatted == 'true'
        uses: peter-evans/create-pull-request@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          title: "Format Python code with psf/black push"
          commit-message: ":art: Format Python code with psf/black"
          body: |
            There appear to be some python formatting errors in ${{ github.sha }}. This pull request
            uses the [psf/black](https://github.com/psf/black) formatter to fix these issues.
          base: ${{ github.head_ref }} # Creates pull request onto pull request or commit branch
          branch: actions/black
```
