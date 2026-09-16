# Functions to validate the output structure
import ast
import json
import re
from statistics import mean

import requests as r


def _validate_json(text: str) -> float:
    try:
        json.loads(text.strip())
        return 10
    except json.JSONDecodeError:
        return 0


def _validate_python(text: str) -> float:
    try:
        ast.parse(text.strip())
        return 10
    except SyntaxError:
        return 0


def _validate_regex(text: str) -> float:
    try:
        re.compile(text.strip())
        return 10
    except re.error:
        return 0


def _syntax_score(response: str, test_case) -> float:
    format = test_case["format"]
    if format == "json":
        return _validate_json(response)
    elif format == "python":
        return _validate_python(response)
    else:
        return _validate_regex(response)


# Function to grade a test case + output using a model
def _grade_by_model(broker: r.MessageBroker, test_case, output):
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


def _run_prompt(broker: r.MessageBroker, test_case) -> str:
    '''Merges the prompt and the test case input, then returns the result'''

    # prompt1 score: 8.17 ; updated score: 8.83
    prompt1 = f'''Please solve the following task:
{test_case['task']}'''

    return broker.chat(prompt1, test_case['format'])


def run_test_case(broker: r.MessageBroker, test_case: object) -> object:
    '''Calls run_prompt, then grades the result'''
    result = _run_prompt(broker, test_case)
    model_grade = _grade_by_model(broker, test_case, result)
    model_score = model_grade['score']
    syntax_score = _syntax_score(result, test_case)

    average_grade = mean([model_score, syntax_score])

    return {
        'output': result,
        'test_case': test_case,
        'score': average_grade,
        'reasoning': model_grade['reasoning']
    }

def evaluate_dataset(broker: r.MessageBroker, test_cases: list[object]):
    eval_results = []

    for test_case in test_cases:
        result = run_test_case(broker, test_case)
        eval_results.append(result)

    average_score = mean([result["score"] for result in eval_results])
    print(f"Average score: {average_score}")

    return eval_results