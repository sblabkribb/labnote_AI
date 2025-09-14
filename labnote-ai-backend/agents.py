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
        # 플레이스홀더 텍스트가 아닌 실제 내용이 있을 경우에만 반환
        return content if content and not content.startswith('(') else "(not specified)"
    return "(not specified)"

async def _generate_options(query: str, uo_id: str, uo_name: str, section: str, uo_block: str) -> List[str]:
    """
    RAG 검색 결과와 동적 프롬프트를 사용하여 AI 제안 옵션을 생성합니다.
    """
    logger.info(f"Generating options for UO '{uo_id}' - Section '{section}'")

    # 1. RAG 검색 및 컨텍스트 강화
    input_context = _extract_section_content(uo_block, "Input")
    output_context = _extract_section_content(uo_block, "Output")
    rag_query = f"Provide a detailed protocol for the '{section}' section of the unit operation '{uo_id}: {uo_name}' as part of the experiment '{query}'."
    
    logger.info(f"Refined RAG Query: {rag_query}")
    context_docs = rag_pipeline.retrieve_context(rag_query, k=3)
    rag_context = rag_pipeline.format_context_for_prompt(context_docs)

    # 2. LLM 프롬프트 재구성
    base_prompt = f"""
You are an expert lab assistant writing a section of a lab note.
Your task is to write the content for the **'{section}'** section of the Unit Operation **'{uo_id}: {uo_name}'**.

**Experimental Context:**
- **Overall Goal:** {query}
- **Input for this step:** {input_context}
- **Expected Output of this step:** {output_context}
"""

    if "No relevant context found" in rag_context or not rag_context.strip():
        logger.warning(f"No relevant SOPs found for '{section}' in '{uo_name}'. Falling back to general knowledge.")
        base_prompt += "\n**Instructions:**\nSince no specific SOPs were found, write a plausible and scientifically sound entry for this section based on your general knowledge. Start with a note: '[참고: 관련된 SOP가 없어 일반 지식을 바탕으로 생성됨]'"
    else:
        sources = sorted(list(set([doc.metadata.get('source', 'Unknown').split(os.path.sep)[-1] for doc in context_docs])))
        attribution_str = f"[참고 SOP: {', '.join(sources)}]"
        base_prompt += f"""
**Reference Information from SOPs:**
{rag_context}

**Instructions:**
Based *only* on the reference information provided above, write the content for the section. Begin your response with the attribution: "{attribution_str}". Do not add any information not present in the references.
"""

    prompts = {
        "concise": {
            "system": "You write in a clear, direct, and brief style, focusing on the essential steps or items. Use bullet points.",
            "user": f"{base_prompt}\n\nGenerate a **concise** version for the '{section}' section."
        },
        "detailed": {
            "system": "You write in a highly detailed, step-by-step format, including specific parameters and quantities. Your tone is formal and precise.",
            "user": f"{base_prompt}\n\nGenerate a **detailed** version for the '{section}' section."
        },
        "alternative": {
            "system": "You provide helpful advice, suggesting alternative methods, key considerations, or potential pitfalls to watch out for.",
            "user": f"{base_prompt}\n\nGenerate a list of **alternatives or key considerations** for the '{section}' section."
        }
    }

    # 3. LLM 호출 및 결과 처리
    tasks = [call_llm_api(p["system"], p["user"]) for p in prompts.values()]
    generated_options = await asyncio.gather(*tasks)
    
    # 에러가 발생하지 않은 유효한 옵션만 필터링
    valid_options = [opt for opt in generated_options if not opt.startswith("(LLM Error")]
    # 최종 결과에서 불필요한 따옴표나 머리글 제거
    cleaned_options = [re.sub(r"^(The answer is|Here is the content for .*?:)\s*['\"]?(.*?)['\"]?$", r"\2", opt, flags=re.DOTALL) for opt in valid_options]
    return cleaned_options

# --- Agent Nodes (비동기 호출 로직 수정) ---
async def method_agent_async(state: AgentState) -> AgentState:
    logger.info(f"Method Agent: Generating content for {state['uo_id']}")
    options = await _generate_options(state['query'], state['uo_id'], state['uo_name'], 'Method', state['uo_block'])
    state['options']['Method'] = options
    return state

async def materials_agent_async(state: AgentState) -> AgentState:
    section = state['section_to_populate']
    logger.info(f"Materials Agent: Generating content for {state['uo_id']} - {section}")
    options = await _generate_options(state['query'], state['uo_id'], state['uo_name'], section, state['uo_block'])
    state['options'][section] = options
    return state

async def results_agent_async(state: AgentState) -> AgentState:
    section = state['section_to_populate']
    logger.info(f"Results Agent: Generating content for {state['uo_id']} - {section}")
    options = await _generate_options(state['query'], state['uo_id'], state['uo_name'], section, state['uo_block'])
    state['options'][section] = options
    return state

# 동기 래퍼 함수 (LangGraph는 동기 함수를 노드로 사용)
def method_agent(state: AgentState) -> AgentState:
    return asyncio.run(method_agent_async(state))
    
def materials_agent(state: AgentState) -> AgentState:
    return asyncio.run(materials_agent_async(state))

def results_agent(state: AgentState) -> AgentState:
    return asyncio.run(results_agent_async(state))
    
# --- Routing Logic & Graph Definition ---
def route_request(state: AgentState) -> str:
    logger.info(f"Router: Routing task for UO '{state['uo_id']}' - Section: '{state['section_to_populate']}'")
    section = state['section_to_populate']
    
    if section == "Method":
        return "method_agent"
    elif section in ["Input", "Reagent", "Consumables", "Equipment"]:
        return "materials_agent"
    elif section in ["Output", "Results & Discussions"]:
        return "results_agent"
    else:
        logger.warning(f"Router: No agent found for section '{section}'. Ending execution.")
        return END
# --- Graph Definition
def create_agent_graph():
    """
    Creates the agent graph with a conditional entry point for routing.
    """
    graph = StateGraph(AgentState)
    # Define the worker agent nodes
    graph.add_node("method_agent", method_agent)
    graph.add_node("materials_agent", materials_agent)
    graph.add_node("results_agent", results_agent)
    graph.set_conditional_entry_point(
        route_request,
        {
            "method_agent": "method_agent",
            "materials_agent": "materials_agent",
            "results_agent": "results_agent",
            END: END
        }
    )
    # All worker agents finish after their execution
    graph.add_edge("method_agent", END)
    graph.add_edge("materials_agent", END)
    graph.add_edge("results_agent", END)
    
    agent_graph = graph.compile()
    logger.info("Agent graph compiled successfully with conditional entry point.")
    return agent_graph

# --- Main execution function ---
def run_agent_team(query: str, uo_block: str, section: str) -> Dict:
    """
    Parses a UO block, runs the appropriate agent, and returns generated options.
    """
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