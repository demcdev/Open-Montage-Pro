import json
from pathlib import Path
from lib.checkpoint import write_checkpoint, validate_artifact

pipeline_dir = Path("pipeline_defs")
project_id = "trex-test-40s"
project_dir = Path("projects") / project_id
artifacts_dir = project_dir / "artifacts"

# Load brief and decision log
with open(artifacts_dir / "brief.json", "r", encoding="utf-8") as f:
    brief = json.load(f)

with open(artifacts_dir / "decision_log.json", "r", encoding="utf-8") as f:
    decision_log = json.load(f)

# 1. Complete idea checkpoint with human_approved=True
write_checkpoint(
    pipeline_dir=pipeline_dir,
    project_id=project_id,
    stage="idea",
    status="completed",
    artifacts={
        "brief": brief,
        "decision_log": decision_log
    },
    pipeline_type="documentary-montage",
    checkpoint_policy="guided",
    human_approval_required=True,
    human_approved=True
)
print("Checkpoint 'idea' completado con éxito.")

# 2. Build scene_plan artifact
scenes = [
    {
        "id": "slot_01",
        "type": "broll",
        "description": "massive fossilized Tyrannosaurus rex skull in dark museum exhibition, dramatic side rim lighting, closed jaws in profile",
        "start_seconds": 0.0,
        "end_seconds": 4.5,
        "narrative_role": "establish_context",
        "hero_moment": True,
        "texture_keywords": ["fossil", "museum", "rim_lit", "dramatic"],
        "required_assets": [
            {"type": "video", "description": "T-rex skull profile shot", "source": "source"}
        ]
    },
    {
        "id": "slot_02",
        "type": "broll",
        "description": "extreme close up of fossilized dinosaur eye socket, forward-facing stereoscopic eye orbital, textured petrified bone",
        "start_seconds": 4.5,
        "end_seconds": 8.0,
        "narrative_role": "evidence",
        "hero_moment": False,
        "texture_keywords": ["macro", "orbital", "bone texture"],
        "required_assets": [
            {"type": "video", "description": "fossil eye socket detail", "source": "source"}
        ]
    },
    {
        "id": "slot_03",
        "type": "broll",
        "description": "macro shot of conical serrated teeth embedded in prehistoric sandstone, dark brown fossilized enamel",
        "start_seconds": 8.0,
        "end_seconds": 12.0,
        "narrative_role": "evidence",
        "hero_moment": False,
        "texture_keywords": ["serrated teeth", "enamel", "macro"],
        "required_assets": [
            {"type": "video", "description": "dinosaur teeth close up", "source": "source"}
        ]
    },
    {
        "id": "slot_04",
        "type": "broll",
        "description": "fossilized Triceratops femur bone showing deep crushing bite marks and spiral fractures, paleontological specimen",
        "start_seconds": 12.0,
        "end_seconds": 16.0,
        "narrative_role": "deliver_payload",
        "hero_moment": True,
        "texture_keywords": ["bone fracture", "bite marks", "fossil"],
        "required_assets": [
            {"type": "video", "description": "crushed prey fossil", "source": "source"}
        ]
    },
    {
        "id": "slot_05",
        "type": "broll",
        "description": "complete mounted Tyrannosaurus skeleton in active predatory stance, museum grand hall, high ceiling, long shadows",
        "start_seconds": 16.0,
        "end_seconds": 20.0,
        "narrative_role": "evidence",
        "hero_moment": False,
        "texture_keywords": ["mounted skeleton", "grand hall", "wide"],
        "required_assets": [
            {"type": "video", "description": "full skeleton exhibit", "source": "source"}
        ]
    },
    {
        "id": "slot_06",
        "type": "broll",
        "description": "geological rock strata and badlands erosion in Hell Creek Formation, arid layered sedimentary cliffs under hazy sun",
        "start_seconds": 20.0,
        "end_seconds": 24.0,
        "narrative_role": "transition",
        "hero_moment": False,
        "texture_keywords": ["badlands", "rock strata", "cretaceous formation"],
        "required_assets": [
            {"type": "video", "description": "sedimentary strata landscape", "source": "source"}
        ]
    },
    {
        "id": "slot_07",
        "type": "broll",
        "description": "paleontologists carefully brushing sandstone away from massive vertebrae fossils in outdoor field quarry",
        "start_seconds": 24.0,
        "end_seconds": 28.0,
        "narrative_role": "evidence",
        "hero_moment": False,
        "texture_keywords": ["field excavation", "quarry", "paleontology"],
        "required_assets": [
            {"type": "video", "description": "fossil excavation brush", "source": "source"}
        ]
    },
    {
        "id": "slot_08",
        "type": "broll",
        "description": "space asteroid entering Earth atmosphere in dark orbit, glowing atmospheric entry trail, NASA public archive imagery",
        "start_seconds": 28.0,
        "end_seconds": 32.5,
        "narrative_role": "build_tension",
        "hero_moment": False,
        "texture_keywords": ["asteroid", "cosmic entry", "nasa archive", "reverent"],
        "required_assets": [
            {"type": "video", "description": "asteroid entry orbit NASA", "source": "source"}
        ]
    },
    {
        "id": "slot_09",
        "type": "broll",
        "description": "dark dust and soot haze horizon over ancient landscape, barren Cretaceous-Paleogene extinction boundary twilight",
        "start_seconds": 32.5,
        "end_seconds": 36.5,
        "narrative_role": "emotional_beat",
        "hero_moment": False,
        "texture_keywords": ["k-pg boundary", "twilight", "dust horizon"],
        "required_assets": [
            {"type": "video", "description": "dark horizon twilight", "source": "source"}
        ]
    },
    {
        "id": "slot_10",
        "type": "broll",
        "description": "reverent slow fade of solitary fossil skull in shadow, glowing amber edge light before final dissolve into black",
        "start_seconds": 36.5,
        "end_seconds": 40.0,
        "narrative_role": "resolution",
        "hero_moment": True,
        "texture_keywords": ["fade to black", "amber light", "end tag overlay"],
        "required_assets": [
            {"type": "video", "description": "skull fade ending", "source": "source"}
        ]
    }
]

