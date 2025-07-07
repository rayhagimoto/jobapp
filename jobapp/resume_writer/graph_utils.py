from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langchain_core.runnables.base import Runnable
from typing import Any, Dict, List, Optional
from langchain_core.runnables import Runnable
from langchain_core.messages import BaseMessage

class LangChainLLMAdapter(Runnable):
    """
    Adapter to wrap a custom LLMInterface and make it compatible with LangChain's Runnable interface.
    """
    def __init__(self, llm_interface):
        self.llm_interface = llm_interface

    def invoke(self, input, config=None, **kwargs):
        # If input is a dict, try to extract a prompt
        if isinstance(input, dict):
            if "prompt" in input:
                prompt = input["prompt"]
            else:
                prompt = " ".join(str(v) for v in input.values() if isinstance(v, str))
        # If input is a LangChain ChatPromptValue or similar, try to get the string
        elif hasattr(input, "to_string"):
            prompt = input.to_string()
        elif hasattr(input, "messages"):
            # Try to join all message contents
            prompt = " ".join(getattr(m, "content", str(m)) for m in input.messages)
        else:
            prompt = str(input)
        return self.llm_interface.send_prompt(prompt)

class PipelineContextParseError(Exception):
    """
    Raised when required context keys are missing or invalid during context validation/parsing.
    """
    pass

class PipelineContextApplyError(Exception):
    """
    Raised when an error occurs while applying updates to the context (e.g., failed mutation, invalid update).
    """
    pass

def require_context_keys(context, keys, node_name=None):
    """
    Checks that all required keys are present and non-empty in the context dict.
    Raises PipelineContextParseError if any are missing or empty.
    """
    missing = [k for k in keys if k not in context or context[k] is None]
    if missing:
        msg = f"Missing required context keys: {missing}"
        if node_name:
            msg = f"[{node_name}] {msg}"
        raise PipelineContextParseError(msg)

class ChatNode:
    """
    Base class for chat-based pipeline nodes with flexible memory/history management.
    Provides a reusable method for sending prompts, updating memory, and storing intermediates.
    """
    def __init__(self, logger, llm, memory=None):
        self.logger = logger
        self.llm = llm  # Should be a LangChain-compatible LLM/chat model
        if memory is None:
            self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        else:
            self.memory = memory

    @staticmethod
    def _send_prompt(
        llm: Runnable,
        memory: ConversationBufferMemory,
        prompt: ChatPromptTemplate,
        msg_context: Dict[str, Any],
        context: Dict[str, Any],
        chat_key: str,
        phase_key: str,
        use_memory: bool,
        update_memory: bool,
        history: List[Any],
    ) -> Any:
        """
        Run a prompt with flexible memory/history usage, update context/memory as needed, and store intermediates.
        Args:
            prompt: ChatPromptTemplate to use for this step.
            msg_context: dict of variables for the prompt (may include chat_history).
            context: main pipeline context dict (for storing intermediates and chat history).
            chat_key: key in context for chat history (default 'chats').
            phase_key: subkey in context[chat_key] for this phase (e.g., 'planning').
            use_memory: if True, use self.memory.chat_memory.messages as chat_history.
            update_memory: if True, update memory and context chat history after call.
            history: explicit list of messages to use as chat_history (overrides memory if use_memory is False).
        Returns:
            output: The LLM's response (string).
        """

        # 1. Determine which chat history to use
        if use_memory and memory is not None:
            msg_context["chat_history"] = memory.chat_memory.messages
        elif history is not None:
            msg_context["chat_history"] = history
        # else: do not add chat_history to msg_context

        # 2. Run the prompt
        chain = prompt | llm
        result = chain.invoke(msg_context)
        output = result.content if hasattr(result, "content") else result

        # 3. Optionally update memory/context
        if update_memory and use_memory and memory is not None:
            # Canonical LangChain pattern: get the exact HumanMessage sent
            messages = prompt.format_messages(**msg_context)
            user_message = messages[-1]
            memory.chat_memory.add_user_message(user_message)
            memory.chat_memory.add_ai_message(AIMessage(content=output))
            if context is not None:
                context.setdefault(chat_key, {})
                if phase_key:
                    context[chat_key].setdefault(phase_key, [])
                    chat_list = context[chat_key][phase_key]
                else:
                    chat_list = context[chat_key]
                chat_list.append(user_message)
                chat_list.append(AIMessage(content=output))

        # 4. Return the output
        return output
    

    def send_prompt(self, prompt_key : str, context : dict, msg_context : dict):
        # Ensure chat_history is present if required by the prompt
        prompt = self.prompts[prompt_key]
        if (
            hasattr(prompt, 'input_variables') and
            'chat_history' in prompt.input_variables and
            'chat_history' not in msg_context
        ):
            msg_context['chat_history'] = []
        # Log the actual filled prompt
        filled_messages = prompt.format_messages(**msg_context)
        filled_prompt = "\n".join(m.content for m in filled_messages)
        memory = None if not hasattr(self, 'memory') else self.memory
        history = None if not hasattr(self, 'history') else self.history
        response = self._send_prompt(
            llm=self.llm,
            memory=memory,
            prompt=prompt,
            msg_context=msg_context,
            context=context,
            chat_key='chats',
            phase_key=self.phase_key,
            use_memory=self.use_memory,
            update_memory=self.update_memory,
            history=history,
        )
        # Store the actual prompt string for transcript readability
        context['intermediates'][f'{prompt_key}_inputs'] = filled_prompt
        context['intermediates'][f'{prompt_key}_output'] = response