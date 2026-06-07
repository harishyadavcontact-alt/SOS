"""Generate a self-contained interactive SoS visualizer faithful to GENESIS.md."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .index import DEFAULT_EXAMPLES_DIR, IndexedObject, build_index
except ImportError:  # Allows `python src/view_interactive_war_room.py` from the repo root.
    from index import DEFAULT_EXAMPLES_DIR, IndexedObject, build_index  # type: ignore[no-redef]


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[1] / "output" / "interactive_war_room.html"

TOP_TABS = [
    "State of the Art",
    "State of Affairs",
    "State of Functions",
    "State of Operations",
    "Graph",
]

TYPE_COLORS = {
    "SourceOfVolatility": "#22d3ee",
    "Domain": "#67e8f9",
    "Craft": "#94a3b8",
    "Affair": "#ef4444",
    "Interest": "#a855f7",
    "Resource": "#38bdf8",
    "Mission": "#f6c453",
    "WarGame": "#f59e0b",
    "DecisionLog": "#fb923c",
    "Protocol": "#f97316",
    "CodeOfConduct": "#c084fc",
    "RulesOfEngagement": "#fb7185",
    "Review": "#14b8a6",
    "ReviewAAR": "#14b8a6",
    "Operation": "#3b82f6",
    "OperationBuild": "#3b82f6",
    "Routine": "#22c55e",
    "Regimen": "#16a34a",
    "Agent": "#e2e8f0",
}

STATE_BY_TYPE = {
    "SourceOfVolatility": "State of the Art",
    "Domain": "State of the Art",
    "Craft": "State of the Art",
    "Signal": "State of the Art",
    "Affair": "State of Affairs",
    "Interest": "State of Affairs",
    "Resource": "State of Affairs",
    "Mission": "State of Affairs",
    "WarGame": "State of Functions",
    "DecisionLog": "State of Functions",
    "Review": "State of Functions",
    "ReviewAAR": "State of Functions",
    "Protocol": "State of Functions",
    "CodeOfConduct": "State of Functions",
    "RulesOfEngagement": "State of Functions",
    "Operation": "State of Operations",
    "OperationBuild": "State of Operations",
    "Routine": "State of Operations",
    "Regimen": "State of Operations",
}

DISPLAY_TYPES = set(STATE_BY_TYPE) | {"Agent"}

STATE_SECTIONS = {
    "State of the Art": [
        "Maya",
        "Skin in the Game",
        "Philosopher's Stone",
        "Sources of Volatility",
        "Domains",
        "Crafts",
        "Models",
        "Signals",
    ],
    "State of Affairs": [
        "Ends",
        "Ways",
        "Means",
        "Affairs",
        "Interests",
        "Resources",
        "Missions",
    ],
    "State of Functions": [
        "War Gaming",
        "Sensing",
        "Preparation",
        "Planning",
        "Execution",
        "Review",
        "Protocols",
        "Decision Logs",
    ],
    "State of Operations": [
        "Operations",
        "Routines",
        "Regimens",
        "Agenda",
        "Calendar",
    ],
}


def _name(item: IndexedObject) -> str:
    name = item.payload.get("name")
    return name if isinstance(name, str) else item.id


def _as_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _first_string(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _add_edge(edges: list[dict[str, str]], objects: dict[str, IndexedObject], source: str, target: str, label: str) -> None:
    if source in objects and target in objects:
        edge = {"source": source, "target": target, "label": label}
        if edge not in edges:
            edges.append(edge)


def _embedded_mission_id(payload: dict[str, Any]) -> str | None:
    decision_log = payload.get("decision_log_input")
    if not isinstance(decision_log, dict):
        return None
    war_game = decision_log.get("war_game_input")
    if not isinstance(war_game, dict):
        return None
    mission = war_game.get("mission")
    if not isinstance(mission, dict):
        return None
    mission_id = mission.get("id")
    return mission_id if isinstance(mission_id, str) else None


def _build_edges(objects: dict[str, IndexedObject]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for item in sorted(objects.values(), key=lambda value: value.id):
        payload = item.payload

        if item.type == "Domain":
            for source_id in _as_ids(payload.get("source_ids")):
                _add_edge(edges, objects, source_id, item.id, "contains")

        if item.type == "Craft":
            for domain_id in _as_ids(payload.get("domain_ids")):
                _add_edge(edges, objects, domain_id, item.id, "contains")

        if item.type == "CodeOfConduct":
            for craft_id in _as_ids(payload.get("craft_ids")):
                _add_edge(edges, objects, craft_id, item.id, "informs")

        if item.type == "RulesOfEngagement":
            for code_id in _as_ids(payload.get("code_of_conduct_id")):
                _add_edge(edges, objects, code_id, item.id, "governs")

        if item.type == "Protocol":
            for rule_id in _as_ids(payload.get("rules_of_engagement_id")):
                _add_edge(edges, objects, rule_id, item.id, "constrains")
            for code_id in _as_ids(payload.get("code_of_conduct_id")):
                _add_edge(edges, objects, code_id, item.id, "governs")

        if item.type in {"Affair", "Interest", "Mission"}:
            for owner_id in _as_ids(payload.get("owner_id")):
                _add_edge(edges, objects, owner_id, item.id, item.type.lower())

        if item.type == "Mission":
            for target in _as_ids(payload.get("affair_ids")):
                _add_edge(edges, objects, item.id, target, "aggregates")
            for target in _as_ids(payload.get("interest_ids")):
                _add_edge(edges, objects, item.id, target, "aggregates")
            for target in _as_ids(payload.get("resource_ids")):
                _add_edge(edges, objects, item.id, target, "allocates")

        if item.type == "Operation":
            for mission_id in _as_ids(payload.get("mission_id")):
                _add_edge(edges, objects, mission_id, item.id, "advances")
            for protocol_id in _as_ids(payload.get("protocol_ids")):
                _add_edge(edges, objects, item.id, protocol_id, "guided by")

        if item.type == "Regimen":
            for routine_id in _as_ids(payload.get("routine_ids")):
                _add_edge(edges, objects, item.id, routine_id, "contains")

        if item.type == "Routine":
            for affair_id in _as_ids(payload.get("supports_affair_ids")):
                _add_edge(edges, objects, item.id, affair_id, "supports")

        if item.type in {"Review", "ReviewAAR"}:
            mission_id = payload.get("mission_id")
            if not isinstance(mission_id, str):
                mission_id = _embedded_mission_id(payload)
            if isinstance(mission_id, str):
                _add_edge(edges, objects, item.id, mission_id, "updates")
            for protocol_id in _as_ids(payload.get("protocol_updates")):
                _add_edge(edges, objects, item.id, protocol_id, "updates")
            for decision_log_id in _as_ids(payload.get("decision_log_id")):
                _add_edge(edges, objects, item.id, decision_log_id, "reviews")

    return edges


def _node_payload(item: IndexedObject, index: int) -> dict[str, Any]:
    column = index % 5
    row = index // 5
    payload = item.payload
    return {
        "id": item.id,
        "type": item.type,
        "state": STATE_BY_TYPE.get(item.type, "System"),
        "name": _name(item),
        "status": payload.get("status"),
        "owner": payload.get("owner_id") or payload.get("owner"),
        "domains": payload.get("domain_ids"),
        "scope": payload.get("scope"),
        "front": payload.get("front"),
        "end": payload.get("end"),
        "priority": payload.get("priority_score") or payload.get("priority"),
        "payload": payload,
        "path": item.path.name,
        "color": TYPE_COLORS.get(item.type, "#cbd5e1"),
        "x": 130 + (column * 168),
        "y": 95 + (row * 105),
    }


def _card_models(nodes: list[dict[str, Any]]) -> list[str]:
    models: set[str] = set()
    for node in nodes:
        for value in _as_list(node["payload"].get("models")):
            if isinstance(value, str):
                models.add(value)
    return sorted(models)


def _calendar_items(nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for node in nodes:
        payload = node["payload"]
        for field in ("start_date", "target_date", "deadline", "review_date", "created_at"):
            value = payload.get(field)
            if isinstance(value, str):
                items.append(
                    {
                        "date": value[:10],
                        "label": node["name"],
                        "type": node["type"],
                        "field": field,
                        "id": node["id"],
                    }
                )
        cadence = _first_string(payload, "cadence", "review_cadence")
        if cadence:
            items.append({"date": cadence, "label": node["name"], "type": node["type"], "field": "cadence", "id": node["id"]})
    return sorted(items, key=lambda item: (item["date"], item["label"]))


def _agenda_items(nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
    agenda: list[dict[str, str]] = []
    for node in nodes:
        payload = node["payload"]
        if node["type"] in {"Operation", "OperationBuild", "Routine", "Regimen", "Review", "ReviewAAR"}:
            status = payload.get("status")
            if status in {"active", "planned", "draft", "recorded"}:
                agenda.append({"label": node["name"], "type": node["type"], "id": node["id"], "detail": str(status)})
        for field in ("next_actions", "follow_up_actions", "steps", "success_criteria"):
            for action in _as_list(payload.get(field))[:4]:
                if isinstance(action, str):
                    agenda.append({"label": action, "type": field, "id": node["id"], "detail": node["name"]})
    return agenda[:32]


def _top_level_mission(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    missions = [node for node in nodes if node["type"] == "Mission"]
    return next((node for node in missions if node["payload"].get("status") in {"active", "draft", "planned"}), missions[0] if missions else None)


def build_cockpit_data(examples_dir: Path = DEFAULT_EXAMPLES_DIR) -> dict[str, Any]:
    index = build_index(examples_dir)
    objects: dict[str, IndexedObject] = index["unique_objects"]
    sorted_objects = sorted(
        objects.values(),
        key=lambda value: (STATE_BY_TYPE.get(value.type, "Z"), value.type, value.id),
    )
    nodes = [
        _node_payload(item, idx)
        for idx, item in enumerate(sorted_objects)
        if item.type in DISPLAY_TYPES
    ]
    visible = {node["id"] for node in nodes}
    object_subset = {object_id: objects[object_id] for object_id in visible}
    counts = {key: len(value) for key, value in index["grouped"].items()}
    return {
        "topTabs": TOP_TABS,
        "nodes": nodes,
        "edges": _build_edges(object_subset),
        "counts": counts,
        "mission": _top_level_mission(nodes),
        "models": _card_models(nodes),
        "calendar": _calendar_items(nodes),
        "agenda": _agenda_items(nodes),
        "stats": {
            "totalObjects": len(objects),
            "missingReferences": len(index["missing_references"]),
            "globalDuplicates": len(index["global_duplicates"]),
            "scenarioLocalDuplicates": len(index["scenario_local_duplicates"]),
        },
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>System of Systems Visualizer</title>
  <style>
    :root {
      --bg:#05090d; --panel:#0b1218; --panel2:#111b23; --panel3:#16262f;
      --line:#243844; --line2:#355160; --text:#d9e7ea; --muted:#89a0a8;
      --cyan:#22d3ee; --gold:#f6c453; --red:#ef4444; --purple:#a855f7;
      --blue:#3b82f6; --green:#22c55e; --teal:#14b8a6; --orange:#f59e0b;
    }
    *{box-sizing:border-box}
    body{margin:0;height:100vh;overflow:hidden;background:var(--bg);color:var(--text);font-family:Arial,Helvetica,sans-serif}
    header{height:86px;display:grid;grid-template-columns:1fr auto;gap:18px;align-items:center;padding:15px 20px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#0d171f,#070d12)}
    h1,h2,h3,h4,p{margin:0} h1{font-size:23px;letter-spacing:0}
    .motto{margin-top:5px;color:var(--muted);font-size:12px}
    .mission{margin-top:8px;color:var(--gold);font-size:13px;display:flex;gap:12px;flex-wrap:wrap}
    .mission span{color:var(--muted)}
    .tabs{display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap}
    .tab{border:1px solid var(--line);background:var(--panel);color:var(--text);border-radius:7px;padding:8px 10px;cursor:pointer;font-size:13px}
    .tab.active{border-color:var(--cyan);color:var(--cyan);background:#0b2328}
    .layout{height:calc(100vh - 86px);display:grid;grid-template-columns:294px minmax(430px,1fr) 358px}
    .sidebar,.workspace,.inspector{background:var(--panel);min-height:0}
    .sidebar{border-right:1px solid var(--line);padding:14px;overflow:auto}
    .workspace{background:#071016;padding:16px;overflow:auto}
    .inspector{border-left:1px solid var(--line);padding:14px;overflow:auto}
    .tree h3,.inspector h3{font-size:13px;color:var(--muted);text-transform:uppercase;margin-bottom:10px}
    details{margin-left:10px} summary{cursor:pointer;color:#c5d6db;padding:4px 0}
    .tree button{display:block;width:100%;border:0;border-radius:6px;background:transparent;color:var(--muted);text-align:left;padding:5px 7px;cursor:pointer}
    .tree button:hover,.tree button.active{background:var(--panel2);color:var(--cyan)}
    .state-title{border:1px solid var(--line);background:linear-gradient(135deg,#10212a,#0a141b);border-radius:12px;padding:15px;margin-bottom:14px}
    .state-title h2{font-size:22px;color:var(--cyan)} .state-title p{margin-top:6px;color:var(--muted)}
    .section{margin-bottom:22px}.section h3{font-size:13px;color:var(--muted);text-transform:uppercase;margin:0 0 9px;letter-spacing:0}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(218px,1fr));gap:10px}
    .card{border:1px solid var(--line);border-left:3px solid var(--line2);border-radius:9px;background:var(--panel2);padding:11px;min-height:104px;cursor:pointer}
    .card:hover{border-color:var(--cyan)} .card h4{font-size:15px;margin-bottom:6px}.card p{font-size:12px;color:var(--muted);line-height:1.35;overflow-wrap:anywhere}
    .card.static{cursor:default}.card.static:hover{border-color:var(--line)}
    .Affair{border-left-color:var(--red)}.Interest{border-left-color:var(--purple)}.Resource{border-left-color:var(--blue)}
    .Mission{border-left-color:var(--gold)}.WarGame,.DecisionLog{border-left-color:var(--orange)}
    .Operation,.OperationBuild{border-left-color:var(--blue)}.Routine,.Regimen{border-left-color:var(--green)}
    .Review,.ReviewAAR{border-left-color:var(--teal)}.Protocol,.CodeOfConduct,.RulesOfEngagement{border-left-color:#c084fc}
    .SourceOfVolatility,.Domain,.Craft{border-left-color:var(--cyan)}
    .toolbar{display:flex;gap:8px;margin-bottom:10px}.toolbar input,.toolbar select{background:#061015;border:1px solid var(--line);color:var(--text);border-radius:7px;padding:9px 10px}
    .toolbar input{flex:1} svg{width:100%;height:650px;border:1px solid var(--line);border-radius:12px;background:radial-gradient(circle at center,#11242e,#060b10 72%)}
    .edge{stroke:#425a66;stroke-width:1.2;marker-end:url(#arrow)}.edge-label{fill:#9bb0b7;font-size:10px;pointer-events:none}.node circle{stroke:#e2e8f0;stroke-width:1;cursor:grab}.node text{fill:var(--text);font-size:11px;pointer-events:none}.node.selected circle{stroke:var(--cyan);stroke-width:3}
    table{width:100%;border-collapse:collapse}th,td{border-bottom:1px solid var(--line);padding:8px;text-align:left;font-size:12px}th{color:var(--cyan);background:#0a151b}
    .kv{display:grid;gap:7px;margin:12px 0}.kv div{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid #1a2b35;padding-bottom:5px}.kv span{color:var(--muted)}.kv strong{text-align:right}
    .inspector-tabs{display:flex;gap:5px;flex-wrap:wrap;margin:12px 0}.inspector-tabs button{border:1px solid var(--line);background:var(--panel2);color:var(--text);border-radius:6px;padding:6px 8px;cursor:pointer}.inspector-tabs button.active{color:var(--cyan);border-color:var(--cyan)}
    pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#050b0f;border:1px solid var(--line);border-radius:10px;padding:12px;color:#cde9ef;max-height:460px;overflow:auto}
    .empty{color:var(--muted);border:1px dashed var(--line);border-radius:9px;padding:12px}
    @media(max-width:1100px){body{overflow:auto}.layout{height:auto;grid-template-columns:1fr}.sidebar,.inspector{border:0;border-bottom:1px solid var(--line);max-height:360px}header{height:auto;grid-template-columns:1fr}}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>SYSTEM OF SYSTEMS</h1>
      <p class="motto">Protected Base. Aggressive Frontier. No Dead Middle.</p>
      <p class="mission" id="mission-strip"></p>
    </div>
    <nav class="tabs" id="tabs"></nav>
  </header>
  <div class="layout">
    <aside class="sidebar">
      <div class="tree">
        <h3>Genesis Tree</h3>
        <div id="tree"></div>
      </div>
    </aside>
    <main class="workspace" id="workspace"></main>
    <aside class="inspector" id="inspector"></aside>
  </div>
  <script id="sos-data" type="application/json">__DATA__</script>
  <script>
    const DATA=JSON.parse(document.getElementById('sos-data').textContent);
    const byId=new Map(DATA.nodes.map(n=>[n.id,n]));
    let activeTab=DATA.topTabs[0];
    let activeSection=null;
    let selected=DATA.mission?.id || DATA.nodes[0]?.id || null;
    const groups={
      'Sources of Volatility':['SourceOfVolatility'],'Domains':['Domain'],'Crafts':['Craft'],'Signals':['Signal'],
      'Affairs':['Affair'],'Interests':['Interest'],'Resources':['Resource'],'Missions':['Mission'],
      'War Gaming':['WarGame'],'Review':['Review','ReviewAAR'],'Protocols':['Protocol'],
      'Decision Logs':['DecisionLog'],'Operations':['Operation','OperationBuild'],'Routines':['Routine'],'Regimens':['Regimen']
    };
    const fieldSets={
      Affair:['status','stake','fragility_score','ruin_risk','deadline','cadence','front','scope','end','priority_score'],
      Interest:['status','upside','downside','convexity_score','optionality_score','front','scope','end','priority_score'],
      Resource:['resource_type','quantity','unit','criticality_score','status'],
      Mission:['status','current_state','target_trajectory','death_spiral_risk','virtuous_spiral_score','affair_ids','interest_ids','resource_ids']
    };
    const esc=v=>String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    const arg=v=>JSON.stringify(String(v??''));
    const nodesOf=types=>DATA.nodes.filter(n=>types.includes(n.type)).sort((a,b)=>a.name.localeCompare(b.name));
    const linked=n=>Object.entries(n.payload).flatMap(([k,v])=>!k.endsWith('_id')&&!k.endsWith('_ids')?[]:Array.isArray(v)?v.filter(x=>typeof x==='string'):(typeof v==='string'?[v]:[]));
    function setTab(tab,section=null){activeTab=tab;activeSection=section;renderTabs();renderWorkspace();if(tab==='Graph')setTimeout(renderGraph,0);setTimeout(jumpToSection,0)}
    function selectNode(id){selected=id;renderInspector();document.querySelectorAll('[data-node-id]').forEach(el=>el.classList.toggle('active',el.dataset.nodeId===id));document.querySelectorAll('.node').forEach(el=>el.classList.toggle('selected',el.dataset.id===id))}
    function renderTabs(){document.getElementById('tabs').innerHTML=DATA.topTabs.map(t=>`<button class="tab ${t===activeTab?'active':''}" onclick="setTab(${arg(t)})">${esc(t)}</button>`).join('')}
    function branch(name,tab,children=''){return `<details open><summary onclick="setTab(${arg(tab)},${arg(name)})">${esc(name)}</summary>${children}</details>`}
    function objectButtons(name){return nodesOf(groups[name]||[]).map(n=>`<button data-node-id="${esc(n.id)}" onclick="selectNode(${arg(n.id)})">${esc(n.name)} <span>${esc(n.type)}</span></button>`).join('')}
    function leaf(name,tab){return `<button onclick="setTab(${arg(tab)},${arg(name)})">${esc(name)}</button>`}
    function groupBranch(name,tab){return branch(name,tab,objectButtons(name)||'<button>none detected</button>')}
    function renderTree(){
      const art=['Maya','Skin in the Game',"Philosopher's Stone"].map(x=>leaf(x,'State of the Art')).join('')+['Sources of Volatility','Domains','Crafts','Models','Signals'].map(x=>groupBranch(x,'State of the Art')).join('');
      const ends=branch('Ends','State of Affairs',['Hedge','Edge','Abort'].map(x=>leaf(x,'State of Affairs')).join(''));
      const ways=branch('Ways','State of Affairs',['Floor','Micro','Dynamic Simple Plan','Barbell','Probe','Review','Exit'].map(x=>leaf(x,'State of Affairs')).join(''));
      const means=branch('Means','State of Affairs',['Resources','Protocols','Operations','Routines','Regimens'].map(x=>groupBranch(x,'State of Affairs')).join(''));
      const affairs=ends+ways+means+['Affairs','Interests','Resources','Missions'].map(x=>groupBranch(x,'State of Affairs')).join('');
      const functions=['War Gaming','Sensing','Preparation','Planning','Execution','Review','Protocols','Decision Logs'].map(x=>groupBranch(x,'State of Functions')).join('');
      const operations=['Operations','Routines','Regimens'].map(x=>groupBranch(x,'State of Operations')).join('')+['Agenda','Calendar'].map(x=>leaf(x,'State of Operations')).join('');
      document.getElementById('tree').innerHTML=branch('System of Systems','State of the Art',branch('Intelligence','State of the Art',branch('State of the Art','State of the Art',art))+branch('Directorial','State of Affairs',branch('State of Affairs','State of Affairs',affairs))+branch('Executive','State of Functions',branch('State of Functions','State of Functions',functions)+branch('State of Operations','State of Operations',operations)));
    }
    function staticCard(title,body){return `<article class="card static"><h4>${esc(title)}</h4><p>${esc(body)}</p></article>`}
    function nodeCard(n,fields=null){const keys=fields||fieldSets[n.type]||['status','scope','front','end','priority_score','owner_id'];const body=keys.map(k=>n.payload[k]===undefined||n.payload[k]===null?'':`${k}: ${Array.isArray(n.payload[k])?n.payload[k].join(', '):n.payload[k]}`).filter(Boolean).join(' / ');return `<article class="card ${esc(n.type)}" onclick="selectNode(${arg(n.id)})"><h4>${esc(n.name)}</h4><p>${esc(n.type)} / ${esc(n.status||'unstatused')}</p><p>${esc(body||n.id)}</p></article>`}
    function objectSection(name,types,fields=null){const cards=nodesOf(types).map(n=>nodeCard(n,fields)).join('');return `<section class="section" data-section="${esc(name)}"><h3>${esc(name)}</h3><div class="grid">${cards||'<div class="empty">none detected</div>'}</div></section>`}
    function staticSection(name,cards){return `<section class="section" data-section="${esc(name)}"><h3>${esc(name)}</h3><div class="grid">${cards.join('')}</div></section>`}
    function renderWorkspace(){if(activeTab==='Graph')return renderGraphPanel();if(activeTab==='State of the Art')return renderArt();if(activeTab==='State of Affairs')return renderAffairs();if(activeTab==='State of Functions')return renderFunctions();return renderOperations()}
    function title(state,purpose){return `<div class="state-title"><h2>${esc(state)}</h2><p>${esc(purpose)}</p></div>`}
    function renderArt(){
      const models=DATA.models.map(m=>staticCard(m,'Model used for judgment, not stored as a new entity.'));
      document.getElementById('workspace').innerHTML=title('State of the Art','See reality, doctrine, and best-known truth.')+
        staticSection('Maya',[staticCard('Volatility','Change and nonlinear movement.'),staticCard('Opacity','What cannot be fully seen.'),staticCard('Uncertainty','Unknown outcomes and incomplete evidence.'),staticCard('Complexity','Interdependent behavior across scales.')])+
        staticSection('Skin in the Game',[staticCard('Risk','Downside borne by the actor.'),staticCard('Stakes','What matters if the action fails.'),staticCard('Exposure','What is open to harm or selection.'),staticCard('Consequence-bearing','The decision-maker pays for error.')])+
        staticSection("Philosopher's Stone",['Convexity','Optionality','Asymmetry','Ergodicity','Jensen','Kelly','Barbell'].map(x=>staticCard(x,'Judgment model from GENESIS.md.')))+
        objectSection('Sources of Volatility',['SourceOfVolatility'],['description','force_type','volatility_profile'])+
        objectSection('Domains',['Domain'],['source_ids','constraints','parent_domain_id'])+
        objectSection('Crafts',['Craft'],['domain_ids','source_ids','principles','maxims','models','status'])+
        staticSection('Models',models.length?models:[staticCard('none detected','No model list found in example payloads.')])+
        objectSection('Signals',['Signal']);
    }
    function renderAffairs(){
      document.getElementById('workspace').innerHTML=title('State of Affairs','Judge reality: ends, ways, means, and what matters now.')+
        staticSection('Ends',[staticCard('Hedge','Protect downside.'),staticCard('Edge','Create upside.'),staticCard('Abort','Exit unfavorable exposure.')])+
        staticSection('Ways',['Floor','Micro','Dynamic Simple Plan','Barbell','Probe','Review','Exit'].map(x=>staticCard(x,'Doctrine way; not a new ontology entity.')))+
        objectSection('Means',['Resource','Protocol','Operation','OperationBuild','Routine','Regimen'])+
        objectSection('Affairs',['Affair'],fieldSets.Affair)+objectSection('Interests',['Interest'],fieldSets.Interest)+
        objectSection('Resources',['Resource'],fieldSets.Resource)+objectSection('Missions',['Mission'],fieldSets.Mission);
    }
    function renderFunctions(){
      document.getElementById('workspace').innerHTML=title('State of Functions','See capabilities that judge, prepare, plan, execute, and review.')+
        staticSection('War Gaming',['Ergodicity Gate','Convexity Gate','Jensen Gate','Kelly Gate','Abort Gate'].map(x=>staticCard(x,'War Gaming gate.')).concat(nodesOf(['WarGame']).map(n=>nodeCard(n))))+
        objectSection('Sensing',['Signal'])+
        staticSection('Preparation',[staticCard('Preparation','Build readiness, reserves, backups, and skills.')])+
        staticSection('Planning',[staticCard('Planning','Sequence roadmap, blueprint, and action order.')])+
        staticSection('Execution',[staticCard('Execution','Spend capability through operations.')])+
        objectSection('Review',['Review','ReviewAAR'])+objectSection('Protocols',['Protocol'])+objectSection('Decision Logs',['DecisionLog']);
    }
    function renderOperations(){
      const agenda=DATA.agenda.map(i=>`<article class="card" onclick="selectNode(${arg(i.id)})"><h4>${esc(i.label)}</h4><p>${esc(i.type)} / ${esc(i.detail)}</p></article>`).join('');
      const calendar=DATA.calendar.map(i=>`<tr onclick="selectNode(${arg(i.id)})"><td>${esc(i.date)}</td><td>${esc(i.label)}</td><td>${esc(i.type)}</td><td>${esc(i.field)}</td></tr>`).join('');
      document.getElementById('workspace').innerHTML=title('State of Operations','See what is being executed: operations, routines, regimens, agenda, and calendar.')+
        objectSection('Operations',['Operation','OperationBuild'])+objectSection('Routines',['Routine'])+objectSection('Regimens',['Regimen'])+
        `<section class="section" data-section="Agenda"><h3>Agenda</h3><div class="grid">${agenda||'<div class="empty">none detected</div>'}</div></section>`+
        `<section class="section" data-section="Calendar"><h3>Calendar</h3><table><thead><tr><th>Date / Cadence</th><th>Item</th><th>Type</th><th>Field</th></tr></thead><tbody>${calendar}</tbody></table></section>`;
    }
    function renderGraphPanel(){document.getElementById('workspace').innerHTML=`${title('Graph','Inspect ontology relationships without adding a doctrine layer.')}<div class="toolbar"><input id="search" placeholder="Search graph"><select id="graph-filter">${['All','State of the Art','State of Affairs','State of Functions','State of Operations','Mission Focus'].map(x=>`<option>${x}</option>`).join('')}</select></div><svg id="graph" viewBox="0 0 980 660"></svg>`;document.getElementById('search').addEventListener('input',renderGraph);document.getElementById('graph-filter').addEventListener('change',renderGraph);renderGraph()}
    function graphNodes(){const q=(document.getElementById('search')?.value||'').toLowerCase();const f=document.getElementById('graph-filter')?.value||'All';const mission=DATA.mission?.id;const missionIds=new Set(DATA.edges.filter(e=>e.source===mission||e.target===mission).flatMap(e=>[e.source,e.target]).concat(mission||[]));return DATA.nodes.filter(n=>(!q||(n.id+n.name+n.type).toLowerCase().includes(q))&&(f==='All'||n.state===f||(f==='Mission Focus'&&missionIds.has(n.id))))}
    function renderGraph(){const svg=document.getElementById('graph');if(!svg)return;const nodes=graphNodes();const visible=new Set(nodes.map(n=>n.id));const edges=DATA.edges.filter(e=>visible.has(e.source)&&visible.has(e.target));svg.innerHTML='<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#425a66"></path></marker></defs>';for(const e of edges){const s=byId.get(e.source),t=byId.get(e.target);if(!s||!t)continue;svg.insertAdjacentHTML('beforeend',`<line class="edge" x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}"></line><text class="edge-label" x="${(s.x+t.x)/2}" y="${(s.y+t.y)/2}">${esc(e.label)}</text>`)}for(const n of nodes){svg.insertAdjacentHTML('beforeend',`<g class="node ${n.id===selected?'selected':''}" data-id="${esc(n.id)}" transform="translate(${n.x},${n.y})"><circle r="18" fill="${esc(n.color)}"></circle><text x="24" y="4">${esc(n.name)}</text></g>`)}wireDrag(svg)}
    function wireDrag(svg){let drag=null;svg.querySelectorAll('.node').forEach(g=>{g.onclick=()=>selectNode(g.dataset.id);g.onmousedown=ev=>{drag=g.dataset.id;ev.preventDefault()}});svg.onmouseup=()=>drag=null;svg.onmouseleave=()=>drag=null;svg.onmousemove=ev=>{if(!drag)return;const pt=svg.createSVGPoint();pt.x=ev.clientX;pt.y=ev.clientY;const loc=pt.matrixTransform(svg.getScreenCTM().inverse());const n=byId.get(drag);n.x=loc.x;n.y=loc.y;renderGraph()}}
    function renderInspector(tab='Overview'){
      const n=byId.get(selected);if(!n){document.getElementById('inspector').innerHTML='<p class="empty">Select an object.</p>';return}
      const tabs=['Overview','Relations','Doctrine','War Game','Raw JSON'];
      const overview=[['name',n.name],['type',n.type],['status',n.status],['owner',n.owner],['domains',Array.isArray(n.domains)?n.domains.join(', '):n.domains],['scope',n.scope],['front',n.front],['end',n.end],['priority',n.priority],['stake',n.payload.stake],['upside',n.payload.upside],['downside',n.payload.downside],['current_state',n.payload.current_state],['target_trajectory',n.payload.target_trajectory],['linked ids',linked(n).join(', ')]];
      document.getElementById('inspector').innerHTML=`<h3>Inspector</h3><h2>${esc(n.name)}</h2><p class="motto">${esc(n.id)}</p><div class="kv">${overview.filter(([_,v])=>v!==undefined&&v!==null&&v!=='').map(([k,v])=>`<div><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('')}</div><div class="inspector-tabs">${tabs.map(t=>`<button class="${t===tab?'active':''}" onclick="renderInspector(${arg(t)})">${esc(t)}</button>`).join('')}</div>${inspectorBody(n,tab)}`;
    }
    function inspectorBody(n,tab){if(tab==='Raw JSON')return `<details><summary>Open raw JSON</summary><pre>${esc(JSON.stringify(n.payload,null,2))}</pre></details>`;if(tab==='Relations')return `<pre>${esc(DATA.edges.filter(e=>e.source===n.id||e.target===n.id).map(e=>`${e.source} --${e.label}--> ${e.target}`).join('\n')||'No relations detected.')}</pre>`;if(tab==='Doctrine')return doctrineBody(n);if(tab==='War Game')return warGameBody(n);return `<pre>${esc(JSON.stringify({state:n.state,status:n.status,scope:n.scope,front:n.front,end:n.end,priority:n.priority},null,2))}</pre>`}
    function doctrineBody(n){const relatedIds=new Set([n.id,...linked(n),...DATA.edges.filter(e=>e.source===n.id||e.target===n.id).flatMap(e=>[e.source,e.target])]);const related=[...relatedIds].map(id=>byId.get(id)).filter(Boolean).filter(x=>['SourceOfVolatility','Domain','Craft','CodeOfConduct','RulesOfEngagement','Protocol'].includes(x.type));const doctrine=[n.payload.description,n.payload.rationale,n.payload.objective,n.payload.purpose,...(n.payload.principles||[]),...(n.payload.maxims||[]),...(n.payload.heuristics||[]),...(n.payload.policies||[]),...(n.payload.required_constraints||[])].filter(Boolean);return `<pre>${esc(['Associated doctrine:',...related.map(x=>`${x.type}: ${x.name}`),'','Doctrine fields:',...(doctrine.length?doctrine:['No doctrine fields detected.']),'','Skin in the Game: risk / stakes / exposure / consequence-bearing',"Philosopher's Stone: convexity / optionality / asymmetry / ergodicity / Jensen / Kelly / barbell"].join('\n'))}</pre>`}
    function warGameBody(n){const payload=n.payload;const candidate=payload.expected_output||payload.war_game_output||payload;const missionLinked=n.type==='Mission'||DATA.edges.some(e=>(e.source===n.id||e.target===n.id)&&byId.get(e.source)?.type==='WarGame');return `<pre>${esc(JSON.stringify({recommendation:candidate.recommendation,triggered_gates:candidate.triggered_gates,reasoning_summary:candidate.reasoning_summary,next_actions:candidate.next_actions,review_required:candidate.review_required,abort_conditions:payload.abort_conditions||payload.blueprint?.abort_condition,mission_linked:missionLinked},null,2))}</pre>`}
    function updateMissionStrip(){const m=DATA.mission;document.getElementById('mission-strip').innerHTML=m?`<strong>${esc(m.name)}</strong><span>Status: ${esc(m.payload.status||'unknown')}</span><span>${esc(m.payload.target_trajectory||'no target trajectory')}</span>`:'<strong>No active mission detected</strong>'}
    function jumpToSection(){if(!activeSection)return;const el=[...document.querySelectorAll('[data-section]')].find(node=>node.dataset.section===activeSection);if(el)el.scrollIntoView({block:'start'})}
    renderTabs();renderTree();updateMissionStrip();renderWorkspace();renderInspector();setTimeout(jumpToSection,0);
  </script>
</body>
</html>
"""


def render_html(data: dict[str, Any]) -> str:
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__DATA__", data_json)


def write_interactive_war_room(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    examples_dir: Path = DEFAULT_EXAMPLES_DIR,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(build_cockpit_data(examples_dir)), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate output/interactive_war_room.html.")
    parser.add_argument("--examples-dir", type=Path, default=DEFAULT_EXAMPLES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    write_interactive_war_room(args.output, args.examples_dir)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
