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

**Preferred pattern**: nest `In` and `Out` as inner classes inside the workflow. Use `partial class` to split build logic across files.

```csharp
[OriginalName("domain_resource_preparation")]
[Version(1)]
[WorkflowMetadata(FailureWorkflow = typeof(FailAllRunningReports))]
public partial class ResourcePreparation(
    WorkflowDefinitionBuilder<ResourcePreparation, ResourcePreparation.In, ResourcePreparation.Out> builder
) : Workflow<ResourcePreparation, ResourcePreparation.In, ResourcePreparation.Out>(builder)
{
    public class In : WorkflowInput<Out>
    {
        public required string OrderId { get; set; }
        public required ResourceOrderItem Item { get; set; }
    }

    public class Out : WorkflowOutput
    {
        public required RpdDevice RpdDevice { get; init; }
        public required string Intent { get; set; }
    }

    // Task properties — become strongly-typed references in BuildDefinition
    public required GetDevicesFromInventory GetDevices { get; set; }
    public required SwitchTaskModel DecideAction { get; set; }
}
```

`BuildDefinition()` in the same or a partial file — always call `base.BuildDefinition()` first:

```csharp
public override void BuildDefinition()
{
    base.BuildDefinition();

    _builder.AddTask(
        wf => wf.GetDevices,
        wf => new GetDevicesFromInventory { OrderId = wf.Input.OrderId }
    );

    _builder.AddTask(
        wf => wf.DecideAction,
        wf => new SwitchTaskInput { SwitchCaseValue = wf.GetDevices.Output.Action },
        new DecisionCases<ResourcePreparation>
        {
            ["install"] = BuildInstallFlow,
            DefaultCase = BuildRemovalFlow,
        }
    );

    _builder.SetOutput(wf => new Out
    {
        RpdDevice = wf.GetDevices.Output.RpdDevice,
        Intent = wf.GetDevices.Output.Intent,
    });
}

// Delegate case builders to separate methods (preferred over inline lambdas for complex cases)
private static void BuildInstallFlow(ITaskSequenceBuilder<ResourcePreparation> sc) { /* ... */ }
private static void BuildRemovalFlow(ITaskSequenceBuilder<ResourcePreparation> sc) { /* ... */ }
```

### Task Handlers

Extend `TaskRequestHandler<TRequest, TResponse>` (abstract class, NOT an interface). Use primary constructor syntax for dependency injection. Use `sealed` where appropriate.

```csharp
public class GetDevicesFromInventory : IRequest<Response>
{
    public required string OrderId { get; set; }
}

public class Response
{
    public required RpdDevice RpdDevice { get; set; }
    public required string Intent { get; set; }
}

[OriginalName("domain_get_devices_from_inventory")]
public sealed class Handler(
    IServiceInventoryManagement4ApiClient serviceInventory,
    IResourceInventoryManagement4ApiClient resourceInventory
) : TaskRequestHandler<GetDevicesFromInventory, Response>
{
    public override async Task<Response> Handle(GetDevicesFromInventory request, CancellationToken cancellationToken)
    {
        var service = await serviceInventory.GetServiceAsync(request.OrderId, cancellationToken);
        return new Response { /* ... */ };
    }
}
```

- PascalCase properties auto-convert to `snake_case` in Conductor JSON
- Override with `[JsonProperty("custom_name")]` when needed
- Use `[Required]` on request model properties — validated by `AddValidation()` pipeline
- Use `required` keyword on all input/output properties

### Metadata Attributes

| Attribute | Target | Description |
|---|---|---|
| `[OriginalName("name")]` | Class | Custom task/workflow name in Conductor |
| `[WorkflowMetadata(...)]` | Workflow class | OwnerEmail, OwnerApp, Description, FailureWorkflow |
| `[Version(n)]` | Workflow class | Version number for sub-workflow references |
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

C# property access and string interpolation auto-translates to Conductor expressions. Use `wf.Input` to reference workflow input (from inner `In` class):

```csharp
// C#
CustomerName = $"{wf.GetCustomer.Output.FirstName} {wf.GetCustomer.Output.LastName}"
Address = wf.Input.Address   // wf.Input references the workflow's In class

// Generated Conductor JSON
"customer_name": "${get_customer.output.first_name} ${get_customer.output.last_name}",
"address": "${workflow.input.address}"
```

**Supported expression features:**

