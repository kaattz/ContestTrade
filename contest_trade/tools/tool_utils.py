"""
ToolManager
- Tool Registration
- Tool Calling
- Tool Description
"""
import re
import asyncio
import importlib
import json
import sys
from pathlib import Path
from loguru import logger
from typing import Dict, List, Any, Callable, Optional, Union
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from models.llm_model import GLOBAL_LLM

class ToolManagerConfig:
    def __init__(self, tool_paths: List[str]):
        self.tool_paths = tool_paths

class ToolManager:
    """Tool registry - instance level, each agent has its own toolset"""
    
    def __init__(self, config: ToolManagerConfig):
        self.tools: Dict[str, Callable] = {}
        
        # ensure relative import support
        PROJECT_ROOT = Path(__file__).parent.parent.resolve()
        sys.path.append(str(PROJECT_ROOT))

        if config.tool_paths:
            self._register_from_configs(config.tool_paths)
        
    def _register_from_configs(self, tool_paths: List):
        """Register tools from config list"""
        for tool_path in tool_paths:
            try:
                self.register_from_module_path(tool_path)
            except Exception as e:
                logger.error(f"Failed to register tool from config {tool_path}: {e}")
    
    def register(self, tool_name: str, tool_function: Callable):
        """Register tool"""
        self.tools[tool_name] = tool_function
    
    def register_function(self, func: Callable, tool_name: str = None):
        """Register function as tool"""
        name = tool_name or getattr(func, 'name', None) or func.__name__
        self.register(name, func)
        return name
    
    def register_from_module_path(self, module_path: str):
        """Register tool function from module path"""
        try:
            parts = module_path.split('.')
            func_name = parts[-1]
            module_name = '.'.join(parts[:-1])
            
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            
            if not callable(func):
                raise ValueError(f"{module_path} is not callable")
            
            return self.register_function(func)
            
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Cannot import {module_path}: {e}")
    
    def register_functions(self, functions: List[Union[Callable, str]]):
        """Batch register tool functions"""
        registered = []
        for func in functions:
            if isinstance(func, str):
                name = self.register_from_module_path(func)
                registered.append(name)
            elif callable(func):
                name = self.register_function(func)
                registered.append(name)
            else:
                logger.warning(f"Skip invalid tool: {func}")
        
        return registered
    
    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """Get tool"""
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, Callable]:
        """Get all tools"""
        return self.tools.copy()
    
    def build_toolcall_context(self) -> str:
        """Get tools description text"""
        tool_schemas = []
        for tool_name, tool_func in self.tools.items():
            tool_schema = {}
            tool_schema["tool_name"] = tool_name
            tool_schema["description"] = tool_func.description
            for key, value in tool_func.args_schema.model_json_schema().items():
                if key == 'properties':
                    # trigger_time is not needed in tool call
                    if 'trigger_time' in value:
                        value.pop('trigger_time')
                if key == 'required':
                    if 'trigger_time' in value:
                        value.remove('trigger_time')
                if key not in ["title", "type"]:
                    tool_schema[key] = value

            tool_schemas.append(tool_schema)
        return json.dumps(tool_schemas, indent=2)
    
    async def call_tool(self, tool_name: str, kwargs: dict, trigger_time: str=None) -> Any:
        """Call tool"""
        if trigger_time:
            kwargs['trigger_time'] = trigger_time
        tool_func = self.get_tool(tool_name)
        if not tool_func:
            raise ValueError(f"Tool {tool_name} not found")
        
        try:
            print("call tool", tool_name, kwargs)
            if hasattr(tool_func, 'invoke'):
                return await tool_func.ainvoke(kwargs)
            elif asyncio.iscoroutinefunction(tool_func):
                return await tool_func(**kwargs)
            else:
                return tool_func(**kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": "Call tool Failed", "error_msg": str(e)}

    def parse_bounding_json(response: str) -> dict:
        """ parse tool call from llm response """
        bounding_json = re.search(r"<Output>(.*)</Output>", response, flags=re.DOTALL).group(1)
        parsed_output = json.loads(bounding_json)
        assert "tool_name" in parsed_output, "tool_name is required in the output"
        assert "properties" in parsed_output, "properties is required in the output"
        # market in properties
        if "market" in parsed_output["properties"]:
            parsed_output["properties"]["market"] = parsed_output["properties"]["market"].replace(" ", "")
        return parsed_output

    async def select_tool_by_llm(self,
                        prompt: str, 
                        retry_times: int = 3,
                        post_process_func: Callable = parse_bounding_json) -> str:
        """ use llm to select inner tool and return the tool call """
        messages = [{"role": "user", "content": prompt}]
        error_msg = ""
        for i in range(retry_times):
            if error_msg:
                messages.append({"role": "user", "content": error_msg + "\n\n Please try again."})
                error_msg = ""
            try:
                response = await GLOBAL_LLM.a_run(messages, verbose=False, thinking=False, max_retries=5, max_tokens=1000)
                llm_response = response.content
                print("llm_response", llm_response)
                messages.append({"role": "assistant", "content": llm_response})
                parsed_output = post_process_func(llm_response)
                return parsed_output
            except json.JSONDecodeError:
                error_msg += f"Failed to parse tool call {i+1} times"
                print("Failed to parse tool call", llm_response)
            except Exception as e:
                error_msg += f"Failed to call tool {i+1} times with error: {e}"
        return {"error": "Call tool Failed", "error_msg": error_msg}


class PrintHelloInput(BaseModel):
    input_string: str = Field(description="string to print.")

@tool(
    description="print a string",
    args_schema=PrintHelloInput
)
async def print_string(input_string: str):
    return input_string


if __name__ == "__main__":
    """Demo multiple tool registration methods"""

    config = ToolManagerConfig(tool_paths=["tools.tool_utils.print_string"])
    registry = ToolManager(config)

    registry.register_function(print_string)

    registry.register_from_module_path("tools.tool_utils.print_string")

    # get tools description
    print(registry.build_toolcall_context())

    # list all tools
    print(registry.get_all_tools())

    # call tool
    result = asyncio.run(registry.call_tool("print_string", input_string="Hello World!"))
    print(result)
