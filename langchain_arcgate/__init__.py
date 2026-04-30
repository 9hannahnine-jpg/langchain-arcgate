"""
langchain-arcgate: Arc Gate prompt injection detection for LangChain.

Usage:
    from langchain_arcgate import ArcGateCallback
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(callbacks=[ArcGateCallback(api_key="demo")])
    response = llm.invoke("Your prompt here")
"""

from langchain_arcgate.callback import ArcGateCallback

__version__ = "0.1.0"
__all__ = ["ArcGateCallback"]
