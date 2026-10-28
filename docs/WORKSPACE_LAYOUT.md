# SUMO_KARS final version

This is the single consolidated project folder. Double-click Start_City.cmd in the project root to launch the city dashboard.

- kars/: simulation, routing, planning and local server.
- simulation_ui/: browser code and runtime car assets.
- sumo/: networks, routes and configuration.
- knowledge_graph/: ontology and queries.
- tests/: maintained Python and JavaScript tests.
- docs/: guides, research references and this folder map.
- outputs/: saved runs and historical verification evidence.
- tools/package_for_team.py: creates dist/SUMO_KARS_Team_Project.zip.
- tools/legacy/: preserved historical patch and verification scripts.
- asset_sources/: original car geometry and conversion tools.
- artifacts/: audit, logs, screenshots and organization records.
- archive/: preserved scratch material and any unique ZIP contents.

The V10 release contained 142 files, all byte-identical to the active project; the redundant release copy was removed. The original SUMO_KARS.zip was checked entry by entry: matching files were removed with the ZIP, and any unique or differing entries were retained in archive/zip_only/. Runtime files with distinct paths were preserved because their names and locations can be required by the application.

Run commands from this folder:

```powershell
python launch_city.py --check
python -m pytest -q
node --test tests/*.test.mjs
python tools/package_for_team.py
```