- **Property chaining**: `wf.Task.Output.Field`
- **String interpolation**: `$"{wf.Task.Output.Name}"`
- **String concatenation**: `1 + "Str_" + wf.Input.Value`
- **Type casting**: `((FullName)wf.Task.Output.Name).FirstName` → `${task.output.name.first_name}`
- **Dictionary indexing**: `wf.Input.Dictionary["key"].Property` → `${workflow.input.dictionary['key'].property}`
- **Array initialization**: `new[] { 1, 2, 3 }` → `[1, 2, 3]`
- **Object initialization**: Nested objects and anonymous types supported
- **Workflow name embedding**: `NamingUtil.NameOf<MyWorkflow>()` → resolves `[OriginalName]` value

### Accessing Execution Context in Handlers

Inject `ConductorSharpExecutionContext` to access workflow/task metadata:

```csharp
public sealed class Handler(ConductorSharpExecutionContext context)
    : TaskRequestHandler<MyRequest, MyResponse>
{
    public override async Task<MyResponse> Handle(MyRequest request, CancellationToken cancellationToken)
    {
        var workflowId = context.WorkflowId;
        var taskId = context.TaskId;
        var correlationId = context.CorrelationId;
        return new MyResponse();
    }
}
```

## Task Types

### Simple Task

```csharp
_builder.AddTask(wf => wf.MyTask, wf => new MyTaskRequest { Input = wf.Input.Value });
```

### Sub-Workflow Task

Declare with `SubWorkflowTaskModel<TInput, TOutput>`:

```csharp
public SubWorkflowTaskModel<ChildWorkflowInput, ChildWorkflowOutput> ChildWorkflow { get; set; }

_builder.AddTask(wf => wf.ChildWorkflow, wf => new ChildWorkflowInput { OrderId = wf.Input.OrderId });
```

### Switch Task (Conditional Branching)

Declare with `SwitchTaskModel`. Use `DecisionCases<TWorkflow>` with builder lambdas or method references:

```csharp
public required SwitchTaskModel DecideAction { get; set; }

_builder.AddTask(
    wf => wf.DecideAction,
    wf => new SwitchTaskInput { SwitchCaseValue = wf.GetAction.Output.ActionType },
    new DecisionCases<MyWorkflow>
    {
        [nameof(ActionType.Install)] = sc => sc.AddTask(wf => wf.InstallTask, wf => new()),
        [nameof(ActionType.Remove)] = sc => sc.AddTask(wf => wf.RemoveTask, wf => new()),
        DefaultCase = BuildDefaultFlow,   // method reference preferred for complex cases
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
        TaskInput = new ExpectedInput { OrderId = wf.Input.OrderId },
        TaskToExecute = wf.Input.TaskName
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

For dynamic fork-join with runtime-generated tasks, build `WorkflowTask` objects and serialize inputs as `JObject`:

```csharp
var tasks = new List<WorkflowTask>();
var taskInputs = new Dictionary<string, JObject>();

foreach (var item in items)
{
    var taskName = $"{workflowName}/{item.Id}";
    tasks.Add(new WorkflowTask
    {
        TaskReferenceName = taskName,
        Name = taskName,
        Type = "SUB_WORKFLOW",
        SubWorkflowParam = new() { Name = workflowName },
        Optional = true,
    });
    taskInputs.Add(taskName, JObject.FromObject(new { item.Id, item.Name }));
}
```

### Do-While Loop Task

Output is `NoOutput` — no strongly typed output available:

```csharp
public DoWhileTaskModel DoWhile { get; set; }

