"""
LangGraph-based resume optimization pipeline scaffold (class-based nodes, logger injection).

Pipeline expects a context dict with the following keys:
    - 'input_resume': dict (immutable original resume, parsed from YAML)
    - 'edited_resume': dict (deepcopy of input_resume, all mutations here)
    - 'job_description': str
    - 'experiences': str
    - 'section_paths': list (YAML paths to optimize, from user config)
    - 'intermediates': dict (for plans, LLM outputs, etc.)
    - 'chats': dict (per-node chat histories, e.g. {'planning': [...], ...})
    - 'config': dict (user config, optional)

Best practices:
    - Never mutate 'input_resume'.
    - Always update 'edited_resume' using yaml_processor utilities and section_paths.
    - Store all intermediate LLM outputs, plans, etc. in 'intermediates'.
    - Use 'chats' for per-node or per-phase chat histories.
    - Add new fields to context as needed for extensibility.

Example usage:
    import copy, yaml, logging
    from jobapp.resume_writer.pipelines.langgraph_resume_pipeline import ResumeOptimizationPipeline
    
    with open('resume.yaml') as f:
        input_resume = yaml.safe_load(f)
    context = {
        'input_resume': dict: input_resume, 
        'edited_resume': dict: copy.deepcopy(input_resume),
        'job_description': str: job_description_str,
        'experiences': str: experiences_str,
        'section_paths': list: section_paths_list,
        'intermediates': {},
        'chats': {},
        'config': user_config_dict,
    }
    logger = logging.getLogger("resume_pipeline")
    pipeline = ResumeOptimizationPipeline(logger=logger)
    output_context = pipeline.invoke(context)
    # Pass output_context['edited_resume'] to output_manager
"""

from langgraph.graph import StateGraph
from typing import Dict, Any, TypedDict
import copy
import logging
from jobapp.resume_writer.yaml_processing_utils import format_yaml_with_quotes, extract_allowed_updates_only, apply_selective_resume_updates, format_current_sections
from .prompts import EditorPrompt1, EditorPrompt2, EditorPrompt3, EditorPrompt4, OptimizerPrompt, ValidationPrompt, FeedbackPrompt, BoldFormattingPrompt
from jobapp.resume_writer.graph_utils import require_context_keys, PipelineContextParseError, PipelineContextApplyError, ChatNode
from jobapp.resume_writer.utils import parse_llm_yaml_to_dict, parse_refinement_response, parse_formatting_response
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
import re
from jobapp.core.config_manager import ConfigManager
from langchain_core.runnables.base import Runnable


# --- Node class definitions ---
class LoadInputsNode:
    def __init__(self, logger, section_paths):
        self.logger = logger
        self.section_paths = section_paths

    def __call__(self, context):
        # 1. Validate required fields (section_paths is now pipeline-level, not in context)
        required_fields = ['input_resume', 'job_description', 'experiences']
        for field in required_fields:
            if field not in context:
                self.logger.error(f"Missing required field in context: '{field}'")
                raise ValueError(f"Missing required field in context: '{field}'")
        context['edited_resume'] = copy.deepcopy(context['input_resume'])

        # 2. Type checks
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

        # 3. Initialize optional fields
        context.setdefault('intermediates', {})
        context.setdefault('chats', {})
        context.setdefault('config', {})

        # 4. Log input summary for traceability
        self.logger.info("[LoadInputsNode] Input context loaded.")
        # For debugging, print detailed input summary only at DEBUG level
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"[LoadInputsNode] Input context summary:\n"
                f"  input_resume keys: {list(context['input_resume'].keys())}\n"
                f"  edited_resume keys: {list(context['edited_resume'].keys())}\n"
                f"  job_description length: {len(context['job_description'])}\n"
                f"  experiences length: {len(context['experiences'])}\n"
                f"  section_paths (pipeline config): {self.section_paths}\n"
            )

        # Initialize intermediates and version tracking
        context.setdefault('intermediates', {})
        # Start version tracking: initial version
        context['intermediates'].setdefault('edited_resume_versions', []).append(copy.deepcopy(context['edited_resume']))

        return context

