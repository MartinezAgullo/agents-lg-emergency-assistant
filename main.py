import os
import dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver



# For LangSimith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "emergency-assistant"


load_dotenv(override=True)s



checkpointer = SqliteSaver.from_conn_string("./checkpoints/emergency.db")

def main():
    print("Hello from agents-lg-emergency-assistant!")
    llm.with_structured_output(EvacuationPlan)



if __name__ == "__main__":
    main()