_builder.AddTask(
    wf => wf.DoWhile,
    wf => new DoWhileInput { Value = wf.Input.Loops },
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
    wf => new LambdaInput { Value = wf.Input.Value },
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

Use `TerminationStatus` enum, not string literals:

```csharp
public TerminateTaskModel Terminate { get; set; }

_builder.AddTask(
    wf => wf.Terminate,
    wf => new TerminateTaskInput
    {
        TerminationStatus = TerminationStatus.Completed,
        WorkflowOutput = new Out
        {
            RpdDevice = wf.GetDevices.Output.RpdDevice,
            Intent = wf.GetDevices.Output.Intent,
        }
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
    wf => new JqInput { QueryExpression = ".data | map(.name)", Data = wf.Input.Items }
);
```

### PassThrough Task (Raw Definition)

Fallback for unsupported task types:

```csharp
_builder.AddTasks(new WorkflowTask
{
    Name = "custom_task",
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
    .AddConductorSharp(baseUrl: configuration.GetValue<string>("Conductor:BaseUrl"))
    .SetBuildConfiguration(new BuildConfiguration
    {
        DefaultOwnerApp = configuration.GetValue<string>("Conductor:BuildConfiguration:DefaultOwnerApp") ?? "my-app",
        DefaultOwnerEmail = configuration.GetValue<string>("Conductor:BuildConfiguration:DefaultOwnerEmail") ?? "team@example.com",
    })
    .AddExecutionManager(
        maxConcurrentWorkers: configuration.GetValue<int?>("Conductor:MaxConcurrentWorkers") ?? 10,
        sleepInterval: configuration.GetValue("Conductor:SleepInterval", 1000),
        longPollInterval: configuration.GetValue("Conductor:LongPollInterval", 1000),
        domain: null,
        typeof(Program).Assembly
    )
    .UseBetaExecutionManager()
    .AddPipelines(pipelines =>
    {
        pipelines.AddCustomBehavior(typeof(MyCustomBehavior<,>));
        pipelines.AddExecutionTaskTracking();
        pipelines.AddContextLogging();
        pipelines.AddRequestResponseLogging();
        pipelines.AddValidation();
    })
    .AddConductorSharpPatterns();
```

### Assembly-Based Registration (Preferred)

Rather than registering each handler and workflow manually, scan the assembly automatically:

```csharp
// Extension method — define once and reuse across all modules
public static IServiceCollection RegisterAllConductorPartsFromAssembly(
    this IServiceCollection services, Assembly assembly)
{
    return services
        .RegisterWorkflowsFromAssembly(assembly)
        .RegisterWorkersFromAssembly(assembly)
        .AddMediatR(config => config.RegisterServicesFromAssembly(assembly));
}

// Usage
services.RegisterAllConductorPartsFromAssembly(typeof(Program).Assembly);
```

Manual registration (for individual cases):
```csharp
services.RegisterWorkerTask<MyTaskHandler>(options =>
{
    options.OwnerEmail = "team@example.com";
    options.Description = "My task description";
});
services.RegisterWorkflow<MyWorkflow>();
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
.SetHealthCheckService<FileHealthService>()      // persists to CONDUCTORSHARP_HEALTH.json
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
        WorkflowId = wf.Input.TargetWorkflowId,
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
    wf => new LambdaInput { Value = wf.Input.Value },
    input => new LambdaOutput { Result = input.Value.ToUpperInvariant() }
);
```

## Kafka Cancellation Notifier

```csharp
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
# conductorsharp.yaml
baseUrl: http://localhost:8080
apiPath: api
namespace: MyApp.Generated
destination: ./Generated

# Commands
dotnet-conductorsharp                          # all tasks and workflows
dotnet-conductorsharp -n domain_get_customer   # filter by name
dotnet-conductorsharp -e team@example.com      # filter by owner email
dotnet-conductorsharp --no-tasks               # skip tasks
dotnet-conductorsharp --dry-run                # preview only
```

## Conventions

### Naming

- **Domain-prefix** all task and workflow names using `snake_case`: `access_rpd_get_device`, `order_validate_input`
- Use `[OriginalName("domain_action_description")]` on every task handler and workflow class
- Task/workflow names: `snake_case` (all lowercase with underscores)
- C# class names: PascalCase, semantically matching the `[OriginalName]`
- Use `nameof()` for switch case keys when discriminating on enum values: `[nameof(ActionType.Install)]`

### File Organization

Split workflows across partial classes. Keep request/response models in the same file as the handler:

```
src/
  Workflows/
    ResourcePreparation/
      ResourcePreparation.cs               # Class definition + In/Out + task properties
      ResourcePreparationForInstall.cs     # partial — BuildInstallFlow()
      ResourcePreparationForRemoval.cs     # partial — BuildRemovalFlow()
  Tasks/
    GetDevicesFromInventory/
      GetDevicesFromInventory.cs           # Handler + Request + Response in one file
```

### Validation

Use data annotation attributes on request models, not validation logic in handlers:

```csharp
public class GetCustomerRequest : IRequest<GetCustomerResponse>
{
    [Required]
    public required string CustomerId { get; set; }
}
```

Register `AddValidation()` in the pipeline to enforce automatically.

### Failure Workflows

Define a shared failure workflow per domain and reference it via `[WorkflowMetadata]`:

```csharp
[WorkflowMetadata(FailureWorkflow = typeof(FailAllRunningReports))]
```

## Known Limitations

- Conductor **events** are not supported by the library
- `DoWhileTaskModel` provides no strongly typed output (`NoOutput`)
- `LambdaTaskModel` output is accessed via `Output.Result.Property` (extra `.Result` level)
- Dictionary indexing on arbitrary types (non-`Dictionary<,>`) is not supported in expressions
