# Runbook: a release

Versions are derived from tags; nobody types one. The tag push is the release.

## Candidate on `develop` (optional)

1. `develop` is green and deployed to Testing.
2. `git tag -a v<X.Y.Z>-rc.<N> -m "candidate <X.Y.Z>-rc.<N>" <commit>` and `git push origin v<X.Y.Z>-rc.<N>`.
3. Testing now reports that version. Record acceptance against it.

## Release on `main`

1. Open a pull request from `develop` to `main`; the checks run on its head. Merge it. Nothing deploys.
2. The release lane opens or updates the release pull request: `package.json` bump, changelog section, proposed version. To name a specific version, put `Release-As: <X.Y.Z>` in the footer of a commit on `develop` before the merge.
3. Review the release pull request. Merge it. Nothing deploys.
4. Write the deploy-log row: environment, version, commit, your authorization.
5. `git fetch origin main && git tag -a v<X.Y.Z> -m "release <X.Y.Z>" origin/main && git push origin v<X.Y.Z>`.
6. The production lane runs: it refuses if the tag does not name the derived version, deploys, verifies the running version, publishes the GitHub release from the changelog section.
7. Complete the deploy-log row with the verification.

## Rollback

Redeploy the previous tag's image: on the host, start the previous release from its recorded values. Never rebuild. Record the rollback in the deploy log with both versions.
