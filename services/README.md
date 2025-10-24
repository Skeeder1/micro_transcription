# Services Module - AutoGen Integration

This module is prepared for future integration with AutoGen for text reformulation and processing.

## Purpose

The services module will provide AI-powered text reformulation capabilities using AutoGen agents:

- **Prompt Optimization**: Convert dictated text into optimized AI prompts
- **Email Formatting**: Transform casual speech into professional emails
- **Grammar Correction**: Fix spelling and grammar errors
- **Text Summarization**: Create concise summaries
- **Custom Reformulations**: Extensible agent-based processing

## Architecture

```
services/
├── __init__.py
├── config.py              # AutoGen configuration (API keys, models)
├── agents/                # AutoGen agent definitions
│   ├── __init__.py
│   ├── prompt_agent.py    # Prompt optimization agent
│   ├── email_agent.py     # Email formatting agent
│   └── grammar_agent.py   # Grammar correction agent
└── client.py              # Client to interact with agents
```

## Integration with API

The services module will be called by the API module via REST endpoints defined in:
- `api/routes/text_processing.py`

Example flow:
```
UI → API (/api/reformulate/prompt) → services.agents.prompt_agent → AutoGen → Response
```

## Setup Instructions (when implementing)

1. Install AutoGen:
   ```bash
   pip install pyautogen
   ```

2. Configure API keys in `services/config.py`:
   ```python
   # OpenAI API key for AutoGen
   OPENAI_API_KEY = "your-api-key-here"

   # Or use local LLM (Ollama, LM Studio, etc.)
   USE_LOCAL_LLM = True
   LOCAL_LLM_BASE_URL = "http://localhost:11434"
   ```

3. Implement agents in `services/agents/`

4. Update `api/routes/text_processing.py` to call your agents

## Configuration Example

See `config.py.example` for a template configuration file.

## References

- AutoGen Documentation: https://microsoft.github.io/autogen/
- AutoGen GitHub: https://github.com/microsoft/autogen
