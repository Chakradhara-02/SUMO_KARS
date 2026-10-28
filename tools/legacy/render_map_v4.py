from pathlib import Path
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from kars.city import build_city_network,CITY_POINTS,CITY_DISTRICTS
root=ET.parse(build_city_network()).getroot()
fig,ax=plt.subplots(figsize=(10,10),facecolor='#f0f3f0');ax.set_facecolor('#f0f3f0')
for d in CITY_DISTRICTS:
 ax.add_patch(plt.Rectangle((d['x']-75,d['y']-65),150,130,color=d['color'],alpha=.8,zorder=0))
 ax.text(d['x'],d['y'],d['name'].replace(' ','\n',1),ha='center',va='center',fontsize=7,color='#536c7c',weight='bold')
for junction in root.findall('junction'):
 points=[[float(v) for v in p.split(',')] for p in junction.get('shape','').split()]
 if len(points)>=3 and junction.get('type')!='internal':
  color='#df9958' if float(junction.get('z','0'))>1 else '#83949e'
  ax.add_patch(plt.Polygon([(p[0],p[1]) for p in points],color=color,zorder=1))
for edge in root.findall('edge'):
 eid=edge.get('id')
 if eid.startswith(':'):continue
 points=[[float(v) for v in p.split(',')] for p in edge.find('lane').get('shape').split()]
 raised=any(len(p)>2 and p[2]>1 for p in points)
 color='#df9958' if raised else '#15998d' if 'under_' in eid else '#29485e' if eid.startswith('r') else '#83949e'
 ax.plot([p[0] for p in points],[p[1] for p in points],color=color,linewidth=2 if eid.startswith('r') else 1.5,zorder=2 if raised else 1)
for i,p in enumerate(CITY_POINTS):
 ax.scatter(p['x'],p['y'],s=65,color='#ffffff',edgecolors='#254258',zorder=5)
 ax.text(p['x']+15,p['y']+19,p['name'],fontsize=7,color='#18384c',bbox={'facecolor':'white','alpha':.9,'edgecolor':'none','pad':2},zorder=6)
ax.set_xlim(-330,1190);ax.set_ylim(-330,1190);ax.set_aspect('equal');ax.axis('off')
ax.set_title('STRAIGHT CITY\nAvenues · central underpass · outer expressway',loc='left',fontsize=17,fontweight='bold',color='#203e53',pad=22)
ax.legend(handles=[Line2D([0],[0],color=c,lw=3,label=l) for c,l in [('#29485e','Outer expressway'),('#83949e','City avenues'),('#df9958','Raised corridor'),('#15998d','Underpass')]],loc='lower center',bbox_to_anchor=(.5,-.04),ncol=2,frameon=False,fontsize=9)
fig.savefig('docs/Straight_City_Overview.png',dpi=140,bbox_inches='tight');plt.close(fig)
