# AGENTS.md

Guidance for AI coding agents working in this repository.

## Commit identity

Author and commit only as `Cody Dracars <cdracars@gmail.com>`. Never use a
work or employer email address for commits in this repository.

Before committing, check `git config user.email`. If it shows anything else,
pass the identity for that commit (`git -c user.name="Cody Dracars" -c
user.email=cdracars@gmail.com commit ...`) or set it for this repository only;
don't change global git config. Don't rewrite existing history to change
authors unless Cody asks.
