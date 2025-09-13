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
    query: str  # Overall experiment goal
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
        # Return content only if it's not a placeholder
        return content if content and not content.startswith('(') else "(not specified)"
    return "(not specified)"

async def _generate_options(query: str, uo_id: str, uo_name: str, section: str, uo_block: str) -> List[str]:
    """
    Uses RAG and concurrent LLM calls to generate three distinct options for a given section.
    """
    logger.info(f"Generating options for UO '{uo_id}' - Section '{section}'")

    # 1. RAG Search Enhancement
    input_context = _extract_section_content(uo_block, "Input")
    rag_query = f"SOP for '{section}' in '{uo_name} ({uo_id})'. Experiment: '{query}'. Input materials: '{input_context}'"
    
    logger.info(f"Refined RAG Query: {rag_query}")
    context_docs = rag_pipeline.retrieve_context(rag_query, k=3)
    rag_context = rag_pipeline.format_context_for_prompt(context_docs)

    # 2. Define LLM prompts for different styles
    user_prompt = f"""
Based on the provided RAG CONTEXT, please write the '{section}' section for the Unit Operation '{uo_id}: {uo_name}'.
The overall goal of the experiment is: '{query}'.
The specific inputs for this step are: '{input_context}'.

--- RAG CONTEXT ---
{rag_context}
---

Your response should ONLY be the content for the '{section}' section, without any titles or extra formatting.
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

    # Filter out potential errors
    return [opt for opt in generated_options if not opt.startswith("(LLM Error")]


# --- Agent Nodes ---
def method_agent(state: AgentState):
    """Generates content for the 'Method' section."""
    logger.info(f"Method Agent: Generating content for {state['uo_id']}")
    options = asyncio.run(
        _generate_options(state['query'], state['uo_id'], state['uo_name'], 'Method', state['uo_block'])
    )
    state['options']['Method'] = options
    return state

def materials_agent(state: AgentState):
    """Generates content for 'Reagent', 'Consumables', and 'Equipment' sections."""
    section = state['section_to_populate']
    logger.info(f"Materials Agent: Generating content for {state['uo_id']} - {section}")
    options = asyncio.run(
        _generate_options(state['query'], state['uo_id'], state['uo_name'], section, state['uo_block'])
    )
    state['options'][section] = options
    return state

def results_agent(state: AgentState):
    """Generates content for 'Output' and 'Results & Discussions' sections."""
    section = state['section_to_populate']
    logger.info(f"Results Agent: Generating content for {state['uo_id']} - {section}")
    options = asyncio.run(
        _generate_options(state['query'], state['uo_id'], state['uo_name'], section, state['uo_block'])
    )
    state['options'][section] = options
    return state

def supervisor_agent(state: AgentState):
    """Supervisor agent that routes tasks to specialized agents based on the section."""
    logger.info(f"Supervisor: Routing task for UO '{state['uo_id']}' - Section: '{state['section_to_populate']}'")
    section = state['section_to_populate']
    
    if section == "Method":
        return "method_agent"
    elif section in ["Input", "Reagent", "Consumables", "Equipment"]:
        return "materials_agent"
    elif section in ["Output", "Results & Discussions"]:
        return "results_agent"
    else:
        logger.warning(f"Supervisor: No agent found for section '{section}'. Ending execution.")
        return END

# --- Graph Definition ---
# (This part remains the same)
def create_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("method_agent", method_agent)
    graph.add_node("materials_agent", materials_agent)
    graph.add_node("results_agent", results_agent)
    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: supervisor_agent(state),
        {
            "method_agent": "method_agent",
            "materials_agent": "materials_agent",
            "results_agent": "results_agent",
            END: END
        }
    )
    graph.add_edge("method_agent", END)
    graph.add_edge("materials_agent", END)
    graph.add_edge("results_agent", END)
    agent_graph = graph.compile()
    logger.info("Agent graph compiled successfully.")
    return agent_graph

# --- Main execution function ---
def run_agent_team(query: str, uo_block: str, section: str) -> Dict:
    """
    Parses a UO block, runs the appropriate agent, and returns generated options.
    """
    match = re.search(r"### \[(U[A-Z]{2}\d{3}) (.*)\]", uo_block)
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