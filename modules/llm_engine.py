import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"


def generate_response(prompt):

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)

        response.raise_for_status()

        result = response.json()

        return result.get("response", "").strip()

    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama. Check whether Ollama is running."

    except requests.exceptions.Timeout:
        return "ERROR: Ollama request timed out."

    except requests.exceptions.RequestException as e:
        return f"ERROR: {str(e)}"


if __name__ == "__main__":

    prompt = """
    Explain what SQL is in simple English.
    Give one simple example.
    """

    result = generate_response(prompt)

    print("\nAI RESPONSE:\n")
    print(result)
