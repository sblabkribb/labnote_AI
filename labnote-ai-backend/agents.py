import os
import re
import logging
import asyncio
from typing import List, Dict, TypedDict, Annotated, Tuple

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# Local imports
from rag_pipeline import rag_pipeline
from llm_utils import call_llm_api

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Agent State Definition ---
class AgentState(TypedDict):
    query: str
    uo_block: str
    uo_id: str
    uo_name: str
    section_to_populate: str
    options: Dict[str, List[str]]
    messages: Annotated[list, add_messages]

# --- Helper function for content generation ---
def _extract_section_content(uo_block: str, section_name: str) -> str:
    """Helper to extract content of a specific section from a UO block."""
    pattern = re.compile(r"#### " + re.escape(section_name) + r"\n(.*?)(?=\n####|\n------------------------------------------------------------------------)", re.DOTALL)
    match = pattern.search(uo_block)
    if match:
        content = match.group(1).strip()
        return content if content and not content.startswith('(') else "(not specified)"
    return "(not specified)"

async def _generate_options(query: str, uo_id: str, uo_name: str, section: str, uo_block: str) -> Tuple[List[str], str]:
    """
    RAG 검색 결과에 따라 동적으로 프롬프트를 조정하고, 출처 정보 문자열을 함께 반환합니다. (예전 방식 적용)
    """
    logger.info(f"Generating options for UO '{uo_id}' - Section '{section}'")
    # 1. RAG Search Enhancement
    input_context = _extract_section_content(uo_block, "Input")
    rag_query = f"detailed list of {section} for unit operation {uo_id} ({uo_name}) for the experiment: {query}"
    
    logger.info(f"Refined RAG Query: {rag_query}")
    context_docs = rag_pipeline.retrieve_context(rag_query, k=3)
    rag_context = rag_pipeline.format_context_for_prompt(context_docs)
    
    # 2. Define LLM prompts for different style
    attribution_str = "" # 출처 정보를 담을 변수

    # RAG 검색 결과가 유의미한지 확인하고, 그에 따라 프롬프트와 출처 정보를 설정합니다.
    if "No relevant context found" in rag_context or not rag_context.strip():
        logger.warning(f"No relevant SOPs found for '{section}' in '{uo_name}'. Falling back to general knowledge.")
        attribution_str = "[주의: 참고할 SOP가 없어 LLM의 자체 지식으로 생성됨]"
        user_prompt = f"""
Please write the content for the '{section}' section of the Unit Operation '{uo_id}: {uo_name}'.
The overall experiment goal is: '{query}'.
The specific inputs for this step are: '{input_context}'.

Based on your expert knowledge in molecular biology, generate a plausible protocol.
Your response must ONLY be the content for the '{section}' section, without any titles or extra formatting.
"""
    else:
        sources = sorted(list(set([doc.metadata.get('source', 'Unknown').split(os.path.sep)[-1] for doc in context_docs])))
        attribution_str = f"[참고 SOP: {', '.join(sources)}]"
        user_prompt = f"""
Based on the provided reference information, please write the content for the '{section}' section of the Unit Operation '{uo_id}: {uo_name}'.
The overall experiment goal is: '{query}'.
The specific inputs for this step are: '{input_context}'.

--- REFERENCE INFORMATION ---
{rag_context}
---

Your response must ONLY be the content for the '{section}' section, based strictly on the provided references. Do not add titles or extra formatting.
"""

    prompts = {
        "concise": {
            "system": f"You are an expert scientist. Write a clear and concise summary for the '{section}' section. Be brief and to the point.",
            "user": user_prompt
        },
        "detailed": {
            "system": f"You are an expert scientist. Write a highly detailed, step-by-step protocol for the '{section}' section. Include specific parameters, quantities, and durations where applicable.",
            "user": user_prompt
        },
        "alternative": {
            "system": f"You are an expert scientist. Suggest an alternative approach or a list of key considerations for the '{section}' section. Focus on potential pitfalls or optimization strategies.",
            "user": user_prompt
        }
    }
    # 3. Concurrent LLM calls
    tasks = [call_llm_api(p["system"], p["user"]) for p in prompts.values()]
    generated_options = await asyncio.gather(*tasks)

    valid_options = [opt for opt in generated_options if not opt.startswith("(LLM Error")]
    return valid_options, attribution_str

# --- Agent Nodes ---
async def agent_node_async(state: AgentState) -> AgentState:
    section = state['section_to_populate']
    logger.info(f"Agent Node: Generating content for {state['uo_id']} - Section '{section}'")
    
    options, attribution = await _generate_options(
        state['query'], state['uo_id'], state['uo_name'], section, state['uo_block']
    )
    
    # 생성된 각 옵션 앞에 출처 정보를 붙여줍니다.
    state['options'][section] = [f"{attribution}\n{opt}" for opt in options if opt] if options else []

    if not state['options'][section]:
         logger.warning(f"Agent for section '{section}' produced no valid options.")
         state['options'][section] = ["[AI가 적절한 내용을 생성하지 못했습니다. 다른 섹션을 먼저 채우거나, 잠시 후 다시 시도해주세요.]"]
         
    return state

def agent_node(state: AgentState) -> AgentState:
    return asyncio.run(agent_node_async(state))

# --- Graph Definition ---
def route_request(state: AgentState) -> str:
    section = state['section_to_populate']
    logger.info(f"Router: Routing task for section: '{section}'")
    if section in ["Method", "Input", "Reagent", "Consumables", "Equipment", "Output", "Results & Discussions"]:
        return "agent"
    else:
        logger.warning(f"Router: No route found for section '{section}'. Ending execution.")
        return END

def create_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.set_conditional_entry_point(
        route_request,
        { "agent": "agent", END: END }
    )
    graph.add_edge("agent", END)
    agent_graph = graph.compile()
    logger.info("Agent graph compiled successfully.")
    return agent_graph

# --- Main execution function ---
def run_agent_team(query: str, uo_block: str, section: str) -> Dict:
    match = re.search(r"### \[(U[A-Z]{2,3}\d{3}) (.*)\]", uo_block)
    if not match:
        logger.error(f"Could not parse UO ID and Name from block.")
        return {}
        
    uo_id, uo_name = match.groups()

    initial_state = AgentState(
        query=query,
        uo_block=uo_block,
        uo_id=uo_id,
        uo_name=uo_name,
        section_to_populate=section,
        options={},
        messages=[]
    )
    
    graph = create_agent_graph()
    final_state = graph.invoke(initial_state)
    
    return {
        "uo_id": uo_id,
        "section": section,
        "options": final_state.get('options', {}).get(section, [])
    }

if __name__ == '__main__':
    # Example usage for testing
    test_query = "Plasmid construction using Golden Gate Assembly"
    test_block = """
------------------------------------------------------------------------
### [UHW250 Nucleic Acid Purification]
#### Meta
- Experimenter: AI Assistant
- Start_date: '2025-09-12 15:30'
- End_date: ''
#### Input
- (samples from the previous step) 
#### Reagent
- (e.g. enzyme, buffer, etc.) 
#### Consumables
- (e.g. filter, well-plate, etc.) 
#### Equipment
- (e.g. centrifuge, spectrophotometer, etc.) 
#### Method
- (method used in this step) 
#### Output
- (samples to the next step) 
#### Results & Discussions
- (Any results and discussions. Link file path if needed)
------------------------------------------------------------------------
"""
    
    print("--- Testing Method Agent ---")
    results = run_agent_team(test_query, test_block, "Method")
    print(results)