slots_meta = [
    {
        "id": "slot_01",
        "description": "massive fossilized Tyrannosaurus rex skull in dark museum exhibition, dramatic side rim lighting, closed jaws in profile",
        "hero": True,
        "preferred_sources": ["field_museum", "wikimedia", "smithsonian"],
        "queries": [
            "tyrannosaurus rex skull museum",
            "dinosaur fossil skull close up",
            "t-rex museum specimen lighting"
        ],
        "min_duration": 4.0,
        "target_hold_seconds": 4.5,
        "era_hint": "any"
    },
    {
        "id": "slot_02",
        "description": "extreme close up of fossilized dinosaur eye socket, forward-facing stereoscopic eye orbital, textured petrified bone",
        "hero": False,
        "preferred_sources": ["wikimedia", "smithsonian"],
        "queries": [
            "dinosaur skull eye socket",
            "t-rex skull front view",
            "fossil bone texture macro"
        ],
        "min_duration": 3.0,
        "target_hold_seconds": 3.5,
        "era_hint": "any"
    },
    {
        "id": "slot_03",
        "description": "macro shot of conical serrated teeth embedded in prehistoric sandstone, dark brown fossilized enamel",
        "hero": False,
        "preferred_sources": ["wikimedia", "smithsonian"],
        "queries": [
            "t-rex tooth fossil macro",
            "dinosaur teeth jaw close up",
            "fossilized serrated tooth"
        ],
        "min_duration": 3.5,
        "target_hold_seconds": 4.0,
        "era_hint": "any"
    },
    {
        "id": "slot_04",
        "description": "fossilized Triceratops femur bone showing deep crushing bite marks and spiral fractures, paleontological specimen",
        "hero": True,
        "preferred_sources": ["wikimedia", "field_museum"],
        "queries": [
            "dinosaur bone bite marks fossil",
            "triceratops fossil bone damage",
            "paleontology bone fracture specimen"
        ],
        "min_duration": 3.5,
        "target_hold_seconds": 4.0,
        "era_hint": "any"
    },
    {
        "id": "slot_05",
        "description": "complete mounted Tyrannosaurus skeleton in active predatory stance, museum grand hall, high ceiling, long shadows",
        "hero": False,
        "preferred_sources": ["wikimedia", "smithsonian", "pexels"],
        "queries": [
            "mounted dinosaur skeleton hall",
            "t-rex full skeleton museum",
            "paleontology exhibit museum wide"
        ],
        "min_duration": 3.5,
        "target_hold_seconds": 4.0,
        "era_hint": "any"
    },
    {
        "id": "slot_06",
        "description": "geological rock strata and badlands erosion in Hell Creek Formation, arid layered sedimentary cliffs under hazy sun",
        "hero": False,
        "preferred_sources": ["pexels", "archive_org", "wikimedia"],
        "queries": [
            "badlands rock strata geological",
            "sedimentary layers desert cliff",
            "hell creek formation landscape"
        ],
        "min_duration": 3.5,
        "target_hold_seconds": 4.0,
        "era_hint": "any"
    },
    {
        "id": "slot_07",
        "description": "paleontologists carefully brushing sandstone away from massive vertebrae fossils in outdoor field quarry",
        "hero": False,
        "preferred_sources": ["wikimedia", "archive_org", "pexels"],
        "queries": [
            "paleontologist digging fossil brush",
            "dinosaur quarry field excavation",
            "fossil excavation sandstone"
        ],
        "min_duration": 3.5,
        "target_hold_seconds": 4.0,
        "era_hint": "any"
    },
    {
        "id": "slot_08",
        "description": "space asteroid entering Earth atmosphere in dark orbit, glowing atmospheric entry trail, NASA public archive imagery",
        "hero": False,
        "preferred_sources": ["nasa", "wikimedia"],
        "queries": [
            "asteroid earth atmosphere orbit",
            "meteor atmospheric entry nasa",
            "space celestial impact earth"
        ],
        "min_duration": 4.0,
        "target_hold_seconds": 4.5,
        "era_hint": "any"
    },
    {
        "id": "slot_09",
        "description": "dark dust and soot haze horizon over ancient landscape, barren Cretaceous-Paleogene extinction boundary twilight",
        "hero": False,
        "preferred_sources": ["pexels", "archive_org"],
        "queries": [
            "dark smoke horizon desolate",
            "dust storm twilight landscape",
            "volcanic haze dark sky"
        ],
        "min_duration": 3.5,
        "target_hold_seconds": 4.0,
        "era_hint": "any"
    },
    {
        "id": "slot_10",
        "description": "reverent slow fade of solitary fossil skull in shadow, glowing amber edge light before final dissolve into black",
        "hero": True,
        "preferred_sources": ["field_museum", "smithsonian", "wikimedia"],
        "queries": [
            "dinosaur fossil skull dramatic light",
            "t-rex skull silhouette shadow",
            "museum fossil specimen dark"
        ],
        "min_duration": 3.0,
        "target_hold_seconds": 3.5,
        "era_hint": "any"
    }
]

scene_plan = {
    "version": "1.0",
    "style_playbook": "clean-professional",
    "scenes": scenes,
    "metadata": {
        "pipeline": "documentary-montage",
        "shape": "single-image expansion",
        "tone": "reverent",
        "thematic_question": "¿Qué nos revela la física del mayor depredador terrestre sobre la fragilidad del poder biológico frente al cosmos?",
        "total_planned_duration_seconds": 40.0,
        "slots": slots_meta
    }
}

with open(artifacts_dir / "scene_plan.json", "w", encoding="utf-8") as f:
    json.dump(scene_plan, f, indent=2, ensure_ascii=False)

validate_artifact("scene_plan", scene_plan)
print("Scene plan validado con éxito.")

# 3. Write checkpoint: scene_plan -> awaiting_human
write_checkpoint(
    pipeline_dir=pipeline_dir,
    project_id=project_id,
    stage="scene_plan",
    status="awaiting_human",
    artifacts={
        "scene_plan": scene_plan,
        "brief": brief,
        "decision_log": decision_log
    },
    pipeline_type="documentary-montage",
    checkpoint_policy="guided",
    human_approval_required=True,
    human_approved=False
)
print("Checkpoint 'scene_plan' guardado como 'awaiting_human'.")
