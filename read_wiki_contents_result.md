# Page: Overview

# Overview

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [README.md](README.md)
- [docs/background/index.md](docs/background/index.md)
- [docs/index.md](docs/index.md)
- [docs/overrides/main.html](docs/overrides/main.html)

</details>



## Purpose and Scope

SWE-agent is an AI software engineering agent that enables language models (e.g., GPT-4o, Claude Sonnet) to autonomously fix issues in real GitHub repositories, find cybersecurity vulnerabilities, and perform custom software engineering tasks. The system achieves state-of-the-art performance on SWE-bench by implementing an **Agent-Computer Interface (ACI)** that provides LM-centric commands and feedback formats.

Key capabilities include:
- ✅ **State of the art** on SWE-bench among open-source projects
- ✅ **Free-flowing & generalizable**: Leaves maximal agency to the LM
- ✅ **Configurable & fully documented**: Governed by a single `yaml` file
- ✅ **Made for research**: Simple & hackable by design

### EnIGMA Cybersecurity Extension

SWE-agent includes **EnIGMA** (Enhanced Interactive Generative Model Agent), a specialized mode for offensive cybersecurity challenges. EnIGMA achieves state-of-the-art results on multiple cybersecurity benchmarks, solving 13.5% of challenges on the NYU CTF benchmark and surpassing previous agents by more than 3x.

