from langchain_ollama import ChatOllama
from router import route_question

llm = ChatOllama(model="llama3.2", temperature=0)

question = "나 99년생이고 무직인데 국민취업지원제도 신청하면 가능해? 아니면 몇유형 신청해?"
user_profile = {"age": 27, "job_status": "무직"}

result = route_question(question, user_profile, extracted={}, llm=llm)
print(result)
