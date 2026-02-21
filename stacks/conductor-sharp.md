# ABOUTME: ConductorSharp development guide - key concepts, patterns, and conventions for .NET Conductor workflow orchestration.

# ConductorSharp Development Guide

**Source**: https://github.com/codaxy/conductor-sharp
**Wiki**: https://github.com/codaxy/conductor-sharp/wiki

ConductorSharp is a .NET client library for Netflix Conductor providing a strongly-typed workflow builder DSL, task handlers, and quality-of-life additions.

## Installation

```bash
# Core
dotnet add package ConductorSharp.Client
dotnet add package ConductorSharp.Engine

# Optional
dotnet add package ConductorSharp.Patterns
dotnet add package ConductorSharp.KafkaCancellationNotifier
dotnet tool install --global ConductorSharp.Toolkit
```

## Core Packages

| Package | Purpose |
|---|---|
| `ConductorSharp.Client` | API communication with Conductor server |
| `ConductorSharp.Engine` | Workflow definition, task handlers, execution management |
| `ConductorSharp.Patterns` | Pre-built tasks (WaitSeconds, ReadWorkflowTasks, C# lambdas) |
| `ConductorSharp.Toolkit` | CLI for scaffolding definitions from existing Conductor server |
| `ConductorSharp.KafkaCancellationNotifier` | Event-driven task cancellation via Kafka |

## Core Concepts

### Workflows

Inherit from `Workflow<TWorkflow, TInput, TOutput>`. Input must extend `WorkflowInput<TOutput>`, output must extend `WorkflowOutput`. Inject `WorkflowDefinitionBuilder` via constructor.

```csharp
public class SendNotificationInput : WorkflowInput<SendNotificationOutput>
{
    public int CustomerId { get; set; }
}

public class SendNotificationOutput : WorkflowOutput
{
    public string EmailBody { get; set; }
}

[OriginalName("NOTIFICATION_send")]
[WorkflowMetadata(OwnerEmail = "team@example.com")]
public class SendNotificationWorkflow : Workflow<SendNotificationWorkflow, SendNotificationInput, SendNotificationOutput>
{
    public SendNotificationWorkflow(
        WorkflowDefinitionBuilder<SendNotificationWorkflow, SendNotificationInput, SendNotificationOutput> builder
    ) : base(builder) { }

    // Task properties — become strongly-typed references in BuildDefinition
    public GetCustomerHandler GetCustomer { get; set; }
    public PrepareEmailHandler PrepareEmail { get; set; }

    public override void BuildDefinition()
    {
        _builder.AddTask(
            wf => wf.GetCustomer,
            wf => new GetCustomerRequest { CustomerId = wf.WorkflowInput.CustomerId }
        );

        _builder.AddTask(
            wf => wf.PrepareEmail,
            wf => new PrepareEmailRequest
            {
                CustomerName = wf.GetCustomer.Output.Name,
                Address = wf.GetCustomer.Output.Address
            }
        );

        _builder.SetOutput(wf => new SendNotificationOutput
        {
            EmailBody = wf.PrepareEmail.Output.EmailBody
        });
    }
}
```

### Task Handlers

Extend `TaskRequestHandler<TRequest, TResponse>` (abstract class, NOT an interface). Task request implements `IRequest<TResponse>`.

```csharp
public class PrepareEmailRequest : IRequest<PrepareEmailResponse>
{
    [Required]
    public string CustomerName { get; set; }
    public string Address { get; set; }
}

public class PrepareEmailResponse
{
    public string EmailBody { get; set; }
}

[OriginalName("EMAIL_prepare")]
public class PrepareEmailHandler : TaskRequestHandler<PrepareEmailRequest, PrepareEmailResponse>
{
    public override async Task<PrepareEmailResponse> Handle(PrepareEmailRequest request, CancellationToken cancellationToken)
    {
        return new PrepareEmailResponse { EmailBody = $"Hello {request.CustomerName}!" };
    }
}
```

- PascalCase properties auto-convert to `snake_case` in Conductor JSON
- Override with `[JsonProperty("custom_name")]` when needed
- Use `[Required]` on request model properties — validated by `AddValidation()` pipeline

### Metadata Attributes

| Attribute | Target | Description |
|---|---|---|
| `[OriginalName("NAME")]` | Class | Custom task/workflow name in Conductor |
| `[WorkflowMetadata(...)]` | Workflow class | OwnerEmail, OwnerApp, Description, FailureWorkflow |
| `[Version(n)]` | Class | Version number for sub-workflow references |
| `[TaskDomain("domain")]` | Task class | Assign task to specific domain |

Task metadata is configured at registration (not via attribute):
```csharp
services.RegisterWorkerTask<MyTaskHandler>(options =>
{
    options.OwnerEmail = "team@example.com";
    options.Description = "My task description";
});
```

### Expression Generation

C# property access and string interpolation auto-translates to Conductor expressions:

```csharp
// C#
CustomerName = $"{wf.GetCustomer.Output.FirstName} {wf.GetCustomer.Output.LastName}"
Address = wf.WorkflowInput.Address

// Generated Conductor JSON
"customer_name": "${get_customer.output.first_name} ${get_customer.output.last_name}",
"address": "${workflow.input.address}"
```

**Supported expression features:**

- **Property chaining**: `wf.Task.Output.Field`
- **String interpolation**: `$"{wf.Task.Output.Name}"`
- **String concatenation**: `1 + "Str_" + wf.WorkflowInput.Input`
- **Type casting**: `((FullName)wf.Task.Output.Name).FirstName` → `${task.output.name.first_name}`
- **Dictionary indexing**: `wf.WorkflowInput.Dictionary["key"].Property` → `${workflow.input.dictionary['key'].property}`
- **Array initialization**: `new[] { 1, 2, 3 }` → `[1, 2, 3]`
- **Object initialization**: Nested objects and anonymous types supported
- **Workflow name embedding**: `NamingUtil.NameOf<MyWorkflow>()` → resolves `[OriginalName]` value

### Accessing Execution Context in Handlers

Inject `ConductorSharpExecutionContext` to access workflow/task metadata:

```csharp
public class MyHandler : TaskRequestHandler<MyRequest, MyResponse>
{
    private readonly ConductorSharpExecutionContext _context;

    public MyHandler(ConductorSharpExecutionContext context) => _context = context;

    public override async Task<MyResponse> Handle(MyRequest request, CancellationToken cancellationToken)
    {
        var workflowId = _context.WorkflowId;
        var taskId = _context.TaskId;
        var correlationId = _context.CorrelationId;
        return new MyResponse();
    }
}
```

## Task Types

### Simple Task

```csharp
_builder.AddTask(wf => wf.MyTask, wf => new MyTaskRequest { Input = wf.WorkflowInput.Value });
```

### Sub-Workflow Task

Declare with `SubWorkflowTaskModel<TInput, TOutput>`:

```csharp
public SubWorkflowTaskModel<ChildWorkflowInput, ChildWorkflowOutput> ChildWorkflow { get; set; }

_builder.AddTask(wf => wf.ChildWorkflow, wf => new ChildWorkflowInput { CustomerId = wf.WorkflowInput.CustomerId });
```

### Switch Task (Conditional Branching)

Declare with `SwitchTaskModel`. Use `DecisionCases<TWorkflow>` with a builder lambda per case:

```csharp
public SwitchTaskModel SwitchTask { get; set; }
public TaskA TaskInCaseA { get; set; }
public TaskB TaskInCaseB { get; set; }

_builder.AddTask(
    wf => wf.SwitchTask,
    wf => new SwitchTaskInput { SwitchCaseValue = wf.WorkflowInput.Operation },
    new DecisionCases<MyWorkflow>
    {
        ["caseA"] = builder => builder.AddTask(wf => wf.TaskInCaseA, wf => new TaskARequest { }),
        ["caseB"] = builder => builder.AddTask(wf => wf.TaskInCaseB, wf => new TaskBRequest { }),
        DefaultCase = builder => { /* default case tasks */ }
    }
);
```

### Dynamic Task

Task name resolved at runtime:

```csharp
public DynamicTaskModel<ExpectedInput, ExpectedOutput> DynamicHandler { get; set; }

_builder.AddTask(
    wf => wf.DynamicHandler,
    wf => new DynamicTaskInput<ExpectedInput, ExpectedOutput>
    {
        TaskInput = new ExpectedInput { CustomerId = wf.WorkflowInput.CustomerId },
        TaskToExecute = wf.WorkflowInput.TaskName
    }
);
```

### Dynamic Fork-Join

```csharp
public DynamicForkJoinTaskModel DynamicFork { get; set; }

_builder.AddTask(
    wf => wf.DynamicFork,
    wf => new DynamicForkJoinInput
    {
        DynamicTasks = wf.PrepareTasks.Output.DynamicTasks,
        DynamicTasksInput = wf.PrepareTasks.Output.DynamicTasksInput
    }
);
```

### Do-While Loop Task

Output is `NoOutput` — no strongly typed output available:

```csharp
public DoWhileTaskModel DoWhile { get; set; }
public GetCustomerHandler GetCustomer { get; set; }

_builder.AddTask(
    wf => wf.DoWhile,
    wf => new DoWhileInput { Value = wf.WorkflowInput.Loops },
    "$.do_while.iteration < $.value",  // Loop condition (JavaScript)
    builder =>
    {
        builder.AddTask(wf => wf.GetCustomer, wf => new GetCustomerRequest { CustomerId = "CUSTOMER-1" });
    }
);
```

### Lambda Task (JavaScript)

Output accessed via `Output.Result.Property` (not `Output.Property` directly):

```csharp
public LambdaTaskModel<LambdaInput, LambdaOutput> LambdaTask { get; set; }

_builder.AddTask(
    wf => wf.LambdaTask,
    wf => new LambdaInput { Value = wf.WorkflowInput.Input },
    script: "return { something: $.Value.toUpperCase() }"
);

// Access output as: wf.LambdaTask.Output.Result.Something
```

### Wait Task

```csharp
public WaitTaskModel WaitTask { get; set; }

_builder.AddTask(
    wf => wf.WaitTask,
    wf => new WaitTaskInput { Duration = "1h" }  // or Until = "2024-01-01T00:00:00Z"
);
```

### Terminate Task

```csharp
public TerminateTaskModel TerminateTask { get; set; }

_builder.AddTask(
    wf => wf.TerminateTask,
    wf => new TerminateTaskInput
    {
        TerminationStatus = "COMPLETED",
        WorkflowOutput = new { Result = "Done" }
    }
);
```

### Human Task

```csharp
public HumanTaskModel<HumanTaskOutput> HumanTask { get; set; }

_builder.AddTask(wf => wf.HumanTask, wf => new HumanTaskInput<HumanTaskOutput> { });
```

### JSON JQ Transform Task

```csharp
public JsonJqTransformTaskModel<JqInput, JqOutput> TransformTask { get; set; }

_builder.AddTask(
    wf => wf.TransformTask,
    wf => new JqInput { QueryExpression = ".data | map(.name)", Data = wf.WorkflowInput.Items }
);
```

### PassThrough Task (Raw Definition)

Fallback for unsupported task types:

```csharp
_builder.AddTasks(new WorkflowTask
{
    Name = "CUSTOM_task",
    TaskReferenceName = "custom_ref",
    Type = "CUSTOM",
    InputParameters = new Dictionary<string, object> { ["key"] = "value" }
});
```

### Optional Tasks

Workflow continues on failure:

```csharp
_builder.AddTask(wf => wf.OptionalTask, wf => new OptionalTaskRequest { }).AsOptional();
```

## Registration & Configuration

### Service Registration

```csharp
services
    .AddConductorSharp(baseUrl: "http://localhost:8080")
    .AddExecutionManager(
        maxConcurrentWorkers: 10,
        sleepInterval: 500,
        longPollInterval: 100,
        domain: null,
        typeof(Program).Assembly
    )
    .AddPipelines(pipelines =>
    {
        pipelines.AddCustomBehavior(typeof(MyCustomBehavior<,>)); // custom (runs first)
        pipelines.AddExecutionTaskTracking();
        pipelines.AddContextLogging();
        pipelines.AddRequestResponseLogging();
        pipelines.AddValidation();
    });

services.RegisterWorkerTask<GetCustomerHandler>();
services.RegisterWorkflow<SendNotificationWorkflow>();
```

### Multiple Conductor Instances

```csharp
services
    .AddConductorSharp(baseUrl: "http://primary:8080")
    .AddAlternateClient(
        baseUrl: "http://secondary:8080",
        key: "Secondary",
        apiPath: "api",
        ignoreInvalidCertificate: false
    );

// Resolve via keyed services
public class MyService([FromKeyedServices("Secondary")] IWorkflowService secondaryService) { }
```

### Poll Timing Strategies

```csharp
// Default: inverse exponential backoff
.AddExecutionManager(...)

// Constant interval
.AddExecutionManager(...)
.UseConstantPollTimingStrategy()
```

### Health Checks

```csharp
builder.Services.AddHealthChecks()
    .AddCheck<ConductorSharpHealthCheck>("conductor-worker");

// In execution manager chain:
.SetHealthCheckService<InMemoryHealthService>()  // default
// or
.SetHealthCheckService<FileHealthService>()  // persists to CONDUCTORSHARP_HEALTH.json
```

## API Services

| Service | Description |
|---|---|
| `IWorkflowService` | Start, pause, resume, terminate workflows |
| `ITaskService` | Update tasks, get logs, poll for tasks |
| `IMetadataService` | Manage workflow/task definitions |
| `IAdminService` | Admin operations |
| `IEventService` | Event handlers |
| `IQueueAdminService` | Queue administration |
| `IWorkflowBulkService` | Bulk workflow operations |
| `IHealthService` | Conductor server health |
| `IExternalPayloadService` | External payload storage |

## Patterns Package

```csharp
.AddExecutionManager(...)
.AddConductorSharpPatterns()   // Adds WaitSeconds, ReadWorkflowTasks
.AddCSharpLambdaTasks()        // Adds C# lambda task support
```

### WaitSeconds Task

```csharp
public WaitSeconds WaitTask { get; set; }

_builder.AddTask(wf => wf.WaitTask, wf => new WaitSecondsRequest { Seconds = 30 });
```

### ReadWorkflowTasks Task

```csharp
public ReadWorkflowTasks ReadTasks { get; set; }

_builder.AddTask(
    wf => wf.ReadTasks,
    wf => new ReadWorkflowTasksInput
    {
        WorkflowId = wf.WorkflowInput.TargetWorkflowId,
        TaskNames = "task1,task2"
    }
);
```

### C# Lambda Tasks

Execute C# code inline (no JavaScript needed):

```csharp
public CSharpLambdaTaskModel<LambdaInput, LambdaOutput> InlineLambda { get; set; }

_builder.AddTask(
    wf => wf.InlineLambda,
    wf => new LambdaInput { Value = wf.WorkflowInput.Input },
    input => new LambdaOutput { Result = input.Value.ToUpperInvariant() }
);
```

## Kafka Cancellation Notifier

```csharp
.AddExecutionManager(...)
.AddKafkaCancellationNotifier(
    kafkaBootstrapServers: "localhost:9092",
    topicName: "conductor.status.task",
    groupId: "my-worker-group",
    createTopicOnStartup: true
)
```

## Toolkit CLI

Generate C# models from existing Conductor task/workflow definitions.

```bash
# Create conductorsharp.yaml
baseUrl: http://localhost:8080
apiPath: api
namespace: MyApp.Generated
destination: ./Generated

# Scaffold
dotnet-conductorsharp                          # all tasks and workflows
dotnet-conductorsharp -n CUSTOMER_get          # filter by name
dotnet-conductorsharp -e team@example.com      # filter by owner email
dotnet-conductorsharp --no-tasks               # skip tasks
dotnet-conductorsharp --dry-run                # preview only
```

## Conventions

### Naming

- **Domain-prefix** all task and workflow names: `CUSTOMER_get`, `EMAIL_prepare`, `ORDER_validate`
  - Prevents naming conflicts across microservices
- Use `[OriginalName("DOMAIN_action")]` on every task handler and workflow class
- Task names: `SCREAMING_SNAKE_CASE` (Conductor convention)
- C# class names: PascalCase, semantically matching the `[OriginalName]`

### File Organization

Keep request/response models in the same file as the handler when you have many workers:

```
src/
  Workflows/
    SendNotification/
      SendNotificationWorkflow.cs     # Workflow + Input + Output
  Tasks/
    GetCustomer/
      GetCustomerHandler.cs           # Handler + Request + Response in one file
```

### Validation

Use data annotation attributes on request models, not validation logic in handlers:

```csharp
public class GetCustomerRequest : IRequest<GetCustomerResponse>
{
    [Required]
    public string CustomerId { get; set; }
}
```

Register `AddValidation()` in the pipeline to enforce automatically.

## Known Limitations

- Conductor **events** are not supported by the library
- `DoWhileTaskModel` provides no strongly typed output (`NoOutput`)
- `LambdaTaskModel` output is accessed via `Output.Result.Property` (extra `.Result` level)
- Dictionary indexing on arbitrary types (non-`Dictionary<,>`) is not supported in expressions
