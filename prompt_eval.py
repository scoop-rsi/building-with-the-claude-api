import json
import sys
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


def evaluate_dataset():
    broker = r.MessageBroker('claude-haiku-4-5', r.MAX_TOKENS)
    eval_results = []
    with open('dataset.json', 'r') as f:
        test_cases = json.load(f)
        eval_results = g.evaluate_dataset(broker, test_cases)

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