class PlanningPhaseNode(ChatNode):
    def __init__(self, logger, llm, memory=None):
        # Defaults to creating a ConversationBufferMemory
        super().__init__(logger=logger, llm=llm, memory=memory)
        self.phase_key = 'planning'
        self.use_memory=True
        self.update_memory=True

        # Define prompt templates for each step using MessagesPlaceholder
        self.prompts = {
            "jd_analysis": ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template(EditorPrompt1)
            ]),
            "skill_mapping": ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template(EditorPrompt2)
            ]),
            "profile_planning": ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template(EditorPrompt3)
            ]),
            "bullet_points": ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template(EditorPrompt4)
            ]),
        }

    def __call__(self, context):
        context.setdefault('chats', {})
        context['chats'].setdefault('planning', [])
        context.setdefault('intermediates', {})

        intermediates = context['intermediates']

        self.logger.info("[Node] Planning Phase: Starting 4-step planning process")

        # =========================
        # STEP 1: Job Description Analysis (EditorPrompt1)
        # =========================
        msg_context = {'job_description': context['job_description']}
        self.send_prompt(
            prompt_key='jd_analysis',
            context=context,
            msg_context=msg_context
        )
        self.logger.info("Ran EditorPrompt1 and stored output.")
        # if self.logger.isEnabledFor(logging.DEBUG):
        #     self.logger.debug(f"[PlanningPhaseNode] EditorPrompt1 msg_context: {msg_context}")

        # =========================
        # STEP 2: Skill Mapping & Prioritization (EditorPrompt2)
        # =========================
        msg_context = {'experiences': context['experiences']}
        self.send_prompt(
            prompt_key='skill_mapping',
            context=context,
            msg_context=msg_context
        )
        self.logger.info("Ran EditorPrompt2 and stored output.")
        # if self.logger.isEnabledFor(logging.DEBUG):
        #     self.logger.debug(f"[PlanningPhaseNode] EditorPrompt2 msg_context: {msg_context}")

        # =========================
        # STEP 3: Profile Planning (EditorPrompt3)
        # =========================
        msg_context = {'profile_draft': context['edited_resume']['profile']['description']}
        self.send_prompt(
            prompt_key='profile_planning',
            context=context,
            msg_context=msg_context
        )
        self.logger.info("Ran EditorPrompt3 and stored output.")
        # if self.logger.isEnabledFor(logging.DEBUG):
        #     self.logger.debug(f"[PlanningPhaseNode] EditorPrompt3 msg_context: {msg_context}")

        # Update edited_resume to use the description recommended in the profile planning step, if present
        new_description = None
        try:
            # Try to extract a new description from the LLM output (assume it's in intermediates['profile_planning_output'])
            planning_output = context['intermediates'].get('profile_planning_output')
            if planning_output:
                # If it's a dict with 'profile'->'description', use that
                if isinstance(planning_output, dict):
                    new_description = planning_output.get('profile', {}).get('description')
                # If it's a string, try to parse as YAML
                elif isinstance(planning_output, str):
                    from jobapp.resume_writer.utils import parse_llm_yaml_to_dict
                    parsed = parse_llm_yaml_to_dict(planning_output)
                    new_description = parsed.get('profile', {}).get('description')
        except Exception as ex:
            self.logger.debug(f"[PlanningPhaseNode] Could not extract new profile description: {ex}")
        if new_description:
            self.logger.debug(f"[PlanningPhaseNode] Updating profile.description in edited_resume via apply_selective_resume_updates. Section: ['profile.description']")
            apply_selective_resume_updates(
                context['edited_resume'],
                {'profile': {'description': new_description}},
                ['profile.description']
            )

        # =========================
        # STEP 4: Bullet Point Planning (EditorPrompt4)
        # =========================
        full_resume_yaml = format_yaml_with_quotes(context['edited_resume'], exclude_sections=True)
        msg_context = {'resume_draft': full_resume_yaml}
        self.send_prompt(
            prompt_key='bullet_points',
            context=context,
            msg_context=msg_context
        )
        self.logger.info("Ran EditorPrompt4 and stored output.")

        return context

