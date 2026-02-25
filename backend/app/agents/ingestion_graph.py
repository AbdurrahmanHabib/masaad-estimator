from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END
from litellm import completion

class IngestionState(TypedDict):
    file_type: str
    raw_extraction: Dict[str, Any]
    semantic_mapping: List[Dict[str, Any]]
    calibration_data: Dict[str, Any]
    project_context: str

def semantic_router_node(state: IngestionState):
    prompt = f"Map these CAD/Vision data to internal systems: {state['raw_extraction']}"
    response = completion(model="gpt-4-turbo", messages=[{"role": "user", "content": prompt}])
    return {"semantic_mapping": response.choices[0].message.content}

workflow = StateGraph(IngestionState)
workflow.add_node("map_semantics", semantic_router_node)
workflow.set_entry_point("map_semantics")
workflow.add_edge("map_semantics", END)
ingestion_app = workflow.compile()