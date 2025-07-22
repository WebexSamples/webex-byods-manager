# Webex Samples Template

This is the Webex Samples Template Repository, which must be used for all new code contributions. The Webex Samples Template is a standardized framework that provides contributors to the Webex Samples organization with a consistent and organized approach to creating code contributions. By using the template, contributors can create new repositories that are independent of the original repository's commit history, making it easier to track changes and maintain a clean codebase. The template also includes a sample README and linting tools for standardized code samples. Utilizing the template streamlines the contribution process and ensures consistency across the Webex Samples organization, benefiting contributors and maintaining a well-organized codebase.

## Table of Contents

- [Usage](#usage)
- [Github Actions](#github-actions)
- [Installing Prettier via npm (Local Machine)](#installing-prettier-via-npm-local-machine)
- [Installing and Running Ruff Python Linter](#installing-and-running-ruff-python-linter)
- [Pre-Commit Hooks](#pre-commit-hooks)
- [Skipping Hooks](#skipping-hooks)
- [Thanks!](#thanks)

## Usage

Using template repos varies from directly forking a repo. The commit history is cleaned, and there is no link to the original repository. This will give your new repository all the framework needed but without the history or link to other repos. It will be easier to track your changes, and your work will not be tied to the repository’s other forks.

To use this template, [follow these directions to create your new repo from the template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template). Add your project code to the new repo. Then, reach out to Adam Weeks (adweeks) or Ashton Jordan (ashjorda) to have your new repo added to this Github Organization. All newly created repos are set to private by default. Once all Github actions have passed, and your repo is complete, contact Adam or Ashton for review to make the repo public.

This template repo also contains a sample README (this file), that outlines sections you should include in your README to help properly describe the repo's contents. Additionally, you can utilize the [Standard Readme](https://github.com/RichardLitt/standard-readme) format for your README to ensure consistency and best practices.

1. **Create the repository**: First, create your repo by [following these directions to create your new repo from the template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).

2. **Clone the repository**: Next, clone this repository to your local machine using `git clone`.

3. **Install dependencies**: Install prettier/autopep8 as per the below instructions under "GitHub Actions" section to start linting your codebase.

## Github Actions

This template uses GitHub Actions workflow to enforce commonly accepted coding practices across various file formats. We use [Prettier](https://prettier.io), and [Ruff](https://docs.astral.sh/ruff/linter/) for these linting workflows. These workflows run on every pull request. And before merging is allowed, these workflows must pass. During these workflow checks, none of your code will be modified. These checks are commonly focused on spacing and proper tabbing.

The GitHub Actions workflow plays a crucial role in maintaining code quality and consistency within the project. It automates the process of enforcing coding practices, ensuring that all contributions adhere to the established standards.

Specifically, the workflow performs the following checks:

1. **Prettier Formatting**: Prettier is a code formatter that helps maintain consistent code style across the project. The workflow uses Prettier to check if the code follows the defined formatting rules. If any formatting issues are found, the workflow will fail, indicating that the code needs to be properly formatted. Please review the [`prettier.yml`](.github/workflows/prettier.yml) file to see the configuration and settings for the Prettier action.

2. **Ruff Linting**: Ruff is a Python linter that checks for coding style violations and automatically fixes them. The workflow utilizes Ruff to identify any style issues in Python code. If any violations are detected, the workflow will fail, indicating that the code needs to be corrected. Please review the [`ruff.yml`](.github/workflows/ruff.yml) file to see the configuration and settings for the Ruff action.

By running these checks on every pull request, the GitHub Actions workflow ensures that all contributions meet the required coding standards. This helps maintain a clean and consistent codebase, making it easier for developers to collaborate and understand each other's code. It also reduces the chances of introducing bugs or inconsistencies due to coding style variations.

## Installing Prettier via npm (Local Machine)

**Note: Prettier documentation link: (https://prettier.io/docs/en/install.html)**

To format your code locally, run the following:

1. Checking what changes prettier would like to make on all the files within your repo. Before writing them:

```bash
npx prettier . --check
```

2. To write the proposed changes, to ensure the prettier workflow passes. Use the following command:

```bash
npx prettier . --write
```

## Installing and Running Ruff Python Linter

**Note: Ruff Documentation: (https://github.com/astral-sh/ruff)**
To lint your Python code locally, follow these steps:

1. Install ruff:

```bash
pip install ruff
```

2. Checking what changes Ruff would like to make on all the files within your repo. Before writing them:

```bash
ruff check .
```

3. To write the proposed changes, to ensure the Ruff workflow passes. Use the following command:

```bash
ruff check --fix .
```

## Pre-Commit Hooks

This project utilizes Husky and lint-staged to automatically format code on pre-commit hooks.

[Husky](https://github.com/typicode/husky) is a Git hook manager that allows you to run scripts at specific Git lifecycle events. In this project, Husky is configured to run a script before each commit.

[lint-staged](https://github.com/lint-staged/lint-staged) is a tool that allows you to run linters on staged files. It helps ensure that only the relevant files are checked, improving performance. In this project, lint-staged is used in conjunction with Husky to format the code before it is committed.

When you make changes to your code and try to commit them, Husky triggers the lint-staged script. lint-staged then runs the configured linters on the staged files, which in this case includes Prettier and Ruff. Prettier is responsible for formatting the code according to the defined rules, while Ruff checks for style violations in Python code.

By using Husky and lint-staged, this project enforces code formatting and style consistency automatically, reducing the chances of introducing formatting issues or style violations. This ensures that the codebase remains clean and consistent, making it easier for developers to collaborate and maintain the project.

To configure Husky and lint-staged in your own project, you can follow the steps below:

1. Install Husky and lint-staged from the dev dependencies:

```bash
npm install
```

2. Enable pre-commit hooks by removing the comments from the [.husky/pre-commit](.husky/pre-commit) file:

```
# npx lint-staged
# ruff check --fix .
```

3. Save the changes and commit them to your repository. The pre-commit hooks will now run automatically before each commit, ensuring that the code is properly formatted and styled.

## Skipping Hooks

We know that it might not be optimal to have your code checked for every commit (for example, work in progress commits that will be squashed later). For those occasions, skipping the git hooks might be necessary.

### For a Single Command

Most Git commands include a `-n/--no-verify` option to skip hooks:

```sh
git commit -m "..." -n # Skips Git hooks
```

For commands without this flag, disable hooks temporarily with HUSKY=0:

```shell
HUSKY=0 git ... # Temporarily disables all Git hooks
git ... # Hooks will run again
```

### For multiple commands

To disable hooks for an extended period (e.g., during rebase/merge):

```shell
export HUSKY=0 # Disables all Git hooks
git ...
git ...
unset HUSKY # Re-enables hooks
```

## Thanks!

We truly appreciate your contribution to the Webex Samples!

Made with <3 by the Webex Developer Relations Team at Cisco