class OptimizationPhaseNode(ChatNode):
    def __init__(self, logger, llm, section_paths):
        super().__init__(llm=llm, logger=logger)
        self.section_paths = section_paths
        self.phase_key = 'optimizer'
        self.use_memory = True
        self.update_memory = True

        self.prompts = {
            "optimizer_prompt": ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template(
                    OptimizerPrompt
                )
            ])
        }

    def __call__(self, context):
        context.setdefault('chats', {})
        context['chats'].setdefault('optimizer', [])
        context.setdefault('intermediates', {})
        require_context_keys(
            context,
            ["edited_resume", "intermediates"],
            node_name="OptimizationPhaseNode"
        )
        try:
            resume_yaml = format_yaml_with_quotes(context['input_resume'], exclude_sections=True)
            profile_plan = context['intermediates']['profile_planning_output']
            bullet_points_plan = context['intermediates']['bullet_points_output']
        except KeyError as e:
            raise PipelineContextParseError(f"Missing required key in context['intermediates'] for optimizer input: {e}")
        optimizer_context = {
            "profile_plan": profile_plan,
            "bullet_points_plan": bullet_points_plan,
            "resume_yaml": resume_yaml,
        }
        self.send_prompt(
            prompt_key='optimizer_prompt',
            context=context,
            msg_context=optimizer_context
        )
        optimization_output = context['intermediates'].get('optimizer_prompt_output')

        # Parse and apply LLM output
        llm_updates = parse_llm_yaml_to_dict(optimization_output)
        allowed_updates = extract_allowed_updates_only(llm_updates, self.section_paths)
        self.logger.debug(f"[OptimizationPhaseNode] Applying allowed updates to edited_resume using section_paths: {self.section_paths}")
        apply_selective_resume_updates(context['edited_resume'], allowed_updates, self.section_paths)
        context['intermediates']['applied_updates'] = allowed_updates
        # After applying updates, track version
        context['intermediates'].setdefault('edited_resume_versions', []).append(copy.deepcopy(context['edited_resume']))
        self.logger.debug(f"[OptimizationPhaseNode] Applied updates: {allowed_updates}")

        return context

class ValidationPhaseNode(ChatNode):
    def __init__(self, logger, section_paths, max_retries, llm):
        super().__init__(logger=logger, llm=llm)
        self.logger = logger
        self.section_paths = section_paths
        self.max_retries = max_retries
        self.phase_key = 'validation'
        self.use_memory = False
        self.update_memory = False
        self.prompts = {
            "validation_prompt": ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),  # Will be empty/not used
                HumanMessagePromptTemplate.from_template(ValidationPrompt)
            ])
        }

    def __call__(self, context):
        context.setdefault('chats', {})
        context['chats'].setdefault('validation', [])
        context.setdefault('intermediates', {})
        resume_yaml = format_current_sections(context['edited_resume'], self.section_paths)
        initial_resume_yaml = format_current_sections(context['input_resume'], self.section_paths)
        validation_prompt_context = {
            'job_description': context['job_description'],
            'experiences': context['experiences'],
            'initial_resume': initial_resume_yaml,
            'edited_resume': resume_yaml,
        }
        self.send_prompt(
            prompt_key='validation_prompt',
            context=context,
            msg_context=validation_prompt_context
        )
        validation_output = context['intermediates'].get('validation_prompt_output')
        context['chats']['validation'].append({'input': validation_prompt_context, 'output': validation_output})
        parsed = parse_llm_yaml_to_dict(validation_output)
        context['intermediates']['validation_attempts'] = context['intermediates'].get('validation_attempts', 0) + 1
        iteration = context['intermediates']['validation_attempts']
        try:
            results = parsed.get("VALIDATION_RESULTS", {})
            dishonesty_score = results.get("DISHONESTY_SCORE", 0)
            is_valid = isinstance(dishonesty_score, int) and dishonesty_score <= 20
        except Exception as ex:
            snippet = validation_output[:300].replace('\n', ' ')
            raise PipelineContextApplyError(
                f"[ValidationPhaseNode] Failed to parse VALIDATION_RESULTS or DISHONESTY_SCORE from LLM output on validation attempt {iteration}. "
                f"Output snippet: {snippet}. Exception: {ex}"
            ) from ex
        context['intermediates']['is_valid'] = is_valid
        context['intermediates']['dishonesty_score'] = dishonesty_score
        self.logger.info(f"Validation result: is_valid={is_valid}, dishonesty_score={dishonesty_score}, iteration={iteration}")
        if iteration >= self.max_retries and not is_valid:
            self.logger.warning(f"Max validation attempts ({self.max_retries}) reached. Forcing is_valid=True to terminate loop.")
            context['intermediates']['is_valid'] = True
        return context