For detailed information about specific subsystems, see:
- Core agent logic and model integration: [Agent Framework](#3)
- Code execution environments and containerization: [Environment System](#4) 
- Single instance and batch processing workflows: [Execution and Run System](#5)
- File editing, search, and command parsing: [Tool System](#6)
- Command line interface and configuration: [Command Line Interface](#7)
- Trajectory analysis and debugging tools: [Trajectory Management and Inspection](#8)

Sources: [README.md:14-24](), [docs/index.md:16-26](), [docs/background/index.md:7-14](), [docs/background/index.md:41-44]()

## System Architecture Overview

SWE-agent follows a modular architecture that separates concerns between orchestration, agent execution, model integration, environment management, and tool operations.

### Core System Architecture

```mermaid
graph TB
    subgraph "Core Agent System"
        AbstractAgent["AbstractAgent"]
        DefaultAgent["DefaultAgent"]
        RetryAgent["RetryAgent"]
        AbstractModel["AbstractModel"]
        LiteLLM["LiteLLM Integration"]
        AbstractRetryLoop["AbstractRetryLoop"]
        ScoreRetryLoop["ScoreRetryLoop"]
        ChooserRetryLoop["ChooserRetryLoop"]
        
        AbstractAgent --> DefaultAgent
        AbstractAgent --> RetryAgent
        AbstractModel --> LiteLLM
        AbstractRetryLoop --> ScoreRetryLoop
        AbstractRetryLoop --> ChooserRetryLoop
        DefaultAgent --> AbstractModel
        DefaultAgent --> AbstractRetryLoop
    end
    
    subgraph "Environment System"
        SWEEnv["SWEEnv"]
        SWEReX["SWE-ReX Runtime"]
        DockerContainers["Docker Containers"]
        ModalCloud["Modal Cloud"]
        
        SWEEnv --> SWEReX
        SWEReX --> DockerContainers
        SWEReX --> ModalCloud
    end
    
    subgraph "Tool System"
        ToolHandler["ToolHandler"]
        CommandDefinitions["Command Definitions"]
        ParseFunctions["ParseFunctions"]
        ToolBundles["Tool Bundles"]
        
        ToolHandler --> CommandDefinitions
        ToolHandler --> ParseFunctions
        ToolHandler --> ToolBundles
    end
    
    subgraph "Run Orchestration"
        RunSingle["RunSingle"]
        RunBatch["RunBatch"]
        RunHooks["RunHooks"]
        SweBenchEvaluate["SweBenchEvaluate"]
        
        RunBatch --> RunSingle
        RunSingle --> RunHooks
        RunHooks --> SweBenchEvaluate
    end
    
    DefaultAgent --> SWEEnv
    SWEEnv --> ToolHandler
    RunSingle --> DefaultAgent
    RunBatch --> DefaultAgent
```

Sources: [README.md:1-130](), [docs/background/index.md:1-70]()

### Agent-Computer Interface (ACI) Flow

```mermaid
graph LR
    subgraph "Agent Intelligence"
        LanguageModels["Language Models<br/>GPT-4o/Claude/etc"]
        ParseFunction["ParseFunction<br/>FunctionCalling/ThoughtAction"]
        HistoryProcessors["History Processors<br/>Cache Control/Summarization"]
        
        LanguageModels --> ParseFunction
        LanguageModels --> HistoryProcessors
    end
    
    subgraph "Agent-Computer Interface"
        DefaultAgent["DefaultAgent"]
        ToolSystem["Tool System"]
        PromptTemplates["Prompt Templates<br/>System/Instance/NextStep"]
        
        DefaultAgent --> ToolSystem
        DefaultAgent --> PromptTemplates
    end
    
    subgraph "Execution Environment"
        SWEEnv["SWEEnv"]
        SWEReXRuntime["SWE-ReX Runtime"]
        FileSystem["File System"]
        ShellEnvironment["Shell Environment"]
        
        SWEEnv --> SWEReXRuntime
        SWEReXRuntime --> FileSystem
        SWEReXRuntime --> ShellEnvironment
    end
    
    subgraph "Specialized Tools"
        str_replace_editor["str_replace_editor"]
        find_file["find_file"]
        search_dir["search_dir"]
        WindowedFile["WindowedFile"]
        
        str_replace_editor --> FileSystem
        find_file --> FileSystem
        search_dir --> FileSystem
        WindowedFile --> FileSystem
    end
    
    LanguageModels --> DefaultAgent
    ParseFunction --> DefaultAgent
    HistoryProcessors --> DefaultAgent
    DefaultAgent --> SWEEnv
    ToolSystem --> str_replace_editor
    ToolSystem --> find_file
    ToolSystem --> search_dir
    ToolSystem --> WindowedFile
```

Sources: [docs/background/index.md:11-12](), [docs/background/index.md:45-46]()

### Configuration and Data Flow

SWE-agent uses a hierarchical configuration system built on Pydantic models that manages everything from agent behavior to environment setup.

```mermaid
graph TB
    subgraph "Configuration Sources"
        default_yaml["config/default.yaml"]
        custom_yaml["Custom Config Files"]
        CLI_Args["CLI Arguments<br/>--agent.* --env.*"]
        EnvVars["Environment Variables<br/>SWE_AGENT_*"]
    end
    
    subgraph "Configuration Processing"
        HierarchicalMerging["Hierarchical Merging<br/>Pydantic Validation"]
        PathResolution["Path Resolution<br/>Relative to REPO_ROOT"]
        ConfigValidation["Config Validation<br/>Type Checking"]
    end
    
    subgraph "System Components"
        AgentConfig["Agent Configuration<br/>Model/Tools/Templates"]
        EnvironmentConfig["Environment Configuration<br/>Deployment/Repository"]
        ProblemConfig["Problem Configuration<br/>GitHub/Text/File"]
        ToolConfig["Tool Configuration<br/>Bundles/Commands"]
    end
    
    subgraph "Extension Points"
        ToolBundles["Tool Bundles<br/>edit_anthropic/defaults"]
        RunHooks["Hook System<br/>Custom Run Behavior"]
        ParseFunctions["Parse Functions<br/>Custom Output Parsing"]
        HistoryProcessors["History Processors<br/>Context Management"]
    end
    
    default_yaml --> HierarchicalMerging
    custom_yaml --> HierarchicalMerging
    CLI_Args --> HierarchicalMerging
    EnvVars --> HierarchicalMerging
    
    HierarchicalMerging --> PathResolution
    PathResolution --> ConfigValidation
    
    ConfigValidation --> AgentConfig
    ConfigValidation --> EnvironmentConfig
    ConfigValidation --> ProblemConfig
    ConfigValidation --> ToolConfig
    
    AgentConfig --> RunHooks
    AgentConfig --> ParseFunctions
    AgentConfig --> HistoryProcessors
    ToolConfig --> ToolBundles
```

Sources: [README.md:21](), [docs/index.md:23]()

## Key System Components

### Agent Execution Pipeline

The agent execution follows a structured pipeline from initialization through task completion, with comprehensive error handling and retry mechanisms.

```mermaid
sequenceDiagram
    participant User
    participant BasicCLI as "BasicCLI<br/>Argument Parsing"
    participant RunSingle
    participant DefaultAgent
    participant SWEEnv
    participant ToolHandler
    participant LiteLLM as "LiteLLM<br/>Model Integration"
    
    User->>BasicCLI: "sweagent run --config config.yaml --repo_path /path"
    BasicCLI->>RunSingle: "initialize with merged config"
    RunSingle->>DefaultAgent: "create agent instance"
    RunSingle->>SWEEnv: "setup environment with SWE-ReX"
    
    loop "Agent Task Loop"
        DefaultAgent->>LiteLLM: "query for next action"
        LiteLLM-->>DefaultAgent: "response with action"
        DefaultAgent->>ToolHandler: "parse action via ParseFunction"
        ToolHandler-->>DefaultAgent: "structured command"
        DefaultAgent->>SWEEnv: "execute command in container"
        SWEEnv-->>DefaultAgent: "command output/observation"
        DefaultAgent->>DefaultAgent: "update trajectory history"
        
        alt "Task Complete"
            DefaultAgent-->>RunSingle: "AgentRunResult"
        else "Continue Task"
            DefaultAgent->>LiteLLM: "next iteration"
        end
    end
    
    RunSingle->>RunSingle: "save .traj JSON file"
    RunSingle-->>User: "completion status and predictions"
```

Sources: [README.md:14-24](), [docs/background/index.md:7-14]()

### Data Flow and Processing Pipeline

```mermaid
graph LR
    subgraph "Input Sources"
        CLI["Command Line Interface"]
        Config["YAML Configuration"]
        SWEBenchInstances["SWE-bench Instances"]
        GitHubIssues["GitHub Issues"]
        CustomProblems["Custom Problems"]
    end
    
    subgraph "Processing Layer"
        BasicCLI["BasicCLI<br/>Argument Parsing"]
        ConfigMerging["Configuration Merging"]
        InstanceLoader["Instance Loading<br/>Multiple Sources"]
    end
    
    subgraph "Execution Engine"
        RunOrchestrator["Run Orchestrator<br/>Single/Batch"]
        AgentLoop["Agent Execution Loop"]
        SWEEnvInteraction["SWEEnv Interaction"]
    end
    
    subgraph "Output and Analysis"
        TrajectoryFiles["Trajectory Files<br/>.traj JSON"]
        PredictionsJSON["Predictions<br/>preds.json"]
        TrajectoryInspector["Trajectory Inspector<br/>TUI/Web Interface"]
        DemoFiles["Demo Files<br/>YAML Format"]
    end
    
    CLI --> BasicCLI
    Config --> ConfigMerging
    SWEBenchInstances --> InstanceLoader
    GitHubIssues --> InstanceLoader
    CustomProblems --> InstanceLoader
    
    BasicCLI --> RunOrchestrator
    ConfigMerging --> RunOrchestrator
    InstanceLoader --> RunOrchestrator
    
    RunOrchestrator --> AgentLoop
    AgentLoop --> SWEEnvInteraction
    
    SWEEnvInteraction --> TrajectoryFiles
    AgentLoop --> PredictionsJSON
    TrajectoryFiles --> TrajectoryInspector
    TrajectoryFiles --> DemoFiles
```

Sources: [README.md:15-17](), [docs/background/index.md:41-49]()

### EnIGMA Cybersecurity Capabilities

EnIGMA extends SWE-agent with specialized cybersecurity features for offensive security challenges.

```mermaid
graph TB
    subgraph "EnIGMA Extensions"
        InteractiveAgentTools["Interactive Agent Tools (IATs)<br/>Debugger/Multitasking"]
        SummarizerConcept["Summarizer Concept<br/>Long Context Management"]
        CTFDemonstrations["CTF Demonstrations<br/>Category-specific examples"]
        CyberSecurityBundles["Cybersecurity Tool Bundles<br/>Specialized commands"]
    end
    
    subgraph "CTF Categories"
        Cryptography["Cryptography Challenges"]
        ReverseEngineering["Reverse Engineering"]
        Forensics["Forensics Analysis"]
        WebExploitation["Web Exploitation"]
    end
    
    subgraph "Core SWE-agent"
        DefaultAgent["DefaultAgent"]
        SWEEnv["SWEEnv"]
        ToolHandler["ToolHandler"]
    end
    
    InteractiveAgentTools --> DefaultAgent
    SummarizerConcept --> DefaultAgent
    CTFDemonstrations --> DefaultAgent
    CyberSecurityBundles --> ToolHandler
    
    CTFDemonstrations --> Cryptography
    CTFDemonstrations --> ReverseEngineering
    CTFDemonstrations --> Forensics
    CTFDemonstrations --> WebExploitation
    
    DefaultAgent --> SWEEnv
    SWEEnv --> ToolHandler
```

Sources: [README.md:47-55](), [docs/background/index.md:36-50]()

### Version and Dependency Management

SWE-agent maintains strict version compatibility with its dependencies, particularly SWE-ReX for runtime execution.

| Component | Version | Requirement |
|-----------|---------|-------------|
| SWE-agent | 1.1.0 | Current version |
| Python | >= 3.11 | Minimum supported |
| SWE-ReX | >= 1.2.0 | Minimum required |
| SWE-ReX | 1.2.1 | Recommended |

The system includes version checking and warnings for compatibility:

```python
# Version validation constants
PYTHON_MINIMUM_VERSION = (3, 11)
SWEREX_MINIMUM_VERSION = "1.2.0"
SWEREX_RECOMMENDED_VERSION = "1.2.1"
```

Sources: [sweagent/__init__.py:15-18](), [sweagent/__init__.py:85-104]()

### Directory Structure and Package Organization

SWE-agent organizes its components across several key directories that can be configured via environment variables:

```mermaid
graph TD
    subgraph "Package Structure"
        PACKAGE_DIR["sweagent/"]
        CONFIG_DIR["config/"]
        TOOLS_DIR["tools/"]
        TRAJECTORY_DIR["trajectories/"]
    end
    
    subgraph "Environment Variables"
        SWE_AGENT_CONFIG_DIR["SWE_AGENT_CONFIG_DIR"]
        SWE_AGENT_TOOLS_DIR["SWE_AGENT_TOOLS_DIR"] 
        SWE_AGENT_TRAJECTORY_DIR["SWE_AGENT_TRAJECTORY_DIR"]
    end
    
    subgraph "Default Locations"
        DefaultConfig["PACKAGE_DIR.parent/config"]
        DefaultTools["PACKAGE_DIR.parent/tools"]
        DefaultTraj["PACKAGE_DIR.parent/trajectories"]
    end
    
    SWE_AGENT_CONFIG_DIR -.-> CONFIG_DIR
    SWE_AGENT_TOOLS_DIR -.-> TOOLS_DIR
    SWE_AGENT_TRAJECTORY_DIR -.-> TRAJECTORY_DIR
    
    CONFIG_DIR -.-> DefaultConfig
    TOOLS_DIR -.-> DefaultTools
    TRAJECTORY_DIR -.-> DefaultTraj
```

Sources: [sweagent/__init__.py:28-47]()

## Integration with External Systems

### SWE-ReX Runtime Integration

SWE-agent relies heavily on SWE-ReX for secure, isolated code execution. The integration includes version compatibility checking and commit hash tracking for reproducibility.

```python
# Version and commit tracking functions
def get_rex_version() -> str
def get_rex_commit_hash() -> str
def impose_rex_lower_bound() -> None
```

### Model Provider Support

SWE-agent supports multiple LLM providers through a unified interface, including OpenAI, Anthropic, and local model deployments. The system uses LiteLLM for provider abstraction and includes cost tracking and retry mechanisms.

### Documentation and Development Infrastructure

The project uses MkDocs for documentation generation with automatic API reference generation via mkdocstrings. The development workflow includes pre-commit hooks, GitHub Actions CI/CD, and comprehensive testing infrastructure.

Sources: [sweagent/__init__.py:62-82](), [mkdocs.yml:118-150](), [docs/installation/changelog.md:1-343]()