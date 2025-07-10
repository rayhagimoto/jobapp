"""
Resume optimization pipeline (2-prompt version, legacy code style).
- Extracts keywords from job description
- Optimizes profile description and skills list
- Follows legacy output and config conventions
"""

import copy
import logging
import re
import yaml
from typing import Dict, Any, TypedDict

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate

from jobapp.core.config_manager import ConfigManager
from jobapp.core.llm_interface import LLMInterface
from jobapp.resume_writer.yaml_processing_utils import format_yaml_with_quotes, extract_yaml_blocks, deep_merge
from jobapp.resume_writer.graph_utils import PipelineContextParseError, PipelineContextApplyError, require_context_keys, ChatNode
from jobapp.resume_writer.pipelines.prompts import ProfileAndSkillsPrompt, SkillsAndQualificationsPrompt

# --- Pipeline State Definition ---
class ResumePipelineState(TypedDict, total=False):
    input_resume: dict
    edited_resume: dict
    job_description: str
    experiences: str
    intermediates: dict
    chats: dict

# --- Node class definitions ---
class LoadInputsNode:
    """
    Loads and validates initial pipeline context. Mutates context in-place to add 'edited_resume', 'intermediates', and 'chats'.
    """
    def __init__(self, logger):
        self.logger = logger

    def __call__(self, context):
        self.logger.info("[LoadInputsNode] Entering node.")
        required_fields = ['input_resume', 'job_description', 'experiences']
        for field in required_fields:
            if field not in context:
                self.logger.error(f"Missing required field in context: '{field}'")
                raise PipelineContextParseError(f"Missing required field in context: '{field}'")
        context['edited_resume'] = copy.deepcopy(context['input_resume'])  # Mutate context
        if not isinstance(context['input_resume'], dict):
            self.logger.error("input_resume must be a dict (parsed YAML)")
            raise TypeError("input_resume must be a dict")
        if not isinstance(context['edited_resume'], dict):
            self.logger.error("edited_resume must be a dict (deepcopy of input_resume)")
            raise TypeError("edited_resume must be a dict")
        if not isinstance(context['job_description'], str):
            self.logger.error("job_description must be a string")
            raise TypeError("job_description must be a string")
        if not isinstance(context['experiences'], str):
            self.logger.error("experiences must be a string")
            raise TypeError("experiences must be a string")
        context.setdefault('intermediates', {})  # Mutate context
        context.setdefault('chats', {})  # Mutate context
        self.logger.info("[LoadInputsNode] Input context loaded.")
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"[LoadInputsNode] Input context summary:\n"
                f"  input_resume keys: {list(context['input_resume'].keys())}\n"
                f"  edited_resume keys: {list(context['edited_resume'].keys())}\n"
                f"  job_description length: {len(context['job_description'])}\n"
                f"  experiences length: {len(context['experiences'])}\n"
            )
        context['intermediates'].setdefault('edited_resume_versions', []).append(copy.deepcopy(context['edited_resume']))
        self.logger.info("[LoadInputsNode] Exiting node.")
        return context

class KeywordsExtractionNode(ChatNode):
    """
    Extracts keywords from the job description using the first prompt. Uses ChatNode for chat/LLM logic (legacy style).
    """
    def __init__(self, logger, llm):
        super().__init__(logger=logger, llm=llm)
        self.phase_key = 'keywords'
        self.prompts = {
            "keywords_prompt": ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template(SkillsAndQualificationsPrompt)
            ])
        }
        self.use_memory = True
        self.update_memory = True

    def __call__(self, context):
        self.logger.info("[KeywordsExtractionNode] Entering node.")
        context.setdefault('intermediates', {})
        job_description = context['job_description']
        try:
            msg_context = {
                "job_title": context.get("job_title", ""),
                "job_description": job_description
            }
            response = self.send_prompt(
                prompt_key="keywords_prompt",
                context=context,
                msg_context=msg_context
            )
            yaml_blocks = extract_yaml_blocks(response)
            keywords_yaml = yaml_blocks[0] if yaml_blocks else ''
            context['intermediates']['keywords_output'] = keywords_yaml
            context['intermediates']['keywords_raw'] = response
            self.logger.info("[KeywordsExtractionNode] Extracted keywords from job description.")
        except Exception as e:
            self.logger.error(f"[KeywordsExtractionNode] Error during keyword extraction: {e}")
            raise PipelineContextApplyError(f"Keywords extraction failed: {e}")
        self.logger.info("[KeywordsExtractionNode] Exiting node.")
        return context

