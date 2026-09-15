import json
import sys
from statistics import mean
from typing import Any

import grader as g
import requests as r

question = ''
messages = ['']

prompt = f'''
Please answer the user's question:

{question}'''


def _generate_dataset_original(broker: r.MessageBroker) -> Any:
    prompt = """
Generate an evaluation dataset for a prompt evaluation. The dataset will be used to evaluate prompts
that generate Python, JSON, or Regex specifically for AWS-related tasks. Generate an array of JSON
objects, each representing task that requires Python, JSON, or a Regex to complete.

Example output:
```json
[
  {
    "task": "Description of task",
  },
  ...additional
]
```

* Focus on tasks that can be solved by writing a single Python function, a single JSON object, or a single regex
* Focus on tasks that do not require writing much code

Please generate 3 objects.
"""
    response = broker.chat([prompt], 'json')
    return json.loads(response)


def generate_dataset(broker: r.MessageBroker) -> Any:
    prompt = """
Generate an evaluation dataset for a prompt evaluation. The dataset will be used to evaluate prompts
that generate Python, JSON, or Regex specifically for AWS-related tasks. Generate an array of JSON
objects, each representing task that requires Python, JSON, or a Regex to complete.

Example output:
```json
[
  {
    "task": "Description of task",
    "format": "json" or "python" or "regex",
    "solution_criteria": "Key criteria for evaluating the solution"
  },
  ...additional
]
```

* Focus on tasks that can be solved by writing a single Python function, a single JSON object, or a
  regular expression.
* Focus on tasks that do not require writing much code

Please generate 3 objects.
"""
    response = broker.chat([prompt], 'json')
    return json.loads(response)


def run_prompt(broker: r.MessageBroker, test_case) -> str:
    '''Merges the prompt and the test case input, then returns the result'''

    # prompt1 score: 8.17 ; updated score: 8.83
    prompt1 = f'''Please solve the following task:
{test_case['task']}'''

    return broker.chat(prompt1, test_case['format'])


def run_test_case(broker: r.MessageBroker, test_case: object) -> object:
    '''Calls run_prompt, then grades the result'''
    result = run_prompt(broker, test_case)
    model_grade = grade_by_model(broker, test_case, result)
    model_score = model_grade['score']
    syntax_score = g.syntax_score(result, test_case)

    average_grade = mean([model_score, syntax_score])

    return {
        'output': result,
        'test_case': test_case,
        'score': average_grade,
        'reasoning': model_grade['reasoning']
    }


# Function to grade a test case + output using a model
def grade_by_model(broker: r.MessageBroker, test_case, output):
    eval_prompt = f"""
You are an expert AWS code reviewer. Your task is to evaluate the following AI-generated solution.

Original Task:
<task>
{test_case["task"]}
</task>

Solution to Evaluate:
<solution>
{output}
</solution>

Criteria you should use to evaluate the solution:
<criteria>
{test_case["solution_criteria"]}
</criteria>

Output Format
Provide your evaluation as a structured JSON object with the following fields, in this specific order:
- "strengths": An array of 1-3 key strengths
- "weaknesses": An array of 1-3 key areas for improvement
- "reasoning": A concise explanation of your overall assessment
- "score": A number between 1-10

Respond with JSON. Keep your response concise and direct.
Example response shape:
{{
    "strengths": string[],
    "weaknesses": string[],
    "reasoning": string,
    "score": number
}}
    """

    broker.start_new_chat()
    eval_text = broker.chat(eval_prompt, 'json')
    return json.loads(eval_text)


def evaluate_dataset():
    broker = r.MessageBroker('claude-haiku-4-5', r.MAX_TOKENS)
    eval_results = []
    with open('dataset.json', 'r') as f:
        test_cases = json.load(f)
        for test_case in test_cases:
            result = run_test_case(broker, test_case)
            eval_results.append(result)

    average_score = mean([result["score"] for result in eval_results])
    print(f"Average score: {average_score}")

    return eval_results


def main():
    if len(sys.argv) > 1 and sys.argv[1].lower().startswith('gen'):
        # generate
        broker = r.MessageBroker('claude-haiku-4-5', r.MAX_TOKENS)

        dataset = generate_dataset(broker)
        dataset_as_str = json.dumps(dataset, indent=2)

        print(dataset_as_str)
        with open('dataset.json', 'w') as f:
            f.write(dataset_as_str)

    else:
        # evaluate
        eval_results = evaluate_dataset()
        print(json.dumps(eval_results, indent=2))

if __name__ == "__main__":
    main()