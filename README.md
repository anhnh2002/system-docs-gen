# DocAgent: Agentic Hierarchical Docstring Generation System

<p align="center">
  <img src="assets/meta_logo_white.png" width="20%" alt="Meta Logo">
</p>

DocAgent is a system designed to generate high-quality, context-aware docstrings for Python codebases using a multi-agent approach and hierarchical processing.

## Citation

If you use DocAgent in your research, please cite our paper:

```bibtex
@misc{yang2025docagent,
      title={DocAgent: A Multi-Agent System for Automated Code Documentation Generation}, 
      author={Dayu Yang and Antoine Simoulin and Xin Qian and Xiaoyi Liu and Yuwei Cao and Zhaopu Teng and Grey Yang},
      year={2025},
      eprint={2504.08725},
      archivePrefix={arXiv},
      primaryClass={cs.SE}
}
```

You can find the paper on arXiv: [https://arxiv.org/abs/2504.08725](https://arxiv.org/abs/2504.08725)

## Table of Contents

- [Motivation](#motivation)
- [Methodology](#methodology)
- [Installation](#installation)
- [Components](#components)
- [Configuration](#configuration)
- [Usage](#usage)
- [Running the Evaluation System](#running-the-evaluation-system)
- [Optional: Using a Local LLM](#optional-using-a-local-llm)

## Motivation

High-quality docstrings are crucial for code readability, usability, and maintainability, especially in large repositories. They should explain the purpose, parameters, returns, exceptions, and usage within the broader context. Current LLMs often struggle with this, producing superficial or redundant comments and failing to capture essential context or rationale. DocAgent aims to address these limitations by generating informative, concise, and contextually aware docstrings.

## Methodology

DocAgent employs two key strategies:

1.  **Hierarchical Traversal**: Processes code components by analyzing dependencies, starting with files having fewer dependencies. This builds a documented foundation before tackling more complex code, addressing the challenge of documenting context that itself lacks documentation.
2.  **Agentic System**: Utilizes a team of specialized agents (`Reader`, `Searcher`, `Writer`, `Verifier`) coordinated by an `Orchestrator`. This system gathers context (internal and external), drafts docstrings according to standards, and verifies their quality in an iterative process.

<img src="assets/system.png" width="100%" alt="System Overview">

For more details on the agentic framework, see the [Agent Component README](./src/agent/README.md).

## Installation

1.  Clone the repository:
    ```bash
    git clone <repository_url>
    cd DocAgent
    ```
2.  Install the necessary dependencies. It's recommended to use a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate # if you use venv, you can also use conda
    pip install -e .
    ```
    *Note: For optional features like development tools, web UI components, or specific hardware support (e.g., CUDA), refer to the comments in `setup.py` and install extras as needed (e.g., `pip install -e ".[dev,web]"`).*

## Components

DocAgent is composed of several key parts:

- **[Core Agent Framework](./src/agent/README.md)**: Implements the multi-agent system (Reader, Searcher, Writer, Verifier, Orchestrator) responsible for the generation logic.
- **[Docstring Evaluator](./src/evaluator/README.md)**: Provides tools for evaluating docstring quality, primarily focusing on completeness based on static code analysis (AST). *Note: Evaluation is run separately, see its README.*
- **[Generation Web UI](./src/web/README.md)**: A web interface for configuring, running, and monitoring the docstring *generation* process in real-time.

## Configuration

Before running DocAgent, you **must** create a configuration file named `config/agent_config.yaml`. This file specifies crucial parameters for the agents, such as the LLM endpoints, API keys (if required), model names, and generation settings.

1.  **Copy the Example**: An example configuration file is provided at `config/example_config.yaml`. Copy this file to `config/agent_config.yaml`:
    ```bash
    cp config/example_config.yaml config/agent_config.yaml
    ```
2.  **Edit the Configuration**: Open `config/agent_config.yaml` in a text editor and modify the settings according to your environment and requirements. Pay close attention to the LLM provider, model selection, and any necessary API credentials.

## Usage

You can run the docstring generation process using either the command line or the web UI.

**1. Command Line Interface (CLI)**

This is the primary method for running the generation process directly.

```bash
# Example: Run on a test repo (remove existing docstrings first if desired)
./test/tool/remove_docstrings.sh data/raw_test_repo
python generate_docstrings.py --repo-path data/raw_test_repo
```
Use `python generate_docstrings.py --help` to see available options, such as specifying different configurations or test modes.

**2. Generation Web UI**

The web UI provides a graphical interface to configure, run, and monitor the process.

- Note that when input repo path, always put complete absolute path.

```bash
# Launch the web UI server
python run_web_ui.py --host 0.0.0.0 --port 5000
```

Then, access the UI in your web browser, typically at `http://localhost:5000`. If running the server remotely, you might need to set up SSH tunneling (see instructions below or the [Web UI README](./src/web/README.md)).

*Basic SSH Tunneling (if running server remotely):*
```bash
# In your local terminal
ssh -L 5000:localhost:5000 <your_remote_username>@<your_remote_host>
# Then access http://localhost:5000 in your local browser
```

## Running the Evaluation System

DocAgent includes a separate web-based interface for evaluating the quality of generated docstrings.

**1. Running Locally**

To run the evaluation system on your local machine:

```bash
python src/web_eval/app.py
```

Then, access the evaluation UI in your web browser at `http://localhost:5001`.

**2. Running on a Remote Server**

To run the evaluation system on a remote server:

```bash
python src/web_eval/app.py --host 0.0.0.0 --port 5001
```

Then, set up SSH tunneling to access the remote server from your local machine:

```bash
ssh -L 5001:localhost:5001 <your_remote_username>@<your_remote_host>
```

Once the tunnel is established, access the evaluation UI in your local web browser at `http://localhost:5001`.

## Optional: Using a Local LLM

If you prefer to use a local LLM (e.g., one hosted via Hugging Face), you can configure DocAgent to interact with it via an API endpoint.

1.  **Serve the Local LLM**: Use a tool like `vllm` to serve your model. A convenience script is provided:
    ```bash
    # Ensure vllm is installed: pip install vllm
    bash tool/serve_local_llm.sh
    ```
    This script will likely start an OpenAI-compatible API server (check the script details). Note the URL where the model is served (e.g., `http://localhost:8000/v1`).

2.  **Configure DocAgent**: Update your `config/agent_config.yaml` to point to the local LLM API endpoint. You'll typically need to set:
    - The `provider` to `openai` (if using an OpenAI-compatible server like vllm's default).
    - The `api_base` or equivalent URL parameter to your local server address (e.g., `http://localhost:8000/v1`).
    - The `model_name` to the appropriate identifier for your local model.
    - Set the `api_key` to `None` or an empty string if no key is required by your local server.

3.  **Run DocAgent**: Run the generation process as usual (CLI or Web UI). DocAgent will now send requests to your local LLM.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