class RefinementPhaseNode(ChatNode):
    def __init__(self, logger, llm, section_paths, max_validation_attempts):
        super().__init__(logger=logger, llm=llm)
        self.section_paths = section_paths
        self.logger = logger
        self.max_validation_attempts = max_validation_attempts
        self.phase_key = 'refinement'
        self.use_memory = False
        self.update_memory = False
        self.prompts = {
            "feedback_prompt": ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),  # Will be empty/not used
                HumanMessagePromptTemplate.from_template(FeedbackPrompt)
            ])
        }

    def __call__(self, context: Dict[str, Any]):
        context.setdefault('chats', {})
        context['chats'].setdefault('refinement', [])
        require_context_keys(
            context,
            ["edited_resume", "intermediates"],
            node_name="RefinementPhaseNode"
        )
        self.logger.info("[Node] Refinement Phase: Starting refinement process")
        context.setdefault('intermediates', {})
        context.setdefault('chats', {})
        context['chats'].setdefault('refinement', [])
        try:
            validation_chats = context['chats'].get('validation', [])
            validator_feedback = validation_chats[-1]['output'] if validation_chats else ''
            dishonesty_score = context['intermediates'].get('dishonesty_score', 0)
            iteration = context['intermediates'].get('validation_attempts', 1)
            refinement_prompt_context = {
                'validator_feedback': validator_feedback,
                'dishonesty_score': dishonesty_score,
                'edited_resume': format_yaml_with_quotes(context['edited_resume'], exclude_sections=True)
            }
            # Comment out or wrap the following print in DEBUG check to reduce verbosity
            # print(f"[RefinementPhaseNode] HumanMessage: {refinement_prompt_context}")
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"[RefinementPhaseNode] HumanMessage keys: {list(refinement_prompt_context.keys())}")
            self.send_prompt(
                prompt_key='feedback_prompt',
                context=context,
                msg_context=refinement_prompt_context
            )
            refinement_output = context['intermediates'].get('feedback_prompt_output')
            # Try to extract YAML from the output
            try:
                # Attempt to split the output into YAML and changelog sections
                # Look for a changelog section (e.g., starting with 'CHANGES_MADE:' or 'CHANGELOG:')
                changelog = ""
                yaml_part = refinement_output
                changelog_match = re.search(r'(CHANGES_MADE:|CHANGELOG:)', refinement_output)
                if changelog_match:
                    split_idx = changelog_match.start()
                    yaml_part = refinement_output[:split_idx].strip()
                    changelog = refinement_output[split_idx:].strip()
                resume_yaml = parse_llm_yaml_to_dict(yaml_part)
            except Exception as ex:
                print(f"[RefinementPhaseNode] Failed to parse YAML from LLM output. Raw output:\n{refinement_output}")
                raise ValueError("Could not parse YAML resume from LLM output.") from ex
            self.logger.debug(f"[RefinementPhaseNode] Applying selective updates to edited_resume using section_paths: {self.section_paths}")
            apply_selective_resume_updates(context['edited_resume'], resume_yaml, self.section_paths)
            context['intermediates']['refinement_changelog'] = changelog
            # After updating edited_resume, track version
            context['intermediates'].setdefault('edited_resume_versions', []).append(copy.deepcopy(context['edited_resume']))
            self.logger.info(f"Refinement applied successfully on iteration {iteration}")
            if iteration >= self.max_validation_attempts:
                self.logger.warning(f"Max validation attempts ({self.max_validation_attempts}) reached in refinement. Forcing is_valid=True to terminate loop.")
                context['intermediates']['is_valid'] = True

        except Exception as e:
            raise PipelineContextApplyError(f"[RefinementPhaseNode] Failed to apply refinement phase logic: {e}") from e
        return context

class FormattingPhaseNode(ChatNode):
    def __init__(self, logger, llm):
        super().__init__(logger=logger, llm=llm)
        self.logger = logger
        self.use_memory = False
        self.update_memory = False
        self.phase_key = 'formatting'
        self.prompts = {
            "formatting_prompt": ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),  # Will be empty/not used
                HumanMessagePromptTemplate.from_template(BoldFormattingPrompt)
            ])
        }

    def __call__(self, context: Dict[str, Any]) -> Dict[str, Any]:
        require_context_keys(
            context,
            ["edited_resume", "intermediates", "chats"],
            node_name="FormattingPhaseNode"
        )
        self.logger.info("[Node] Formatting Phase: Running formatting LLM prompt.")
        context.setdefault('intermediates', {})
        context.setdefault('chats', {})
        context['chats'].setdefault('formatting', [])
        try:
            formatting_prompt_context = {
                'resume_yaml': format_yaml_with_quotes(context['edited_resume'], exclude_sections=True),
                'target_keywords': context['intermediates']['jd_analysis_output'],
            }
            iteration = context['intermediates'].get('validation_attempts', 1)
            # Comment out or wrap the following in DEBUG check to reduce verbosity
            # self.logger.debug(f"[FormattingPhaseNode] formatting_prompt_context: {formatting_prompt_context}")
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"[FormattingPhaseNode] formatting_prompt_context keys: {list(formatting_prompt_context.keys())}")
            self.send_prompt(
                prompt_key='formatting_prompt',
                context=context,
                msg_context=formatting_prompt_context
            )
            formatting_output = context['intermediates'].get('formatting_prompt_output')
            context['chats']['formatting'].append({'input': formatting_prompt_context, 'output': formatting_output})
            formatted_resume_yaml = parse_formatting_response(formatting_output)
            formatted_resume = parse_llm_yaml_to_dict(formatted_resume_yaml)
            if not isinstance(formatted_resume, dict):
                snippet = formatting_output[:300].replace('\n', ' ')
                raise PipelineContextApplyError(
                    f"[FormattingPhaseNode] Failed to parse formatted resume as dict from LLM output on formatting attempt {iteration}. "
                    f"Type: {type(formatted_resume)}, Output snippet: {snippet}"
                )
            # Overwrite the 'sections' field to guarantee it is preserved
            formatted_resume['sections'] = context['input_resume']['sections']
            self.logger.debug("[FormattingPhaseNode] Overwrote 'sections' in formatted_resume with value from input_resume.")
            context['intermediates']['formatted_resume'] = formatted_resume
            self.logger.info(f"Formatting applied successfully on iteration {iteration}.")
        except Exception as e:
            raise PipelineContextApplyError(f"[FormattingPhaseNode] Failed to apply formatting phase logic: {e}") from e
        return context

