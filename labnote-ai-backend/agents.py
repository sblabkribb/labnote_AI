import os
import re
import logging
import asyncio
from typing import List, Dict, TypedDict, Annotated

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

# --- Helper functions ---
def _extract_section_content(uo_block: str, section_name: str) -> str:
    """Helper to extract content of a specific section from a UO block."""
    pattern = re.compile(r"#### " + re.escape(section_name) + r"\n(.*?)(?=\n####|\n------------------------------------------------------------------------)", re.DOTALL)
    match = pattern.search(uo_block)
    if match:
        content = match.group(1).strip()
        return content if content and not content.startswith('(') else "(not specified)"
    return "(not specified)"

def _clean_llm_output(text: str) -> str:
    """Removes common LLM artifacts and ensures the output is clean."""
    # "Here is the..." 또는 "The method section should be..." 와 같은 서론 제거
    text = re.sub(r"^(The\s(method|equipment|reagent)\ssection\sshould\sbe|Here is the content for)[^:\n]*:\s*", "", text, flags=re.IGNORECASE).strip()
    # 마크다운 코드 블록 ` ``` ` 제거
    text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    return text

async def _generate_options(query: str, uo_id: str, uo_name: str, section: str, uo_block: str) -> List[str]:
    """
    RAG 검색 결과와 명확한 지시문을 사용하여 AI 제안 옵션을 생성합니다.
    """
    logger.info(f"Generating options for UO '{uo_id}' - Section '{section}'")

    # 1. RAG 검색 및 컨텍스트 강화
    input_context = _extract_section_content(uo_block, "Input")
    rag_query = f"protocol for '{section}' section of unit operation '{uo_id}: {uo_name}' for experiment '{query}'"
    
    context_docs = rag_pipeline.retrieve_context(rag_query, k=3)
    rag_context = rag_pipeline.format_context_for_prompt(context_docs)

    # 2. LLM 프롬프트 재구성 (가장 직접적인 방식으로 수정)
    context_block = f"""
---
**CONTEXT FOR YOUR TASK**
- **Overall Experiment Goal:** {query}
- **Current Unit Operation:** {uo_id}: {uo_name}
- **Section to Write:** {section}
- **Known Inputs for this step:** {input_context}
"""

    if "No relevant context found" in rag_context or not rag_context.strip():
        logger.warning(f"No SOPs found for '{section}' in '{uo_name}'. Using general knowledge.")
        context_block += "- **Reference SOPs:** None available. Use your general scientific knowledge.\n---"
        attribution_str = "[참고: 관련된 SOP가 없어 일반 지식을 바탕으로 생성됨]"
    else:
        sources = sorted(list(set([doc.metadata.get('source', 'Unknown').split(os.path.sep)[-1] for doc in context_docs])))
        attribution_str = f"[참고 SOP: {', '.join(sources)}]"
        context_block += f"- **Reference SOPs:**\n{rag_context}\n---"

    # 각 스타일에 맞는 명확하고 직접적인 지시문 생성
    system_prompts = {
        "concise": "You are a scientist writing a lab note. Your task is to provide a concise, bulleted list for the given section. Respond ONLY with the list content itself.",
        "detailed": "You are a scientist writing a lab note. Your task is to provide a detailed, step-by-step protocol for the given section. Respond ONLY with the protocol content itself.",
        "alternative": "You are a scientist writing a lab note. Your task is to provide a list of key considerations or alternative methods for the given section. Respond ONLY with the list content itself."
    }
    
    # User prompt는 이제 컨텍스트와 최종 지시만 전달
    user_prompt = f"{context_block}\n\n**Task:** Write the content for the '{section}' section now, starting with `{attribution_str}`."

    # 3. LLM 호출 및 결과 처리
    tasks = [call_llm_api(system_prompt, user_prompt) for system_prompt in system_prompts.values()]
    generated_options = await asyncio.gather(*tasks)
    
    # 후처리 함수를 적용하여 결과 정리
    valid_options = [_clean_llm_output(opt) for opt in generated_options if not opt.startswith("(LLM Error")]
    # 비어있는 응답 필터링
    valid_options = [opt for opt in valid_options if opt]
    return valid_options

# --- Agent Nodes ---
async def agent_node_async(state: AgentState) -> AgentState:
    section = state['section_to_populate']
    logger.info(f"Agent Node: Generating content for {state['uo_id']} - Section '{section}'")
    options = await _generate_options(state['query'], state['uo_id'], state['uo_name'], section, state['uo_block'])
    if not options:
        logger.warning(f"Agent for section '{section}' produced no valid options.")
        options = ["[AI가 적절한 내용을 생성하지 못했습니다. 다른 섹션을 먼저 채우거나, 잠시 후 다시 시도해주세요.]"]
    state['options'][section] = options
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