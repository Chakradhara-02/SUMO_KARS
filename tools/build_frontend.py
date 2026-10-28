"""Build the UI and its separately bundled background planner."""
from pathlib import Path
import shutil,subprocess
root=Path(__file__).resolve().parents[1]
npx=shutil.which('npx.cmd') or shutil.which('npx')
if not npx:raise SystemExit('Node.js/npx is needed to build browser assets.')
for source,target in [('simulation_ui/reachability.worker.js','simulation_ui/reachability.worker.bundle.js'),('simulation_ui/app.js','simulation_ui/app.bundle.js')]:
    loaders=['--loader:.bundle.js=text'] if source.endswith('/app.js') else []
    subprocess.run([npx,'--yes','esbuild@0.28.2',source,'--bundle','--format=iife','--minify','--outfile='+target,*loaders],cwd=root,check=True)
