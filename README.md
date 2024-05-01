# WebAutotender
The intended goal is to have a Web UI (probably react based) to let you more easily interact with and modify the state of ongoing processes.
This is intended to be a more general and more useful rep0lacment for my RSS Feed automator which did processing on RSS Feed data and the configuration was in a text file.

### General Usage

There are two main items that you will interact with; Workflows and Instances.

Workflows are static but contain the steps that the processing will take.
Instances contain state, and follow the steps of its given Workflow.

By default, nothing happens in the program. There are currently no triggers to autonomously react to triggers.
So first, make a Workflow that will be your own custom trigger - eg polls periodically to check for RSS Feed updates.
Then make an instance of that Workflow that will actually run and do the polling.

Second you make a workflow that handles processing the trigger - eg grabbing something from the feed and doing something.
The triggering instance needs to have a step to spawn a new instance, but using the processing workflow.

### Test Env Setup
```
python -m venv venv
pip install uvicorn fastapi
source venv/bin/activate
```
