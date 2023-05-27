import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")


def summarize(text: str) -> str:
    prompt = "Summarize the following text in a brief manner."
    prompt += " Make the summary interesting as it will be read out loud"
    prompt += " in a podcast format."
    prompt += " The host and audience are very interested in "
    prompt += " programming and AI."
    prompt += f"\n\nText: {text}\n\nSummary:"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt},
        ]
    )
    return response["choices"][0]["message"]["content"]
