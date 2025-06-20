# Eva Assistant - LangSmith Deployment Guide

This guide walks you through deploying Eva Assistant to LangSmith for monitoring, debugging, and production hosting.

## Prerequisites

1. **LangSmith Account**: Sign up at [smith.langchain.com](https://smith.langchain.com)
2. **LangSmith CLI**: Install the LangGraph CLI
   ```bash
   pip install langgraph-cli
   ```
3. **Environment Variables**: Set up your API keys

## Setup

### 1. Install LangGraph CLI
```bash
pip install langgraph-cli
```

### 2. Set Environment Variables
Add these to your `.env` file:
```bash
# Required
OPENAI_API_KEY=your_openai_api_key

# LangSmith (optional but recommended)
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING_V2=true
LANGSMITH_PROJECT=eva-assistant
```

### 3. Test Locally with LangSmith Tracing
```bash
python scripts/test_langsmith.py
```

## Deployment Options

### Option 1: LangSmith Studio (Recommended for Testing)

1. **Initialize deployment**:
   ```bash
   langgraph up
   ```

2. **Open LangSmith Studio**:
   ```bash
   langgraph studio
   ```

3. **Test your graph** in the interactive playground

### Option 2: LangSmith Cloud Deployment

1. **Deploy to LangSmith Cloud**:
   ```bash
   langgraph deploy --name eva-assistant
   ```

2. **Monitor deployment**:
   ```bash
   langgraph status eva-assistant
   ```

3. **View logs**:
   ```bash
   langgraph logs eva-assistant
   ```

## Configuration Details

### langgraph.json Explanation

```json
{
  "dependencies": ["."],              // Install current package
  "graphs": {
    "eva_assistant": {                // Graph name
      "path": "eva_assistant.agent.graph:get_eva_graph",  // Entry point
      "description": "Eva - AI Executive Assistant",
      "config_schema": {              // Input validation schema
        "type": "object",
        "properties": {
          "user_id": {"type": "string", "default": "founder"},
          "conversation_id": {"type": "string"},
          "with_persistence": {"type": "boolean", "default": true}
        }
      }
    }
  }
}
```

### Key Features

- **Automatic Tracing**: All LLM calls and graph steps are traced
- **Input Validation**: Schema validation for all inputs
- **Persistence**: SQLite conversation history
- **Error Handling**: Graceful error handling with detailed logs

## Testing in LangSmith

### 1. Test Input Examples

**Simple Meeting Request**:
```json
{
  "user_id": "founder",
  "current_request": "Schedule a meeting with John tomorrow at 2pm"
}
```

**Complex Scheduling**:
```json
{
  "user_id": "founder", 
  "current_request": "Book a 1-hour meeting with Alice and Bob for next Tuesday between 10am-4pm, title 'Product Strategy Review'"
}
```

### 2. Monitor Execution

In LangSmith dashboard you'll see:
- **Graph Flow**: Visual representation of Plan → Act → Reflect
- **LLM Calls**: All OpenAI API calls with prompts and responses
- **Tool Executions**: Mock tool calls and their results
- **State Changes**: How the conversation state evolves
- **Performance Metrics**: Latency, token usage, costs

### 3. Debug Issues

Use LangSmith to:
- **View failed executions** with full stack traces
- **Compare successful vs failed runs** 
- **Analyze prompt performance** and iterate
- **Monitor token usage** and costs
- **Test edge cases** interactively

## Production Considerations

### Security
- Store sensitive environment variables securely
- Use OAuth tokens with minimal required scopes
- Enable audit logging for compliance

### Performance
- Monitor token usage and API costs
- Set up alerting for failures
- Consider rate limiting for production

### Reliability  
- Test error handling scenarios
- Monitor conversation persistence
- Set up health checks

## Troubleshooting

### Common Issues

1. **Graph won't load**:
   - Check that `get_eva_graph()` returns a compiled graph
   - Verify all dependencies are installed
   - Check environment variables

2. **Tracing not working**:
   - Ensure `LANGCHAIN_API_KEY` is set
   - Check `LANGCHAIN_TRACING_V2=true`
   - Verify project name in `LANGCHAIN_PROJECT`

3. **Authentication errors**:
   - Verify OpenAI API key is valid
   - Check OAuth token files exist
   - Test with minimal permissions first

### Support

- LangSmith Documentation: [docs.smith.langchain.com](https://docs.smith.langchain.com)
- LangGraph CLI Help: `langgraph --help`
- Eva Assistant Logs: Check application logs for detailed error info

## Next Steps

1. **Deploy to staging** environment first
2. **Set up monitoring** and alerting
3. **Train on real data** and iterate prompts
4. **Scale to production** with proper infrastructure

Happy deploying! 🚀 