
import dotenv, os
dotenv.load_dotenv()

from openai import OpenAI
client = OpenAI(api_key = os.getenv('OPENAI_KEY'))

response = client.chat.completions.create(
  model="gpt-3.5-turbo-1106",
  response_format={ "type": "json_object" },
  messages=[
    {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
    {"role": "user", "content": "Who won the world series in 2020?"},
    {"role": "system", "content": "You are talking to the Pepper robot at the Human-Robot Interaction conference in Stockholm. The year is 2023."}

  ]
)
print(response.choices[0].message.content)