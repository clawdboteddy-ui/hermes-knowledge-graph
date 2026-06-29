#!/usr/bin/env python
"""Generate a self-contained neon 3D WebGL visual from a Graphify graph.json."""
import json, sys
from collections import Counter
from pathlib import Path


def build(graph_json_path, out_path=None, title=None):
    src = Path(graph_json_path)
    data = json.loads(src.read_text(encoding="utf-8"))
    raw_nodes = data.get("nodes", [])
    raw_links = data.get("links", [])
    deg = Counter()
    for l in raw_links:
        deg[l.get("source")] += 1
        deg[l.get("target")] += 1
    nodes = [{
        "id": n.get("id"),
        "label": n.get("label", n.get("id")),
        "community": n.get("community", 0),
        "type": n.get("file_type", "node"),
        "deg": deg.get(n.get("id"), 0),
    } for n in raw_nodes]
    links = [{"source": l.get("source"), "target": l.get("target"),
              "relation": l.get("relation", "")} for l in raw_links]
    payload = json.dumps({"nodes": nodes, "links": links}, ensure_ascii=False)
    name = title or src.parent.parent.name
    out = Path(out_path) if out_path else src.with_name("graph-3d.html")
    out.write_text(HTML.replace("__TITLE__", name).replace("__DATA__", payload), encoding="utf-8")
    return str(out)


HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__ — 3D Knowledge Graph</title>
<style>
  html,body{margin:0;height:100%;background:#03030a;overflow:hidden;font-family:-apple-system,Segoe UI,Roboto,sans-serif;}
  #graph{width:100vw;height:100vh;}
  #hud{position:fixed;top:16px;left:18px;z-index:10;color:#eef0ff;pointer-events:none;text-shadow:0 1px 10px #000;}
  #hud h1{margin:0;font-size:18px;font-weight:600;letter-spacing:.4px;}
  #hud .stat{margin-top:4px;font-size:12px;opacity:.6;}
  #panel{position:fixed;top:16px;right:18px;z-index:10;display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;max-width:60vw;}
  #panel button{pointer-events:auto;cursor:pointer;border:1px solid #2b2d48;background:rgba(18,20,40,.7);color:#d8d9ee;font-size:12px;padding:7px 11px;border-radius:8px;backdrop-filter:blur(6px);}
  #panel button:hover{background:rgba(46,50,90,.92);border-color:#5a5fa0;}
  #panel button.on{background:rgba(90,70,200,.55);border-color:#8a7bff;color:#fff;}
  #tip{position:fixed;bottom:14px;left:18px;z-index:10;color:#7c80a8;font-size:11px;pointer-events:none;}
  #loading{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;color:#aab;font-size:14px;z-index:5;}
</style></head>
<body>
<div id="hud"><h1>__TITLE__</h1><div class="stat" id="stat"></div></div>
<div id="panel">
  <button id="labels">Hub labels</button>
  <button id="particles" class="on">Light flow</button>
  <button id="spin">Auto-rotate</button>
  <button id="reset">Reset view</button>
</div>
<div id="tip">drag to orbit · scroll to zoom · hover a node for its name · click a node to fly to it</div>
<div id="loading">summoning the graph…</div>
<div id="graph"></div>
<script src="https://unpkg.com/three@0.158.0/build/three.min.js"></script>
<script
src="https://unpkg.com/3d-force-graph@1.73.4/dist/3d-force-graph.min.js"></script>
<script src="https://unpkg.com/three-spritetext@1.8.2/dist/three-spritetext.min.js"></script>
<script>
(function(){
  if(typeof THREE==='undefined'||typeof ForceGraph3D==='undefined'){
    document.getElementById('loading').textContent='Could not load the 3D libraries — check your internet connection.';return;}
  const DATA=__DATA__;
  document.getElementById('loading').remove();
  document.getElementById('stat').textContent=DATA.nodes.length+' nodes · '+DATA.links.length+' connections';
  const maxDeg=Math.max(1,...DATA.nodes.map(n=>n.deg));
  const HUB=Math.max(5,Math.ceil(maxDeg*0.6));
  const communities=[...new Set(DATA.nodes.map(n=>n.community))];
  const byId={};DATA.nodes.forEach(n=>byId[n.id]=n);
  const colorFor=(c)=>{const h=(communities.indexOf(c)*360/Math.max(1,communities.length))%360;return new THREE.Color('hsl('+Math.round(h)+', 95%, 62%)');};
  const GLOW=(function(){const c=document.createElement('canvas');c.width=c.height=128;const g=c.getContext('2d');
    const grd=g.createRadialGradient(64,64,0,64,64,64);
    grd.addColorStop(0,'rgba(255,255,255,1)');grd.addColorStop(0.25,'rgba(255,255,255,0.55)');grd.addColorStop(1,'rgba(255,255,255,0)');
    g.fillStyle=grd;g.fillRect(0,0,128,128);return new THREE.CanvasTexture(c);})();
  function geoFor(node){const r=2.4+node.deg*1.1;const pick=communities.indexOf(node.community)%3;
    if(node.deg>=HUB)return new THREE.IcosahedronGeometry(r,0);
    if(pick===1)return new THREE.TetrahedronGeometry(r,0);
    return new THREE.OctahedronGeometry(r,0);}
  function nodeObject(node,withLabel){
    const col=colorFor(node.community);const r=2.4+node.deg*1.1;const group=new THREE.Group();
    const glow=new THREE.Sprite(new THREE.SpriteMaterial({map:GLOW,color:col,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0.85}));
    const gs=r*6;glow.scale.set(gs,gs,1);group.add(glow);
    const mesh=new THREE.Mesh(geoFor(node),new THREE.MeshBasicMaterial({color:col}));
    mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry),new THREE.LineBasicMaterial({color:0xffffff,transparent:true,opacity:0.4})));
    group.add(mesh);
    if(withLabel&&node.deg>=HUB){const s=new SpriteText(node.label.replace(/\.md$/,''));s.color='#ffffff';s.textHeight=5;s.backgroundColor='rgba(3,3,10,0.5)';s.padding=1.5;s.position.y=7+node.deg;group.add(s);}
    return group;}
  const Graph=ForceGraph3D()(document.getElementById('graph'))
    .graphData(DATA).backgroundColor('#03030a')
    .nodeLabel(n=>'<div style="background:rgba(8,10,22,.94);color:#fff;padding:6px 9px;border-radius:6px;font-size:12px;max-width:300px">'+n.label+'<br><span style="opacity:.6">'+n.type+' · '+n.deg+' links · community '+n.community+'</span></div>')
    .nodeThreeObject(n=>nodeObject(n,false))
    .linkColor(l=>colorFor((byId[(l.source.id||l.source)]||{}).community).getStyle())
    .linkOpacity(0.45).linkWidth(0.5)
    .linkDirectionalParticles(2).linkDirectionalParticleWidth(1.6).linkDirectionalParticleSpeed(0.006)
    .onNodeClick(node=>{const dist=120;const len=Math.hypot(node.x,node.y,node.z)||1;const r=1+dist/len;
      Graph.cameraPosition({x:node.x*r,y:node.y*r,z:node.z*r},node,1400);});
  Graph.d3Force('charge').strength(-160);
  let labelsOn=false;const lb=document.getElementById('labels');
  lb.onclick=()=>{labelsOn=!labelsOn;lb.classList.toggle('on',labelsOn);Graph.nodeThreeObject(n=>nodeObject(n,labelsOn));};
  let pOn=true;const pb=document.getElementById('particles');
  pb.onclick=()=>{pOn=!pOn;pb.classList.toggle('on',pOn);Graph.linkDirectionalParticles(pOn?2:0);};
  let spin=false,t=0;const sb=document.getElementById('spin');
  sb.onclick=()=>{spin=!spin;sb.classList.toggle('on',spin);};
  (function rot(){if(spin){t+=0.0015;const d=360;Graph.cameraPosition({x:d*Math.sin(t),z:d*Math.cos(t)});}requestAnimationFrame(rot);})();
  document.getElementById('reset').onclick=()=>Graph.zoomToFit(900,50);
  setTimeout(()=>Graph.zoomToFit(1400,60),900);
window.addEventListener('resize',()=>{Graph.width(window.innerWidth).height(window.innerHeight);});
})();
</script></body></html>
"""


if __name__ == "__main__":
    argv = sys.argv[1:]; title=None; pos=[]; i=0
    while i < len(argv):
        if argv[i]=="--title" and i+1<len(argv): title=argv[i+1]; i+=2; continue
        pos.append(argv[i]); i+=1
    if not pos: print("usage: python graphify_3d.py <graph.json> [out.html] [--title NAME]"); sys.exit(1)
    print("wrote", build(pos[0], pos[1] if len(pos)>1 else None, title))
