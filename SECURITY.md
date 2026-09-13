# Security policy

## Reporting a vulnerability

Please report suspected security issues privately through the repository
owner's GitHub security contact rather than opening a public issue. Include
the affected version, operating system, reproduction steps, and any relevant
logs or hashes. Do not attach confidential CAD files.

If private vulnerability reporting is not enabled, open an issue titled
“Private security report requested” without including exploit details; a
maintainer will provide a private channel.

## Scope

Reports involving the Fusion add-in, bundled native DLLs, release packaging,
engine update validation, or unsafe STL/STEP processing are in scope.

The add-in launches a native converter on user-selected files. Keep the
bundled engine pinned to a verified upstream release and report unexpected
binary or checksum changes immediately.