class OutputCompileNode:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    def __call__(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("[Node] Output/Compile")
        context['intermediates']['output'] = 'output saved here'
        return context

class ResumePipelineState(TypedDict, total=False):
    input_resume: dict
    edited_resume: dict
    job_description: str
    experiences: str
    intermediates: dict
    chats: dict

class ResumeOptimizationPipeline:
    """
    LangGraph-based resume optimization pipeline.

    Output contract:
        - invoke(context) returns a dict with:
            - 'edited_resume': the final optimized resume (dict)
            - 'context': the full pipeline context (dict), including all intermediates, transcripts, etc.
    """
    def __init__(
        self,
        config: ConfigManager,
        logger: logging.Logger,
        llm: Runnable
    ):
        self.config = config
        self.logger = logger
        self.llm = llm
        self.section_paths = config.get_section_paths()
        
        # Max retries: prefer module config, then default config, then fallback
        self.max_retries = config.get('settings', {}).get('validation', {}).get('max_retries', 5)
        self._build_graph()

    def _build_graph(self):
        self.graph = StateGraph(state_schema=ResumePipelineState)
        self.graph.add_node("load_inputs", LoadInputsNode(self.logger, self.section_paths))
        self.graph.add_node("planning_phase", PlanningPhaseNode(self.logger, self.llm))
        self.graph.add_node("optimization_phase", OptimizationPhaseNode(self.logger, self.llm, self.section_paths))
        self.graph.add_node("validation_phase", ValidationPhaseNode(self.logger, self.section_paths, self.max_retries, self.llm))
        self.graph.add_node("refinement_phase", RefinementPhaseNode(self.logger, self.llm, self.section_paths, self.max_retries))
        self.graph.add_node("formatting_phase", FormattingPhaseNode(self.logger, self.llm))
        self.graph.add_node("output_compile", OutputCompileNode(self.logger))

        # Edges (transitions)
        self.graph.add_edge("load_inputs", "planning_phase")
        self.graph.add_edge("planning_phase", "optimization_phase")
        self.graph.add_edge("optimization_phase", "validation_phase")

        def validation_router(context: Dict[str, Any]) -> str:
            # Use intermediates['is_valid'] to decide
            return "formatting_phase" if context.get('intermediates', {}).get('is_valid') else "refinement_phase"

        self.graph.add_conditional_edges("validation_phase", validation_router)
        self.graph.add_edge("refinement_phase", "optimization_phase")  # Loop back
        self.graph.add_edge("formatting_phase", "output_compile")

        self.graph.set_entry_point("load_inputs")
        self.graph.set_finish_point("output_compile")
        self.pipeline = self.graph.compile()

    def invoke(self, context):
        final_context = self.pipeline.invoke(context)
        return {
            "edited_resume": final_context["edited_resume"],
            "context": final_context,
            "formatted_resume": final_context.get("intermediates", {}).get("formatted_resume")
        }

# Example usage (not executed here):
# import copy, yaml, logging
# with open('resume.yaml') as f:
#     input_resume = yaml.safe_load(f)
# section_paths = ["profile.description", "skills", "experience[Susquehanna]"]
# logger = logging.getLogger("resume_pipeline")
# pipeline = ResumeOptimizationPipeline(logger=logger, section_paths=section_paths, max_validation_attempts=5)
# context = {
#     'input_resume': input_resume,
#     'edited_resume': copy.deepcopy(input_resume),
#     'job_description': job_description_str,
#     'experiences': experiences_str,
#     'intermediates': {},
#     'chats': {},
#     'config': user_config_dict,
# }
# output_context = pipeline.invoke(context)
# output_manager.write_outputs(output_context['edited_resume'])
