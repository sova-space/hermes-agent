---
name: upgrade-hermes
description: Workflow for upgrading the upstream Hermes Agent version in this repo. Use when bumping HERMES_REF in the Dockerfile to a new release tag.
disable-model-invocation: false
---

When the user runs /upgrade-hermes, guide them through this workflow:

1. **Check the current version**: Read the Dockerfile and show the current `HERMES_REF` value.

2. **Find the latest release**: Ask the user what version tag they want to upgrade to, or check the upstream repo at https://github.com/nousresearch/hermes for recent release tags.

3. **Update HERMES_REF**: Edit the `ARG HERMES_REF=` line in the Dockerfile to the new tag.

4. **Rebuild the image**:
   ```
   docker build -t hermes-agent .
   ```
   Note: the build installs Hermes and its npm dependencies, so it may take several minutes.

5. **Smoke test**: Run the new image and verify:
   ```
   docker run --rm -it -p 8080:8080 -e PORT=8080 -e ADMIN_PASSWORD=changeme -v hermes-data:/data hermes-agent
   ```
   Check:
   - Admin UI loads at http://localhost:8080
   - The Hermes gateway and dashboard start without errors (watch the log output)
   - The version shown in the UI matches the new tag

6. **Commit**: If the smoke test passes, commit the Dockerfile change on a branch named `update/v<new-version>` and open a PR.

If the build fails, check whether the Hermes install command in the Dockerfile needs updated extras (the `.[all,messaging,tts-premium,...]` list) — upstream may have added or removed optional packages.