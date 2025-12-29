from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings
import boto3
import os
from dotenv import load_dotenv
import os
load_dotenv()

tokenizer = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1",
                              region_name=os.getenv('AWS_REGION'),
                               aws_access_key_id="AWS_ACCESS_KEY_ID",
                               aws_secret_access_key="AWS_SECRET_ACCESS_KEY"
)

data = [
]

vector_db = FAISS.from_texts(data, embedding=tokenizer)

def search_data(query:str, k:int = 2 ):
    docs = vector_db.similarity_search(query, k)
    return "\n".join( [ doc.page_content for doc in docs ] )