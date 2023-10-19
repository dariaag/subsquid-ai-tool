"""PlaygroundsSubgraphConnectorToolSpec."""
from introspect import introspect_schema
from typing import Optional, Union
import openai
import logging
from llama_index.agent import OpenAIAgent
import requests
from llama_index.bridge.langchain import FunctionMessage
from langchain.agents import initialize_agent, AgentType
from llama_hub.tools.graphql.base import GraphQLToolSpec
import json
from typing import Sequence
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.memory import ChatMessageHistory
from llama_index.tools import BaseTool, FunctionTool
from langchain.tools import BaseTool, StructuredTool




import os


openai_key = os.getenv("OPENAI_API_KEY")



def graphql_request(
      
        query: str,
        variables: Optional[dict] = None,
        operation_name: Optional[str] = None,
    ) -> Union[dict, str]:
        """
        Make a GraphQL query.

        Args:
            query (str): The GraphQL query string to execute.
            variables (dict, optional): Variables for the GraphQL query. Default is None.
            operation_name (str, optional): Name of the operation, if multiple operations are present in the query. Default is None.

        Returns:
            dict: The response from the GraphQL server if successful.
            str: Error message if the request fails.
        """
        
        payload = {"query": query.strip()}

        if variables:
            payload["variables"] = variables

        if operation_name:
            payload["operationName"] = operation_name

        try:
            TIMEOUT_SECONDS = 300 #5 mins timeout, the graph network can sometimes have unusually long response 
            #response = requests.post(self.url, headers=self.headers, json=payload, timeout=TIMEOUT_SECONDS)
            url = 'https://squid.subsquid.io/swaps-squid/v/v1/graphql'
            response = requests.post(url, json=payload)
            print(response.text)

            # Check if the request was successful
            response.raise_for_status()

            # Return the JSON response
            print(response.text)
            return response.json()

        except requests.RequestException as e:
            # Handle request errors
            return str(e)
        
        except requests.Timeout:
            return "Request timed out"
        
        except ValueError as e:
            # Handle JSON decoding errors
            return f"Error decoding JSON: {e}"
class MyOpenAIAgent:
    def __init__(
        self,
        tools: Sequence[BaseTool] = [],
        llm: ChatOpenAI = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-0613", openai_api_key = openai_key),
        chat_history: ChatMessageHistory = ChatMessageHistory(),
    ) -> None:
        self._llm = llm
        self._tools = {tool.metadata.name: tool for tool in tools}
        self._chat_history = chat_history

    def reset(self) -> None:
        self._chat_history.clear()

    def chat(self, message: str) -> str:
        chat_history = self._chat_history
        chat_history.add_user_message(message)
        functions = [tool.metadata.to_openai_function() for _, tool in self._tools.items()]

        ai_message = self._llm.predict_messages(chat_history.messages, functions=functions)
        chat_history.add_message(ai_message)

        function_call = ai_message.additional_kwargs.get("function_call", None)
        if function_call is not None:
            function_message = self._call_function(function_call)
            chat_history.add_message(function_message)
            ai_message = self._llm.predict_messages(chat_history.messages)
            chat_history.add_message(ai_message)

        return ai_message.content

    def _call_function(self, function_call: dict) -> FunctionMessage:
        tool = self._tools[function_call["name"]]
        output = tool(**json.loads(function_call["arguments"]))
        return FunctionMessage(
            name=function_call["name"],
            content=str(output), 
        )


tool1 = StructuredTool.from_function(graphql_request)
tool2 = StructuredTool.from_function(introspect_schema)
prompt = '''query MyQuery {
  swaps(limit: 10, orderBy: id_ASC) {
    id
    amount1
    amount0
    blockNumber
  }
}
query and provide consice summary of the data'''
def inspect_with_llama(prompt, openai_key):
    query_tool = FunctionTool.from_defaults(fn=graphql_request)
    introspect_tool = FunctionTool.from_defaults(fn=introspect_schema)
    openai.api_key = openai_key
    agent = MyOpenAIAgent(tools=[query_tool, introspect_tool])
    print(agent.chat(prompt))
    
def inspect_with_langchain(prompt, openai_key):
    openai.api_key = openai_key
    llm = OpenAI(temperature = 0, openai_api_key = openai_key)
    agent  = initialize_agent([tool1, tool2], llm, agent = AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,verbose = True)
    response  = agent.run(prompt)
    return response


