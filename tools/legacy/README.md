# Historical development scripts

This folder preserves one-off scripts previously mixed with the application entry points: UI rewrites, old update installers, release builders, browser checks and native verification utilities.

These are historical records rather than the maintained launch or test workflow. Some contain absolute paths to the original developer's computer, expect old output fixtures, or assume they live beside `main.py`. Their contents have been preserved, so moving them does not make those assumptions portable. Review and adapt a script before running it; patch scripts can overwrite application files.

Use `../../launch_city.py` to launch the application and the maintained tests under `../../tests/` to verify it. Run those commands with the application folder as the working directory. Use the workspace-level `tools/package_for_team.py` for team packaging.