class ResumeOptimizationNode(ChatNode):
    """
    Optimizes profile and skills using the second prompt. Uses ChatNode for chat/LLM logic (legacy style).
    """
    def __init__(self, logger, llm):
        super().__init__(logger=logger, llm=llm)
        self.phase_key = 'optimization'
        self.prompts = {
            "optimization_prompt": ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template(ProfileAndSkillsPrompt)
            ])
        }
        self.use_memory = True
        self.update_memory = True

    def __call__(self, context):
        self.logger.info("[ResumeOptimizationNode] Entering node.")
        context.setdefault('intermediates', {})
        edited_resume = context['edited_resume']
        experiences = context['experiences']
        keywords_yaml = context['intermediates'].get('keywords_output', '')
        resume_to_send = {k:v for (k,v) in edited_resume.items() if k in ['profile', 'skills']}
        resume_yaml = format_yaml_with_quotes(resume_to_send)
        try:
            msg_context = {
                "resume": resume_yaml,
                "experiences": experiences,
                "keywords": keywords_yaml
            }
            response = self.send_prompt(
                prompt_key="optimization_prompt",
                context=context,
                msg_context=msg_context
            )
            yaml_blocks = extract_yaml_blocks(response)
            if not yaml_blocks:
                self.logger.error("[ResumeOptimizationNode] No YAML blocks found in LLM response.")
                raise PipelineContextApplyError("No YAML blocks found in LLM response.")
            merged_yaml = "\n".join(yaml_blocks)
            try:
                edited_sections_only_dict = yaml.safe_load(merged_yaml)
            except yaml.YAMLError as e:
                self.logger.error(f"[ResumeOptimizationNode] Failed to parse YAML blocks: {e}")
                raise PipelineContextApplyError(f"Failed to parse YAML blocks: {e}")
            try:
                context['edited_resume'] = deep_merge(context['edited_resume'], edited_sections_only_dict)
            except Exception as e:
                self.logger.error(f"[ResumeOptimizationNode] Deep merge failed: {e}")
                raise PipelineContextApplyError(f"Deep merge failed: {e}")
            context['intermediates']['applied_updates'] = edited_sections_only_dict
            context['intermediates'].setdefault('edited_resume_versions', []).append(copy.deepcopy(context['edited_resume']))
            self.logger.info("[ResumeOptimizationNode] Applied profile and skills updates.")
        except Exception as e:
            self.logger.error(f"[ResumeOptimizationNode] Error during optimization: {e}")
            raise PipelineContextApplyError(f"Resume optimization failed: {e}")
        self.logger.info("[ResumeOptimizationNode] Exiting node.")
        return context

class OutputCompileNode:
    """
    Finalizes pipeline output. Mutates context to add 'output' key in intermediates.
    """
    def __init__(self, logger):
        self.logger = logger
    def __call__(self, context):
        self.logger.info("[OutputCompileNode] Entering node.")
        context['intermediates']['output'] = 'output saved here'  # Mutate context
        self.logger.info("[OutputCompileNode] Pipeline complete. Output ready.")
        self.logger.info("[OutputCompileNode] Exiting node.")
        return context

class ResumePipeline:
    """
    Orchestrates the resume optimization pipeline. Handles node execution, context management, and output writing.
    """
    def __init__(self, config: ConfigManager, llm: LLMInterface, logger=None):
        self.config = config
        self.llm = llm
        self.logger = logger or logging.getLogger(__name__)
        self.load_inputs_node = LoadInputsNode(self.logger)
        self.keywords_node = KeywordsExtractionNode(self.logger, self.llm)
        self.optimization_node = ResumeOptimizationNode(self.logger, self.llm)
        self.output_node = OutputCompileNode(self.logger)

    def invoke(self, input_resume: dict, job_description: str, experiences: str) -> dict:
        """
        Run the pipeline from inputs to outputs. Returns the final context dict.
        """
        self.logger.info("[ResumePipeline] Starting pipeline run.")
        context: ResumePipelineState = {
            'input_resume': input_resume,
            'job_description': job_description,
            'experiences': experiences,
        }
        try:
            context = self.load_inputs_node(context)
            context = self.keywords_node(context)
            context = self.optimization_node(context)
            context = self.output_node(context)
            self.logger.info("[ResumePipeline] Pipeline completed successfully.")
        except Exception as e:
            self.logger.error(f"[ResumePipeline] Pipeline failed: {e}")
            raise
        self.logger.info("[ResumePipeline] Exiting pipeline run.")
        return context
